"""Baixa os logs das urnas do 2º turno de 2026 e extrai o horário de cada voto.

O log de cada urna (log.jez -> logd.dat) registra cada evento com timestamp. Ele acumula os dois
turnos, então só as linhas de 25/10/2026 são usadas. Os horários são o relógio LOCAL da urna;
a coluna `ts_*_brasilia` converte para o horário de Brasília (não se aplica ao exterior, ZZ).

Fonte: https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/ (pleito 3221 = 2º turno).

Uso:
    uv run scripts/baixar_logs_urna.py              # Brasil inteiro + exterior
    uv run scripts/baixar_logs_urna.py --uf ac
    uv run scripts/baixar_logs_urna.py --uf sp --municipio 71072   # só a capital
    uv run scripts/baixar_logs_urna.py --uf ac --uf rr --keep-raw    # guarda os .jez em data/raw
    uv run scripts/baixar_logs_urna.py --completar  # só as seções que faltam nas UFs já concluídas

Saídas em data/processed/logs_urna/ (particionado no estilo hive, por UF):
    eleitores/sg_uf=XX/part-*.parquet -> uma linha por eleitor que votou (horários de cada etapa)
    secoes/sg_uf=XX/part-*.parquet    -> uma linha por seção (abertura, primeiro/último voto, n de votos)

Leitura: pl.scan_parquet("data/processed/logs_urna/eleitores/**/*.parquet", hive_partitioning=True)

Sem --uf processa todas as UFs + exterior; UFs concluídas (_SUCCESS) são puladas ao rodar de novo.
"""

import argparse
import http.client
import io
import json
import multiprocessing
import os
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import polars as pl

PLEITO = "3221"
P = f"p{int(PLEITO):06d}"
BASE = f"https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/{PLEITO}"
DIA = "25/10/2026"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "arquivo-urna" / PLEITO
RAW_BU = ROOT / "data" / "raw" / "bu" / PLEITO  # plano B caso o bweb (CSV dos BUs) demore a sair
OUT = ROOT / "data" / "processed" / "logs_urna"
HEADERS = {"User-Agent": "Mozilla/5.0 (analise-eleicao-2026)"}

# Diferença (horas) do relógio local da urna para Brasília. AM tem municípios em UTC-4 e UTC-5: os de UTC-5
# ficam numa tabela fixa (FUSO_AM_MENOS_2). A tabela saiu do próprio 2º turno de 2026: nesses 11 municípios todas
# as urnas ficaram prontas às 6h do relógio local (8h de Brasília), e nenhum município teve urnas nos dois grupos.
# A hora de prontidão não decide mais o fuso (uma urna aberta com atraso seria classificada errado); serve só de
# conferência, em `fuso_divergente`.
FUSO_UF = {"ac": -2, "am": -1, "mt": -1, "ms": -1, "ro": -1, "rr": -1}
FUSO_AM_MENOS_2 = {"AMATURÁ", "ATALAIA DO NORTE", "BENJAMIN CONSTANT", "EIRUNEPÉ", "ENVIRA", "GUAJARÁ", "IPIXUNA",
                   "ITAMARATI", "JUTAÍ", "SÃO PAULO DE OLIVENÇA", "TABATINGA"}
# Valores conhecidos de "Tipo de habilitação do eleitor [...]"; qualquer outro é contado em n_tipo_hab_desconhecido.
TIPOS_HABILITACAO = {"biométrica"}


def get(url: str, tentativas: int = 5) -> bytes:
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        # OSError cobre URLError/timeout/reset; HTTPException cobre RemoteDisconnected
        except (OSError, http.client.HTTPException) as exc:
            if i == tentativas - 1 or getattr(exc, "code", None) == 404:
                raise
            time.sleep(2**i)
    raise AssertionError("inalcançável")


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%d/%m/%Y %H:%M:%S")


