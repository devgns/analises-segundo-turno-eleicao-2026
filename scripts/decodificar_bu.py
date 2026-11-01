"""Decodifica os boletins de urna (bu.dat, ASN.1 DER) baixados por baixar_logs_urna.py.

Gera o resultado presidencial por seção: aptos, comparecimento, votos por candidato, brancos e
nulos, além dos horários de abertura/encerramento/emissão do BU (relógio local da urna).

É o plano B enquanto o TSE não publica o bweb (CSV dos BUs) do 2º turno; o bweb traz também a
data/hora de recebimento do BU, que o bu.dat não tem.

Uso:
    uv run scripts/decodificar_bu.py              # todas as UFs já baixadas
    uv run scripts/decodificar_bu.py --uf ac
Saída: data/processed/bu_secao/sg_uf=XX/part-0000.parquet
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import polars as pl

ELEICAO_PRESIDENTE = 6258
ROOT = Path(__file__).resolve().parent.parent
RAW_BU = ROOT / "data" / "raw" / "bu" / "3221"
OUT = ROOT / "data" / "processed" / "bu_secao"

# tipoVoto no BU: 1 = nominal, 2 = branco, 3 = nulo
BRANCO, NULO = 2, 3


def der(b: bytes, i: int = 0, end: int | None = None) -> list:
    """Parser DER mínimo: devolve lista de (tag, valor); valor é lista se construído, bytes se não."""
    end = len(b) if end is None else end
    out = []
    while i < end:
        tag = b[i]
        i += 1
        if tag & 0x1F == 0x1F:  # tag longa
            while b[i] & 0x80:
                i += 1
            i += 1
        n = b[i]
        i += 1
        if n & 0x80:
            k = n & 0x7F
            n = int.from_bytes(b[i : i + k], "big")
            i += k
        v = b[i : i + n]
        out.append((tag, der(b, i, i + n) if tag & 0x20 else v))
        i += n
    return out


def inteiro(v: bytes) -> int:
    return int.from_bytes(v, "big", signed=True)


def ts(v: bytes) -> datetime:
    return datetime.strptime(v.decode(), "%Y%m%dT%H%M%S")


def decodificar(b: bytes) -> dict:
    envelope = der(b)[0][1]
    conteudo = next(v for t, v in envelope if t == 0x04)  # OCTET STRING com o BU
    bu = der(conteudo)[0][1]

    r: dict = {}
    for t, v in bu:
        if t == 0x1B and "ts_emissao_bu" not in r:
            r["ts_emissao_bu"] = ts(v)
        elif t == 0xA0 and len(v) == 2 and all(x[0] == 0x1B for x in v):
            r["ts_abertura"], r["ts_encerramento"] = ts(v[0][1]), ts(v[1][1])

    # resultadosVotacaoPorEleicao: SEQUENCE cujos itens começam com o código da eleição
    for t, v in bu:
        if t != 0x30 or not v or v[0][0] != 0x30:
            continue
        for item in v:
            campos = item[1]
            if not (isinstance(campos, list) and campos and campos[0][0] == 0x02 and inteiro(campos[0][1]) == ELEICAO_PRESIDENTE):
                continue
            r["aptos"] = inteiro(campos[1][1])
            resultado = next(x[1] for x in campos if x[0] == 0x30)[0][1]  # 1º resultadoVotacao
            r["comparecimento"] = next(inteiro(x[1]) for x in resultado if x[0] == 0x02)
            votos = {"votos_13": 0, "votos_22": 0, "votos_brancos": 0, "votos_nulos": 0}
            for totais_cargo in next(x[1] for x in resultado if x[0] == 0x30):
                lista = next(x[1] for x in totais_cargo[1] if x[0] == 0x30)
                for _, vv in lista:
                    d = {tg: val for tg, val in vv}
                    tipo, qtd = inteiro(d[0x81]), inteiro(d[0x82])
                    if tipo == BRANCO:
                        votos["votos_brancos"] += qtd
                    elif tipo == NULO:
                        votos["votos_nulos"] += qtd
                    else:
                        codigo = inteiro(d[0xA3][1][1])  # identificacaoVotavel = {partido, codigo}
                        votos[f"votos_{codigo}"] = votos.get(f"votos_{codigo}", 0) + qtd
            r.update(votos)
            return r
    raise ValueError("eleição presidencial não encontrada no BU")


def processar_uf(pasta: Path) -> tuple[str, int, list[str]]:
    linhas, erros = [], []
    for arq in sorted(pasta.glob("*-bu.dat")):
        mu, zo, se, h = arq.name.split("-")[:4]
        try:
            linhas.append({"cd_municipio_tse": mu, "zona": zo, "secao": se, "hash_prefixo": h,
                           **decodificar(arq.read_bytes())})
        except Exception as exc:  # noqa: BLE001
            erros.append(f"{arq.name}: {exc!r}")
    uf = pasta.name.upper()
    df = pl.DataFrame(linhas, infer_schema_length=None)
    # Urna substituída gera mais de um BU para a mesma seção: fica o de maior comparecimento
    df = df.sort("comparecimento", descending=True).unique(["cd_municipio_tse", "zona", "secao"], keep="first")
    df = df.with_columns((pl.col("votos_13") + pl.col("votos_22")).alias("votos_validos"))
    dest = OUT / f"sg_uf={uf}"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "part-0000.parquet")
    return uf, df.height, erros


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf", action="append")
    args = ap.parse_args()
    pastas = sorted(p for p in RAW_BU.iterdir() if p.is_dir() and (not args.uf or p.name in [u.lower() for u in args.uf]))
    with ProcessPoolExecutor() as pool:
        for uf, n, erros in pool.map(processar_uf, pastas):
            print(f"{uf}: {n} seções, {len(erros)} erros", flush=True)
            for e in erros[:5]:
                print("  ", e)


if __name__ == "__main__":
    main()
