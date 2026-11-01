"""Cap. 08b — amostra de logs de urna do 2º turno de 2022 para validar a inferência de modelo pelo nº de série.

O bweb de 2022 não tem coluna de modelo de urna, mas tem o nº da urna (`nr_urna_efetivada`).
O 08b_modelos_urna.py infere o modelo pela faixa de série. Este script baixa o log (logd.dat)
de uma amostra aleatória ESTRATIFICADA por faixa de série e lê a linha
"Identificação do Modelo de Urna: UE20xx" gravada pela própria urna, para medir a acurácia.

Fonte: arquivos de urna transmitidos para totalização, 2º turno 2022 (pleito 407), um ZIP por UF no
CDN do TSE (https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2022/arqurnatot/). Os ZIPs de
SP/MG passam de 9–20 GB, então NÃO baixamos o ZIP inteiro: lemos o diretório central por HTTP Range
e buscamos só os bytes do `.logjez` de cada seção sorteada.

O `.logjez` de 2022 é um arquivo 7z (LZMA); por isso o script precisa de `py7zr`, que não está no
projeto. Rode sem alterar o ambiente:
    uv run --with py7zr python analises/08b_baixar_logs_2022.py --n-estrato 60   # estratificada (540)
    uv run --with py7zr python analises/08b_baixar_logs_2022.py --simples 400    # aleatória simples (400)

Saídas:
    data/raw/logs_urna_2022_amostra/<UF>/o00407-MMMMMZZZZSSSS.logjez   (brutos, para auditoria)
    data/processed/base/cap08b_validacao_logs_2022[_simples].parquet     (uma linha por seção sorteada)
"""

from __future__ import annotations

import argparse
import io
import struct
import sys
import tempfile
import time
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import BASE, ROOT, bweb  # noqa: E402

URL = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2022/arqurnatot/bu_imgbu_logjez_rdv_vscmr_2022_2t_{uf}.zip"
RAW = ROOT / "data" / "raw" / "logs_urna_2022_amostra"
SAIDA = BASE / "cap08b_validacao_logs_2022.parquet"
UA = {"User-Agent": "Mozilla/5.0 (analise-eleicao-2026)"}
SEMENTE = 2022

# Estratos de série (definidos pelos vãos da distribuição, ANTES de ver qualquer log) + faixas de fronteira.
ESTRATOS = [
    ("s1_1000-1200k", 1_000_000, 1_200_000),
    ("s2_1200-1225k_fronteira", 1_200_000, 1_225_000),
    ("s3_1225-1340k", 1_225_000, 1_340_000),
    ("s4_1340-1400k_fronteira", 1_340_000, 1_400_000),
    ("s5_1600-1640k", 1_600_000, 1_640_000),
    ("s6_1640-1660k_fronteira", 1_640_000, 1_660_000),
    ("s7_1660-1700k", 1_660_000, 1_700_000),
    ("s8_1750-1860k", 1_750_000, 1_860_000),
    ("s9_2000-2250k", 2_000_000, 2_250_000),
]


def get(url: str, rng: tuple[int, int] | None = None, tentativas: int = 6) -> bytes:
    h = dict(UA)
    if rng:
        h["Range"] = f"bytes={rng[0]}-{rng[1]}"
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120) as r:
                return r.read()
        except OSError:
            if i == tentativas - 1:
                raise
            time.sleep(2**i)
    raise AssertionError