def parse_log(logd: bytes) -> tuple[list[dict], dict]:
    """Extrai eleitores e resumo da seção das linhas de 25/10 do logd.dat.

    Um eleitor só vira registro quando a sequência identificação → … → "voto computado" fecha. O que fica fora
    dela não é descartado em silêncio: o resumo conta cada caso, e vale a reconciliação
        n_computado_lidas = len(eleitores) + n_computado_orfao
    (n_computado_orfao inclui uma segunda mensagem de computação depois de a sequência fechar)."""
    eleitores: list[dict] = []
    resumo = {"ts_urna_pronta": None, "modelo_urna": None, "n_alertas": 0, "n_erros": 0,
              "n_habilitacoes_sem_voto": 0, "n_computado_lidas": 0, "n_computado_orfao": 0,
              "n_identificacao_sem_habilitacao": 0, "n_pendente_fim_arquivo": 0, "n_tipo_hab_desconhecido": 0}
    atual: dict | None = None
    for linha in logd.decode("latin-1").splitlines():
        if "Modelo de Urna:" in linha:  # pode aparecer só na preparação, antes do dia da eleição
            resumo["modelo_urna"] = linha.split("Modelo de Urna:", 1)[1].split("\t", 1)[0].strip()
        if not linha.startswith(DIA):
            continue
        campos = linha.split("\t")
        if len(campos) < 5:
            continue
        ts, nivel, _, app, msg = campos[:5]
        if nivel == "ALERTA":
            resumo["n_alertas"] += 1
        elif nivel == "ERRO":
            resumo["n_erros"] += 1
        if app != "VOTA":
            continue
        if msg == "Urna pronta para receber votos":
            resumo["ts_urna_pronta"] = resumo["ts_urna_pronta"] or parse_ts(ts)
        elif msg == "Identificador do eleitor digitado pelo mesário":
            if atual and atual.get("ts_habilitado"):
                resumo["n_habilitacoes_sem_voto"] += 1
            elif atual:
                resumo["n_identificacao_sem_habilitacao"] += 1
            atual = {"ts_identificador": parse_ts(ts), "n_tentativas_digital": 0}
        elif msg == "O voto do eleitor foi computado" and atual is None:
            resumo["n_computado_lidas"] += 1
            resumo["n_computado_orfao"] += 1
        elif atual is None:
            continue
        elif msg.startswith("Identificador digitado pelo mesário foi:"):
            atual["tipo_identificador"] = msg.split("(", 1)[-1].rstrip(")")
        elif msg.startswith("Capturada a digital"):
            atual["n_tentativas_digital"] += 1
        elif msg.startswith("Tipo de habilitação do eleitor"):
            atual["tipo_habilitacao"] = msg.split("[", 1)[-1].rstrip("]")
            if atual["tipo_habilitacao"] not in TIPOS_HABILITACAO:
                resumo["n_tipo_hab_desconhecido"] += 1
        elif msg == "Eleitor foi habilitado":
            atual["ts_habilitado"] = parse_ts(ts)
        elif msg == "Voto confirmado para [Presidente]":
            atual["ts_voto_presidente"] = parse_ts(ts)
        elif msg == "O voto do eleitor foi computado":
            resumo["n_computado_lidas"] += 1
            atual["ts_computado"] = parse_ts(ts)
            eleitores.append(atual)
            atual = None
    if atual is not None:  # fim do arquivo com atendimento aberto
        resumo["n_pendente_fim_arquivo"] += 1
        if atual.get("ts_habilitado"):
            resumo["n_habilitacoes_sem_voto"] += 1
    assert resumo["n_computado_lidas"] == len(eleitores) + resumo["n_computado_orfao"]
    return eleitores, resumo


