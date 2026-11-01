"""Contagem de votos por seção e faixa de 20 minutos (horário de Brasília), a partir dos logs das urnas.

Gera o cache data/processed/agregados/votos_secao_slot20.parquet, usado por 06_horarios.py.
O exterior (ZZ) fica de fora: o horário lá é o local de cada país. O cache só é refeito quando
os logs processados forem mais novos que ele (ou com --recalcular).

Uso:
    uv run python analises/votos_por_faixa.py [--recalcular]
"""

import sys
from pathlib import Path

import polars as pl

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
CHAVE = ["sg_uf", "cd_municipio_tse", "zona", "secao"]


def votos_por_slot(minutos: int = 20, recalcular: bool = False) -> pl.DataFrame:
    cache = PROC / "agregados" / f"votos_secao_slot{minutos}.parquet"
    fontes = list((PROC / "logs_urna" / "eleitores").glob("*/*.parquet"))
    if not fontes:
        raise FileNotFoundError("Nenhum log processado ainda. Rode scripts/baixar_logs_urna.py.")
    mais_novo = max(f.stat().st_mtime for f in fontes)
    if recalcular or not cache.exists() or cache.stat().st_mtime < mais_novo:
        cache.parent.mkdir(parents=True, exist_ok=True)
        (
            pl.scan_parquet(PROC / "logs_urna" / "eleitores" / "**" / "*.parquet", hive_partitioning=True)
            .filter(pl.col("ts_computado_brasilia").is_not_null())
            .group_by(*CHAVE, pl.col("ts_computado_brasilia").dt.truncate(f"{minutos}m").alias("slot"))
            .agg(pl.len().alias("n"))
            .sink_parquet(cache)
        )
    return pl.read_parquet(cache)


if __name__ == "__main__":
    df = votos_por_slot(recalcular="--recalcular" in sys.argv)
    print(f"{df.height:,} linhas (seção × faixa), {df['n'].sum():,} votos")
