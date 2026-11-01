"""Capítulo 6 (auxiliar) — horário de recebimento dos BUs de 2022 (DT_BU_RECEBIDO).

O cache compartilhado data/processed/bweb_secao/ano=2022 tem as colunas de data nulas: o layout de 2022 grava as
datas como "dd/mm/aaaa hh:mm:ss", e o parser do baixar_bweb.py espera "aaaa-mm-dd". Para não mexer no cache dos
outros capítulos, este script baixa de novo os zips do 2º turno (e do 1º, opcional) de 2022 — conferindo o SHA-512
publicado pelo TSE — e grava só o que o capítulo 6 precisa:

    data/processed/agregados/cap06_bweb2022_t{N}.parquet
        sg_uf, cd_municipio_tse, zona, secao, dt_bu_recebido, dt_encerramento, dt_emissao_bu, votos_13, votos_22

Uso: uv run python analises/06b_bweb2022_recebido.py [--turno 2]
"""

from __future__ import annotations

import argparse
import importlib.util
import tempfile
import zipfile
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "processed" / "agregados"
RAW = ROOT / "data" / "raw" / "bweb" / "2022"

_spec = importlib.util.spec_from_file_location("baixar_bweb", ROOT / "scripts" / "baixar_bweb.py")
bb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bb)


def data(col: str) -> pl.Expr:
    c = pl.col(col)
    return pl.coalesce(c.str.to_datetime("%d/%m/%Y %H:%M:%S", strict=False),
                       c.str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False)).alias(col.lower())


def processar(zip_path: Path, turno: int) -> pl.DataFrame:
    with tempfile.TemporaryDirectory(dir=RAW) as tmp, zipfile.ZipFile(zip_path) as z:
        nome = next(n for n in z.namelist() if n.endswith(".csv"))
        csv = Path(z.extract(nome, tmp))
        lf = pl.scan_csv(csv, separator=";", encoding="utf8-lossy", infer_schema=False).filter(
            (pl.col("CD_CARGO_PERGUNTA") == "1") & (pl.col("NR_TURNO") == str(turno)))
        chave = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
        return (
            lf.group_by(chave).agg(
                pl.col("DT_BU_RECEBIDO", "DT_ENCERRAMENTO", "DT_EMISSAO_BU").first(),
                pl.col("QT_VOTOS").cast(pl.Int32).filter(pl.col("NR_VOTAVEL") == "13").sum().alias("votos_13"),
                pl.col("QT_VOTOS").cast(pl.Int32).filter(pl.col("NR_VOTAVEL") == "22").sum().alias("votos_22"),
            ).collect(engine="streaming")
            .select(
                pl.col("SG_UF").alias("sg_uf"), pl.col("CD_MUNICIPIO").str.zfill(5).alias("cd_municipio_tse"),
                pl.col("NR_ZONA").str.zfill(4).alias("zona"), pl.col("NR_SECAO").str.zfill(4).alias("secao"),
                data("DT_BU_RECEBIDO"), data("DT_ENCERRAMENTO"), data("DT_EMISSAO_BU"), "votos_13", "votos_22",
            )
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--turno", type=int, default=2)
    args = ap.parse_args()
    disp = bb.recursos(2022, args.turno)
    partes = []
    for uf in sorted(disp):
        url, url_hash = disp[uf]
        dest = RAW / f"turno{args.turno}" / Path(url).name
        status = bb.conferir_sha512(bb.baixar(url, dest), url_hash)
        df = processar(dest, args.turno)
        dest.unlink()
        partes.append(df)
        print(f"2022 T{args.turno} {uf.upper()}: {df.height} seções, {df['dt_bu_recebido'].null_count()} sem data ({status})",
              flush=True)
    AGG.mkdir(parents=True, exist_ok=True)
    out = AGG / f"cap06_bweb2022_t{args.turno}.parquet"
    pl.concat(partes).write_parquet(out)
    print("->", out)


if __name__ == "__main__":
    main()