def processar_secao(sec: dict, keep_raw: bool, baixar_bu: bool) -> tuple[list[dict], list[dict]]:
    uf, mu, zo, se = sec["uf"], sec["cd_municipio_tse"], sec["zona"], sec["secao"]
    pasta = f"{BASE}/dados/{uf}/{mu}/{zo}/{se}"
    aux = json.loads(get(f"{pasta}/{P}-{uf}-m{mu}-z{zo}-s{se}-aux.json"))
    eleitores, secoes = [], []
    com_log = [h for h in aux.get("hashes", []) if any(a["tp"] == "log" for a in h.get("arq", []))]
    # ~3% das seções ficam só como "Recebido" mesmo com a apuração em 100%; vale o "Totalizado" quando houver
    hashes = [h for h in com_log if h.get("st") == "Totalizado"] or [h for h in com_log if h.get("st") == "Recebido"]
    for h in hashes:
        log = next(a["nm"] for a in h["arq"] if a["tp"] == "log")
        jez = get(f"{pasta}/{h['hash']}/{log}")
        if keep_raw:
            dest = RAW / uf / mu / zo / se / log
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(jez)
        bu = next((a["nm"] for a in h.get("arq", []) if a["tp"] == "bu"), None)
        if baixar_bu and bu:
            dest = RAW_BU / uf / f"{mu}-{zo}-{se}-{h['hash'][:16]}-bu.dat"
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(get(f"{pasta}/{h['hash']}/{bu}"))
        with zipfile.ZipFile(io.BytesIO(jez)) as z:
            elei, resumo = parse_log(z.read("logd.dat"))
        chave = {"sg_uf": uf.upper(), "cd_municipio_tse": mu, "nm_municipio": sec["nm_municipio"],
                 "zona": zo, "secao": se, "hash": h["hash"]}
        fuso = fuso_horas(uf, sec["nm_municipio"])
        resumo["fuso_divergente"] = fuso_divergente(uf, fuso, resumo["ts_urna_pronta"])
        for i, e in enumerate(elei, 1):
            eleitores.append({**chave, "ordem": i, **e, "fuso_brasilia_h": fuso})
        tsc = [e["ts_computado"] for e in elei]
        secoes.append({**chave, **resumo, "fuso_brasilia_h": fuso, "n_votos_log": len(elei),
                       "ts_primeiro_voto": min(tsc, default=None), "ts_ultimo_voto": max(tsc, default=None)})
    return eleitores, secoes


def fuso_horas(uf: str, nm_municipio: str) -> int | None:
    if uf == "zz":
        return None
    if nm_municipio == "FERNANDO DE NORONHA":
        return 1
    if uf == "am" and nm_municipio in FUSO_AM_MENOS_2:
        return -2
    return FUSO_UF.get(uf, 0)


def fuso_divergente(uf: str, fuso: int | None, ts_pronta: datetime | None) -> bool | None:
    """Conferência no AM: urna pronta antes das 7h locais sugere UTC-5; a partir das 7h, UTC-4. Uma divergência
    pode ser só atraso na abertura; fica registrada para inspeção, sem mudar o fuso."""
    if uf != "am" or ts_pronta is None:
        return None
    return (ts_pronta.hour < 7) != (fuso == -2)


def listar_secoes(uf: str, municipios: set[str] | None) -> list[dict]:
    cs = json.loads(get(f"{BASE}/config/{uf}/{uf}-{P}-cs.json"))
    return [
        {"uf": uf, "cd_municipio_tse": mu["cd"], "nm_municipio": mu["nm"], "zona": zo["cd"], "secao": s["ns"]}
        for abr in cs["abr"]
        for mu in abr["mu"]
        if not municipios or mu["cd"] in municipios
        for zo in mu["zon"]
        for s in zo["sec"]
        if "nsp" not in s  # seção agregada: votou na urna da seção principal `nsp`, não tem arquivos próprios
    ]


