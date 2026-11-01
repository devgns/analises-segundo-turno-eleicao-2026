"""Baixa o bweb (CSV dos boletins de urna) do portal de dados abertos do TSE e gera o resultado
presidencial por seção, com todos os candidatos, DT_BU_RECEBIDO (hora em que o TSE recebeu o BU),
biometria, tipo de urna e dados de carga.

Cada zip é conferido contra o SHA-512 publicado pelo TSE antes de ser processado.

Uso:
    uv run scripts/baixar_bweb.py                         # 2026, 2º turno, todas as UFs
    uv run scripts/baixar_bweb.py --ano 2022 --turno 1
    uv run scripts/baixar_bweb.py --turno 1 --uf ac
Saída: data/processed/bweb_secao/ano=AAAA/turno=N/sg_uf=XX/part-0000.parquet
  votos_<NR> para cada candidato, votos_brancos (95), votos_nulos (96), votos_validos (nominais)
"""

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import polars as pl

PACOTE = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=resultados-{ano}-boletim-de-urna"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "bweb"
OUT = ROOT / "data" / "processed" / "bweb_secao"
HEADERS = {"User-Agent": "Mozilla/5.0 (analise-eleicao-2026)"}
NOME_TURNO = {1: "Primeiro turno", 2: "Segundo turno"}
DATAS = ["DT_BU_RECEBIDO", "DT_ABERTURA", "DT_ENCERRAMENTO", "DT_EMISSAO_BU", "DT_CARGA_URNA_EFETIVADA"]
# atributos da seção (repetidos em todas as linhas de votável)
ATRIBUTOS = [
    "NR_LOCAL_VOTACAO", *DATAS, "CD_TIPO_URNA", "DS_TIPO_URNA", "NR_URNA_EFETIVADA",
    "CD_CARGA_1_URNA_EFETIVADA", "CD_CARGA_2_URNA_EFETIVADA", "CD_FLASHCARD_URNA_EFETIVADA",
    "DS_SECOES_AGREGADAS", "NR_JUNTA_APURADORA", "NR_TURMA_APURADORA",
]
CONTAGENS = ["QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "QT_ELEI_BIOM_SEM_HABILITACAO"]
# nomes de colunas do layout de 2022 -> layout de 2026
RENOMEAR_2022 = {"DS_AGREGADAS": "DS_SECOES_AGREGADAS", "QT_ELEITORES_BIOMETRIA_NH": "QT_ELEI_BIOM_SEM_HABILITACAO"}


def ler_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"), strict=False)


def recursos(ano: int, turno: int) -> dict[str, tuple[str, str | None]]:
    """UF -> (url do zip, url do sha512)."""
    zips, hashes = {}, {}
    for r in ler_json(PACOTE.format(ano=ano))["result"]["resources"]:
        m = re.match(r"(\w\w) - (Boletim de Urna|Hash SHA2) - (.+?) -", r["name"])
        if not m or m.group(3) != NOME_TURNO[turno]:
            continue
        uf = m.group(1).lower()
        if m.group(2) == "Hash SHA2":
            hashes[uf] = r["url"]
        elif r["url"].endswith(".zip"):
            zips[uf] = r["url"]
        elif r["url"].endswith(".zip.sha512"):  # erro de cadastro no portal (RR, 2º turno 2026)
            zips[uf] = r["url"].removesuffix(".sha512")
    return {uf: (url, hashes.get(uf)) for uf, url in zips.items()}


def baixar(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=1800) as resp, open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f, 1 << 20)
        tmp.rename(dest)
    return dest