class ArquivoRemoto(io.RawIOBase):
    """Arquivo somente-leitura sobre HTTP Range (para o zipfile ler o diretório central)."""

    def __init__(self, url: str):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            self.size = int(r.headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def readinto(self, b):
        if self.pos >= self.size:
            return 0
        d = get(self.url, (self.pos, min(self.pos + len(b), self.size) - 1))
        b[: len(d)] = d
        self.pos += len(d)
        return len(d)


def ler_membro(url: str, info: zipfile.ZipInfo) -> bytes:
    ini = info.header_offset
    bloco = get(url, (ini, ini + 30 + 1024 + info.compress_size))
    assert bloco[:4] == b"PK\x03\x04", "cabeçalho local inválido"
    n, m = struct.unpack("<HH", bloco[26:30])
    dados = bloco[30 + n + m : 30 + n + m + info.compress_size]
    if info.compress_type == zipfile.ZIP_STORED:
        return dados
    if info.compress_type == zipfile.ZIP_DEFLATED:
        return zlib.decompressobj(-15).decompress(dados)
    raise ValueError(f"compressão {info.compress_type}")


def modelo_do_log(jez: bytes) -> dict:
    import py7zr

    with tempfile.TemporaryDirectory() as td:
        with py7zr.SevenZipFile(io.BytesIO(jez)) as z:
            z.extractall(td)
        texto = (Path(td) / "logd.dat").read_bytes().decode("latin-1")
    modelos_dia, modelos_todos, n_votos = [], [], 0
    ids: dict[str, int] = {}
    for linha in texto.splitlines():
        campos = linha.split("\t")
        if len(campos) >= 5:  # 3ª coluna: identificador gravado em cada linha (o "67305985" do relatório do IVL)
            ids[campos[2]] = ids.get(campos[2], 0) + 1
        if "Modelo de Urna:" in linha:
            mod = linha.split("Modelo de Urna:", 1)[1].split("\t", 1)[0].strip()
            modelos_todos.append(mod)
            if linha.startswith("30/10/2022"):
                modelos_dia.append(mod)
        if linha.startswith("30/10/2022") and "O voto do eleitor foi computado" in linha:
            n_votos += 1
    return {
        "modelo_log": (modelos_dia or modelos_todos or [None])[-1],
        "n_modelos_distintos": len(set(modelos_todos)),
        "n_votos_log": n_votos,
        "id_log": max(ids, key=ids.get) if ids else None,
        "n_ids_distintos": len(ids),
    }


def amostra(n_estrato: int, simples: int = 0) -> pl.DataFrame:
    b = (
        bweb(2022, 2)
        .filter(pl.col("sg_uf") != "ZZ")
        .select("sg_uf", "cd_municipio_tse", "zona", "secao", "nr_urna_efetivada", "qt_comparecimento")
        .collect()
        .with_columns(pl.col("nr_urna_efetivada").cast(pl.Int64, strict=False).alias("serie"))
    )
    if simples:  # validação fora da amostra: sorteio aleatório simples, semente diferente
        return b.sample(simples, seed=SEMENTE + 1).with_columns(pl.lit("aleatoria_simples").alias("estrato"))
    partes = []
    for nome, lo, hi in ESTRATOS:
        e = b.filter(pl.col("serie").is_between(lo, hi, closed="left"))
        partes.append(e.sample(min(n_estrato, e.height), seed=SEMENTE).with_columns(pl.lit(nome).alias("estrato")))
    return pl.concat(partes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-estrato", type=int, default=60)
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--simples", type=int, default=0,
                    help="em vez da amostra estratificada, sorteia N seções ao acaso (validação fora da amostra)")
    ap.add_argument("--do-disco", action="store_true",
                    help="reusa os .logjez já salvos em data/raw (só baixa o que faltar)")
    args = ap.parse_args()
    amo = amostra(args.n_estrato, args.simples)
    saida = SAIDA.with_name(SAIDA.stem + ("_simples" if args.simples else "") + ".parquet")
    print(f"amostra: {amo.height} seções em {amo['sg_uf'].n_unique()} UFs", flush=True)
    linhas = []
    for uf, grupo in amo.group_by("sg_uf", maintain_order=True):
        uf = uf[0]
        url = URL.format(uf=uf)
        t0 = time.time()
        with zipfile.ZipFile(io.BufferedReader(ArquivoRemoto(url), buffer_size=1 << 20)) as z:
            por_nome: dict[str, list[zipfile.ZipInfo]] = {}
            for i in z.infolist():
                if i.filename.endswith(".logjez"):
                    por_nome.setdefault(i.filename[7:20], []).append(i)

        def tarefa(r: dict) -> dict:
            chave = f"{r['cd_municipio_tse']}{r['zona']}{r['secao']}"
            infos = por_nome.get(chave, [])
            out = {**r, "n_logjez": len(infos), "modelo_log": None, "n_modelos_distintos": 0, "n_votos_log": None}
            if not infos:
                return out
            info = infos[-1]
            dest = RAW / uf / Path(info.filename).name
            if args.do_disco and dest.exists():
                jez = dest.read_bytes()
            else:
                jez = ler_membro(url, info)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(jez)
            out.update(modelo_do_log(jez))
            return out

        with ThreadPoolExecutor(args.threads) as pool:
            res = list(pool.map(tarefa, grupo.to_dicts()))
        linhas += res
        print(f"  {uf}: {len(res)} seções, {sum(r['modelo_log'] is not None for r in res)} com modelo "
              f"({time.time() - t0:.0f}s)", flush=True)
    df = pl.DataFrame(linhas, infer_schema_length=None)
    df.write_parquet(saida)
    print(df.group_by("estrato", "modelo_log").len().sort("estrato", "modelo_log"))
    print(f"gravado {saida}")


if __name__ == "__main__":
    main()
