"""Base comum das análises: carga e padronização das fontes do TSE.

Gera (e lê de cache) três tabelas canônicas em data/processed/base/:
    secoes_2026.parquet     uma linha por seção, 1º e 2º turno lado a lado + resumo do log da urna (2º turno)
    municipios_2026.parquet uma linha por município, 1º e 2º turno
    municipios_2022.parquet idem para 2022 (linha de base histórica; seções de 2022 não casam com as de 2026)

Convenções de colunas (sufixo _1 = 1º turno, _2 = 2º turno):
    lula, flavio (2022: bolsonaro), cury, renan, caiado, zema, menores (demais), outros (= todos os eliminados),
    brancos, nulos, validos (nominais), comp (comparecimento), aptos, biom_sh (habilitados sem biometria)
O candidato 28 do 1º turno de 2026 teve votos anulados (o painel do TSE os soma aos nulos); aqui também.

Uso: `from comum import *` a partir de analises/ (ou `sys.path.insert`); `python analises/comum.py` regera o cache.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
BASE = PROC / "base"
SITE_DATA = ROOT / "site" / "public" / "data"
ACHADOS = ROOT / "analises" / "achados"
CHAVE = ["sg_uf", "cd_municipio_tse", "zona", "secao"]

REGIAO = {
    **dict.fromkeys(["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MS", "MT"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
    "ZZ": "Exterior",
}

# número do candidato -> nome da coluna
CAND_2026_T1 = {"13": "lula", "22": "flavio", "70": "cury", "14": "renan", "55": "caiado", "30": "zema"}
ANULADOS_2026_T1 = ["28"]
CAND_2022_T1 = {"13": "lula", "22": "bolsonaro", "12": "ciro", "15": "tebet", "44": "soraya", "30": "davila"}
CAND_2026_T2 = {"13": "lula", "22": "flavio"}
CAND_2022_T2 = {"13": "lula", "22": "bolsonaro"}


def bweb(ano: int, turno: int) -> pl.LazyFrame:
    return pl.scan_parquet(
        PROC / "bweb_secao" / f"ano={ano}" / f"turno={turno}" / "**" / "*.parquet", hive_partitioning=True
    ).drop("ano", "turno", strict=False)


def _padronizar(ano: int, turno: int, cand: dict[str, str], anulados: list[str] = ()) -> pl.DataFrame:
    lf = bweb(ano, turno)
    cols = lf.collect_schema().names()
    votos_nom = [c for c in cols if c.startswith("votos_") and c.removeprefix("votos_").isdigit()]
    principais = [f"votos_{n}" for n in cand]
    anul = [f"votos_{n}" for n in anulados if f"votos_{n}" in cols]
    menores = [c for c in votos_nom if c not in principais and c not in anul]
    elim = [c for c in votos_nom if c not in ("votos_13", "votos_22") and c not in anul]
    sfx = f"_{turno}"
    soma = lambda cs: pl.sum_horizontal(cs) if cs else pl.lit(0)  # noqa: E731
    return lf.select(
        *CHAVE,
        pl.col("nr_local_votacao").alias("local"),
        *[pl.col(f"votos_{n}").fill_null(0).alias(nome + sfx) for n, nome in cand.items()],
        *([soma(menores).alias("menores" + sfx), soma(elim).alias("outros" + sfx)] if len(cand) > 2 else []),
        pl.col("votos_brancos").alias("brancos" + sfx),
        (pl.col("votos_nulos") + soma(anul)).alias("nulos" + sfx),
        (pl.col("votos_validos") - soma(anul)).alias("validos" + sfx),
        pl.col("qt_comparecimento").alias("comp" + sfx),
        pl.col("qt_aptos").alias("aptos" + sfx),
        pl.col("qt_elei_biom_sem_habilitacao").alias("biom_sh" + sfx),
        pl.col("dt_abertura").alias("abertura" + sfx),
        pl.col("dt_encerramento").alias("encerramento" + sfx),
        pl.col("dt_emissao_bu").alias("emissao_bu" + sfx),
        pl.col("dt_bu_recebido").alias("bu_recebido" + sfx),
        pl.col("ds_tipo_urna").alias("tipo_urna" + sfx),
        pl.col("nr_urna_efetivada").alias("nr_urna" + sfx),
        pl.col("ds_secoes_agregadas").alias("agregadas" + sfx),
    ).collect()


def _nomes_municipios() -> pl.DataFrame:
    return pl.read_parquet(PROC / "municipio.parquet").select(
        "sg_uf", "cd_municipio_tse", "cd_municipio_ibge", "nm_municipio", "capital"
    )


def _gerar_secoes_2026() -> pl.DataFrame:
    t1 = _padronizar(2026, 1, CAND_2026_T1, ANULADOS_2026_T1)
    t2 = _padronizar(2026, 2, CAND_2026_T2).drop("local")
    logs = (
        pl.scan_parquet(PROC / "logs_urna" / "secoes" / "**" / "*.parquet", hive_partitioning=True)
        .sort("n_votos_log", descending=True)
        .unique(CHAVE, keep="first")
        .select(*CHAVE, "modelo_urna", "fuso_brasilia_h", "n_alertas", "n_erros", "n_habilitacoes_sem_voto",
                "n_votos_log", "ts_urna_pronta", "ts_primeiro_voto", "ts_ultimo_voto")
        .collect()
    )
    return (
        t1.join(t2, on=CHAVE, how="full", coalesce=True)
        .join(logs, on=CHAVE, how="left")
        .join(_nomes_municipios(), on=["sg_uf", "cd_municipio_tse"], how="left")
        .with_columns(
            pl.col("sg_uf").replace_strict(REGIAO, default=None).alias("regiao"),
            (pl.col("lula_1").is_not_null() & pl.col("lula_2").is_not_null()).alias("pareada"),
        )
    )


def _agregar_municipios(secoes: pl.DataFrame) -> pl.DataFrame:
    soma = [c for c in secoes.columns if c.rsplit("_", 1)[-1] in ("1", "2")
            and secoes.schema[c].is_integer() and not c.startswith(("fuso", "n_"))]
    return (
        secoes.group_by("sg_uf", "cd_municipio_tse")
        .agg(pl.col(soma).sum(), pl.len().alias("n_secoes"))
        .join(_nomes_municipios(), on=["sg_uf", "cd_municipio_tse"], how="left")
        .with_columns(pl.col("sg_uf").replace_strict(REGIAO, default=None).alias("regiao"))
        .sort("sg_uf", "cd_municipio_tse")
    )


def _gerar_municipios_2022() -> pl.DataFrame:
    t1 = _padronizar(2022, 1, CAND_2022_T1).drop("local")
    t2 = _padronizar(2022, 2, CAND_2022_T2).drop("local")
    return _agregar_municipios(t1.join(t2, on=CHAVE, how="full", coalesce=True))


def _cache(nome: str, gerar, recalcular: bool) -> pl.DataFrame:
    path = BASE / f"{nome}.parquet"
    if recalcular or not path.exists():
        BASE.mkdir(parents=True, exist_ok=True)
        gerar().write_parquet(path)
    return pl.read_parquet(path)


def secoes_2026(recalcular: bool = False) -> pl.DataFrame:
    return _cache("secoes_2026", _gerar_secoes_2026, recalcular)


def municipios_2026(recalcular: bool = False) -> pl.DataFrame:
    return _cache("municipios_2026", lambda: _agregar_municipios(secoes_2026()), recalcular)


def municipios_2022(recalcular: bool = False) -> pl.DataFrame:
    return _cache("municipios_2022", _gerar_municipios_2022, recalcular)


def _sem_nan(x):
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _sem_nan(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_sem_nan(v) for v in x]
    return x


def salvar_json(nome: str, obj, decimais: int | None = 4) -> Path:
    """Grava site/public/data/<nome>.json (DataFrame vira lista de registros). Floats arredondados."""
    if isinstance(obj, pl.DataFrame):
        if decimais is not None:
            obj = obj.with_columns(pl.col(pl.Float64, pl.Float32).round(decimais))
        obj = obj.to_dicts()
    path = SITE_DATA / f"{nome}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    # NaN/Infinity não são JSON válido (o navegador recusa o arquivo): viram null
    path.write_text(json.dumps(_sem_nan(obj), ensure_ascii=False, default=str, separators=(",", ":"), allow_nan=False))
    return path


if __name__ == "__main__":
    s = secoes_2026(recalcular=True)
    m = municipios_2026(recalcular=True)
    m22 = municipios_2022(recalcular=True)
    print("secoes_2026", s.shape, "pareadas:", s["pareada"].sum())
    print("municipios_2026", m.shape, "municipios_2022", m22.shape)
    print(s.select(pl.col("lula_1", "flavio_1", "outros_1", "lula_2", "flavio_2", "comp_1", "comp_2").sum()))
    print(m22.select(pl.col("lula_1", "bolsonaro_1", "outros_1", "lula_2", "bolsonaro_2").sum()))