def conferir_sha512(zip_path: Path, url_hash: str | None) -> str:
    if url_hash is None:
        return "sem hash publicado"
    req = urllib.request.Request(url_hash, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        esperado = resp.read().decode().split()[0].lower()
    h = hashlib.sha512()
    with open(zip_path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    if h.hexdigest() != esperado:
        raise SystemExit(f"SHA-512 não confere para {zip_path.name}")
    return "sha512 ok"


def processar(zip_path: Path, ano: int, turno: int, uf: str) -> int:
    with tempfile.TemporaryDirectory(dir=RAW) as tmp, zipfile.ZipFile(zip_path) as z:
        nome = next(n for n in z.namelist() if n.endswith(".csv"))
        csv = Path(z.extract(nome, tmp))
        # latin-1 lido como utf8-lossy: só nomes com acento se perdem, e usamos apenas códigos
        lf = pl.scan_csv(csv, separator=";", encoding="utf8-lossy", infer_schema=False)
        lf = lf.rename({k: v for k, v in RENOMEAR_2022.items() if k in lf.collect_schema()}).filter(
            (pl.col("CD_CARGO_PERGUNTA") == "1") & (pl.col("NR_TURNO") == str(turno))
        )
        chave = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
        secao = lf.group_by(chave).agg(
            *[pl.col(c).first() for c in ATRIBUTOS],
            *[pl.col(c).first().cast(pl.Int32, strict=False) for c in CONTAGENS],
        ).collect(engine="streaming")
        votos = (
            lf.group_by([*chave, "NR_VOTAVEL", "CD_TIPO_VOTAVEL"])
            .agg(pl.col("QT_VOTOS").cast(pl.Int32).sum())
            .collect(engine="streaming")
        )
    # CD_TIPO_VOTAVEL: 1 nominal, 2 branco, 3 nulo, 4 legenda (não existe para presidente)
    validos = votos.filter(pl.col("CD_TIPO_VOTAVEL") == "1").group_by(chave).agg(
        pl.col("QT_VOTOS").sum().alias("votos_validos")
    )
    largo = votos.with_columns(
        pl.when(pl.col("CD_TIPO_VOTAVEL") == "2").then(pl.lit("votos_brancos"))
        .when(pl.col("CD_TIPO_VOTAVEL") == "3").then(pl.lit("votos_nulos"))
        .otherwise(pl.lit("votos_") + pl.col("NR_VOTAVEL"))
        .alias("col")
    ).pivot(on="col", index=chave, values="QT_VOTOS", aggregate_function="sum")
    df = (
        secao.join(largo, on=chave, how="left")
        .join(validos, on=chave, how="left")
        .with_columns(
            pl.col("CD_MUNICIPIO").str.zfill(5).alias("cd_municipio_tse"),
            pl.col("NR_ZONA").str.zfill(4).alias("zona"),
            pl.col("NR_SECAO").str.zfill(4).alias("secao"),
            # 2026 usa aaaa-mm-dd; 2022 usa dd/mm/aaaa
            *[pl.coalesce(pl.col(c).str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
                          pl.col(c).str.to_datetime("%d/%m/%Y %H:%M:%S", strict=False)).alias(c) for c in DATAS],
            pl.col("DS_SECOES_AGREGADAS").replace("#NULO#", None),
        )
        .drop(chave)
        .rename(lambda c: c.lower())
    )
    votos_cols = sorted(c for c in df.columns if c.startswith("votos_"))
    df = df.with_columns(pl.col(votos_cols).fill_null(0))
    dest = OUT / f"ano={ano}" / f"turno={turno}" / f"sg_uf={uf.upper()}"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "part-0000.parquet")
    return df.height


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", type=int, default=2026, choices=[2022, 2026])
    ap.add_argument("--turno", type=int, default=2, choices=[1, 2])
    ap.add_argument("--uf", action="append")
    ap.add_argument("--manter-zip", action="store_true", help="não apaga o zip depois de processar")
    args = ap.parse_args()

    disp = recursos(args.ano, args.turno)
    if not disp:
        raise SystemExit(f"bweb {args.ano} do {NOME_TURNO[args.turno].lower()} não publicado no portal.")
    ufs = [u.lower() for u in args.uf] if args.uf else sorted(disp)
    for uf in ufs:
        if uf not in disp:
            print(f"{uf.upper()}: não publicado")
            continue
        url, url_hash = disp[uf]
        dest_zip = RAW / str(args.ano) / f"turno{args.turno}" / Path(url).name
        status = conferir_sha512(baixar(url, dest_zip), url_hash)
        n = processar(dest_zip, args.ano, args.turno, uf)
        if not args.manter_zip:
            dest_zip.unlink()
        print(f"{args.ano} T{args.turno} {uf.upper()}: {n} seções ({status})", flush=True)


if __name__ == "__main__":
    main()