ESQUEMA_ELEITOR = {
    "sg_uf": pl.String, "cd_municipio_tse": pl.String, "nm_municipio": pl.String, "zona": pl.String,
    "secao": pl.String, "hash": pl.String, "ordem": pl.Int32, "ts_identificador": pl.Datetime("us"),
    "n_tentativas_digital": pl.Int8, "tipo_identificador": pl.String, "tipo_habilitacao": pl.String,
    "ts_habilitado": pl.Datetime("us"), "ts_voto_presidente": pl.Datetime("us"),
    "ts_computado": pl.Datetime("us"), "fuso_brasilia_h": pl.Int8,
}
ESQUEMA_SECAO = {
    "sg_uf": pl.String, "cd_municipio_tse": pl.String, "nm_municipio": pl.String, "zona": pl.String,
    "secao": pl.String, "hash": pl.String, "ts_urna_pronta": pl.Datetime("us"), "modelo_urna": pl.String,
    "n_alertas": pl.Int32,
    "n_erros": pl.Int32, "n_habilitacoes_sem_voto": pl.Int32, "n_computado_lidas": pl.Int32,
    "n_computado_orfao": pl.Int32, "n_identificacao_sem_habilitacao": pl.Int32, "n_pendente_fim_arquivo": pl.Int32,
    "n_tipo_hab_desconhecido": pl.Int32, "fuso_divergente": pl.Boolean, "fuso_brasilia_h": pl.Int8,
    "n_votos_log": pl.Int32, "ts_primeiro_voto": pl.Datetime("us"), "ts_ultimo_voto": pl.Datetime("us"),
}


def df_eleitores(linhas: list[dict]) -> pl.DataFrame:
    off = pl.duration(hours=-pl.col("fuso_brasilia_h"))
    return pl.DataFrame(linhas, schema=ESQUEMA_ELEITOR).with_columns(
        (pl.col("ts_computado") - pl.col("ts_identificador")).dt.total_seconds().cast(pl.Int32).alias("seg_atendimento"),
        (pl.col("ts_computado") - pl.col("ts_habilitado")).dt.total_seconds().cast(pl.Int32).alias("seg_na_cabine"),
        (pl.col("ts_identificador") + off).alias("ts_identificador_brasilia"),
        (pl.col("ts_computado") + off).alias("ts_computado_brasilia"),
    )


def processar_lote(lote: list[dict], keep_raw: bool, baixar_bu: bool, threads: int):
    """Roda num processo filho: baixa/parseia um lote de seções com threads e devolve DataFrames.

    Processos contornam o GIL (o parsing dos logs é CPU-bound); as threads cobrem a latência de rede.
    """
    eleitores, resumos, falhas = [], [], []
    with ThreadPoolExecutor(threads) as pool:
        futs = {pool.submit(processar_secao, s, keep_raw, baixar_bu): s for s in lote}
        for fut in as_completed(futs):
            try:
                e, r = fut.result()
                eleitores += e
                resumos += r
            except Exception as exc:  # noqa: BLE001
                falhas.append({**futs[fut], "erro": repr(exc)})
    return df_eleitores(eleitores), pl.DataFrame(resumos, schema=ESQUEMA_SECAO), falhas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf", action="append", help="sigla da UF (repetível); zz = exterior. Omitido = todas")
    ap.add_argument("--municipio", action="append", help="código TSE do município (repetível)")
    ap.add_argument("--processos", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--threads", type=int, default=8, help="threads de download por processo")
    ap.add_argument("--lote", type=int, default=40, help="seções por tarefa enviada a um processo")
    ap.add_argument("--chunk", type=int, default=500_000, help="eleitores por arquivo parquet")
    ap.add_argument("--keep-raw", action="store_true", help="salva os log.jez em data/raw")
    ap.add_argument("--sem-bu", action="store_true", help="não baixa os bu.dat brutos")
    ap.add_argument("--refazer", action="store_true", help="reprocessa UFs já concluídas")
    ap.add_argument("--completar", action="store_true",
                    help="em UFs já concluídas, baixa só as seções que ainda não estão em secoes/")
    args = ap.parse_args()

    if args.uf:
        ufs = [u.lower() for u in args.uf]
    else:
        cfg = json.loads(get("https://resultados.tse.jus.br/oficial/ele2026/6258/config/mun-e006258-cm.json"))
        ufs = sorted(u["cd"] for u in cfg["abr"])
    print(f"{args.processos} processos x {args.threads} threads", flush=True)

    # spawn: fork depois de o polars abrir threads no processo principal trava os filhos
    with ProcessPoolExecutor(args.processos, mp_context=multiprocessing.get_context("spawn")) as procs:
        for uf in ufs:
            dir_e = OUT / "eleitores" / f"sg_uf={uf.upper()}"
            dir_s = OUT / "secoes" / f"sg_uf={uf.upper()}"
            arq_falhas = OUT / f"falhas_{uf.upper()}.csv"
            completar = args.completar and (dir_e / "_SUCCESS").exists()
            if (dir_e / "_SUCCESS").exists() and not args.refazer and not args.municipio and not completar:
                print(f"{uf.upper()}: já concluída, pulando", flush=True)
                continue
            secoes = listar_secoes(uf, set(args.municipio) if args.municipio else None)
            if completar:
                feitas_antes = set(pl.read_parquet(dir_s / "*.parquet", columns=["cd_municipio_tse", "zona", "secao"]).rows())
                secoes = [s for s in secoes if (s["cd_municipio_tse"], s["zona"], s["secao"]) not in feitas_antes]
                # novas partes ganham prefixo próprio para não sobrescrever as existentes
                prefixo = f"c{len(list(dir_s.glob('*.parquet'))):02d}-"
            else:
                prefixo = ""
                for d in (dir_e, dir_s):
                    d.mkdir(parents=True, exist_ok=True)
                    for f in d.iterdir():
                        f.unlink()
            arq_falhas.unlink(missing_ok=True)
            if not secoes:
                print(f"{uf.upper()}: nada a completar", flush=True)
                continue
            lotes = [secoes[k : k + args.lote] for k in range(0, len(secoes), args.lote)]
            print(f"{uf.upper()}: {len(secoes)} seções em {len(lotes)} lotes", flush=True)
            buffer: list[pl.DataFrame] = []
            resumos: list[pl.DataFrame] = []
            falhas: list[dict] = []
            n_buffer = n_eleitores = parte = feitas = 0
            t0 = time.time()
            futs = {procs.submit(processar_lote, lt, args.keep_raw, not args.sem_bu, args.threads): len(lt)
                    for lt in lotes}
            for fut in as_completed(futs):
                e, r, f = fut.result()
                buffer.append(e)
                resumos.append(r)
                falhas += f
                n_buffer += e.height
                feitas += futs[fut]
                if n_buffer >= args.chunk:
                    pl.concat(buffer).write_parquet(dir_e / f"{prefixo}part-{parte:04d}.parquet")
                    n_eleitores += n_buffer
                    buffer, n_buffer, parte = [], 0, parte + 1
                if feitas % 2000 < futs[fut] or feitas == len(secoes):
                    dt = time.time() - t0
                    print(f"  {feitas}/{len(secoes)} seções ({dt:.0f}s, {feitas / dt:.1f} seções/s)", flush=True)
            if buffer:
                pl.concat(buffer).write_parquet(dir_e / f"{prefixo}part-{parte:04d}.parquet")
                n_eleitores += n_buffer
            pl.concat(resumos).write_parquet(dir_s / f"{prefixo}part-0000.parquet")
            if falhas:
                pl.DataFrame(falhas).write_csv(arq_falhas)
            if not args.municipio and not falhas:
                (dir_e / "_SUCCESS").touch()
            print(f"  {uf.upper()} {'ok' if not falhas else 'COM FALHAS (rode de novo)'}: "
                  f"eleitores={n_eleitores} seções com log={sum(r.height for r in resumos)} "
                  f"falhas={len(falhas)}", flush=True)


if __name__ == "__main__":
    main()
