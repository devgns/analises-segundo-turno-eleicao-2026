"""Passada única (streaming, arquivo a arquivo) pelos ~128 milhões de registros de eleitor do log da urna.

Usada pelos capítulos 07 (biometria) e 08 (logs). Cada arquivo parquet de
data/processed/logs_urna/eleitores/ contém seções inteiras (o coletor grava cada seção de uma vez),
então dá para processar um arquivo por vez com pouca memória.

Classes de habilitação (do log, 2º turno):
    B   habilitado por biometria (tipo_habilitacao = "biométrica")
    NT  sem biometria, com >= 1 tentativa de captura de digital (≈ qt_elei_biom_sem_habilitacao do bweb)
    N0  sem biometria e sem nenhuma tentativa (eleitor sem digital cadastrada, ou mesário pulou a captura)
    "sem digital" = NT + N0

Saídas (cache em data/processed/base/):
    log_secoes.parquet       uma linha por seção: contagens, rajadas, janelas, anomalias de relógio
    log_hist_cabine.parquet  histograma nacional de seg_na_cabine por classe
    log_hora.parquet         votos por UF x faixa de 10 min (horário de Brasília) x classe
    log_tentativas.parquet   distribuição de n_tentativas_digital por classe
Uso: uv run python analises/logs_eleitor_agregado.py   (recalcula tudo; ~10–20 min)
"""

from __future__ import annotations

import sys
import time
from functools import lru_cache
from math import comb
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import BASE, PROC  # noqa: E402

DIR = PROC / "logs_urna" / "eleitores"
SEC = ["sg_uf", "cd_municipio_tse", "zona", "secao"]
GAP_LONGO_S = 15 * 60          # ociosidade "longa" antes de um eleitor
JANELA_FINAL = (16, 30)         # votos computados a partir de 16h30 (Brasília; exterior: local)
CABINE_CURTA_S = 5              # "voto relâmpago": até 5 s entre habilitação e voto computado
COLS = ["cd_municipio_tse", "zona", "secao", "ordem", "n_tentativas_digital", "tipo_habilitacao",
        "ts_identificador", "ts_habilitado", "ts_voto_presidente", "ts_computado", "seg_na_cabine",
        "seg_atendimento", "fuso_brasilia_h"]


# ------------------------------------------------------------------ nulo exato da maior sequência
@lru_cache(maxsize=None)
def _arranjos_max_run(n: int, k: int, m: int) -> int:
    """Nº de arranjos de k sucessos em n posições cuja maior sequência de sucessos é <= m."""
    if k == 0:
        return 1
    if m <= 0:
        return 0
    if m >= k:
        return comb(n, k)
    total = 0
    falhas = n - k
    for j in range(1, min(k, falhas + 1) + 1):          # j blocos de sucessos
        # composições de k em j partes, cada parte em 1..m (inclusão–exclusão)
        c = 0
        for i in range(0, j + 1):
            r = k - i * m
            if r < j:
                break
            c += (-1) ** i * comb(j, i) * comb(r - 1, j - 1)
        if c:
            total += comb(falhas + 1, j) * c
    return total


def p_max_run(n: int, k: int, r: int) -> float:
    """P(maior sequência >= r) sob permutação aleatória da ordem dentro da seção (exato)."""
    if r <= 0 or k == 0:
        return 1.0
    if r == 1:
        return 1.0
    total = comb(n, k)
    return (total - _arranjos_max_run(n, k, r - 1)) / total


# ------------------------------------------------------------------ passada por arquivo
def _por_arquivo(path: Path, uf: str):
    df = pl.read_parquet(path, columns=COLS).sort("cd_municipio_tse", "zona", "secao", "ordem")
    # habilitação biométrica = valor explícito; um tipo desconhecido interrompe em vez de virar "biometria" calado
    desconhecidos = df.filter(pl.col("tipo_habilitacao").is_not_null() & (pl.col("tipo_habilitacao") != "biométrica"))
    if desconhecidos.height:
        raise ValueError(f"{path}: tipo_habilitacao desconhecido: {desconhecidos['tipo_habilitacao'].unique().to_list()}")
    h_fin, m_fin = JANELA_FINAL
    fuso = pl.col("fuso_brasilia_h").fill_null(0).cast(pl.Int64)
    df = df.with_columns(
        pl.when(pl.col("tipo_habilitacao") == "biométrica").then(pl.lit("B"))
        .when(pl.col("n_tentativas_digital") > 0).then(pl.lit("NT")).otherwise(pl.lit("N0")).alias("classe"),
        (pl.col("ts_computado") - pl.duration(hours=fuso)).alias("tc_bsb"),
        (pl.col("ts_identificador") - pl.duration(hours=fuso)).alias("ti_bsb"),
    ).with_columns(
        (pl.col("classe") != "B").alias("nb"),
        (pl.col("classe") == "NT").alias("nt"),
        (pl.col("ts_identificador") - pl.col("ts_computado").shift(1).over("cd_municipio_tse", "zona", "secao"))
        .dt.total_seconds().alias("gap_s"),
        (pl.col("ts_computado") < pl.col("ts_computado").shift(1).over("cd_municipio_tse", "zona", "secao"))
        .alias("desordem"),
        ((pl.col("tc_bsb").dt.hour() > h_fin) | ((pl.col("tc_bsb").dt.hour() == h_fin)
                                                  & (pl.col("tc_bsb").dt.minute() >= m_fin))).alias("final"),
    ).with_columns(
        (pl.col("gap_s") >= GAP_LONGO_S).fill_null(False).alias("apos_gap"),
    )

    # sequências (runs) de habilitações sem digital, por seção
    chave_run = (pl.col("nb") != pl.col("nb").shift(1).over("cd_municipio_tse", "zona", "secao")).fill_null(True)
    df = df.with_columns(chave_run.cum_sum().alias("_run"))
    runs = (df.filter("nb").group_by("cd_municipio_tse", "zona", "secao", "_run")
            .agg(pl.len().alias("tam"), pl.col("ti_bsb").first().alias("ini"), pl.col("tc_bsb").last().alias("fim"),
                 pl.col("apos_gap").first().alias("run_apos_gap"), pl.col("final").any().alias("run_final")))
    run_sec = (runs.sort("tam", descending=True)
               .group_by("cd_municipio_tse", "zona", "secao")
               .agg(pl.col("tam").first().alias("max_run_nb"), pl.col("ini").first().alias("max_run_ini"),
                    pl.col("fim").first().alias("max_run_fim"), pl.col("run_final").first().alias("max_run_final"),
                    pl.col("run_apos_gap").first().alias("max_run_apos_gap")))

    cab = pl.col("seg_na_cabine")
    sec = df.group_by("cd_municipio_tse", "zona", "secao").agg(
        pl.len().alias("n"),
        pl.col("nb").sum().alias("n_nb"),
        pl.col("nt").sum().alias("n_nt"),
        (pl.col("classe") == "N0").sum().alias("n_n0"),
        pl.col("final").sum().alias("n_final"),
        (pl.col("final") & pl.col("nb")).sum().alias("n_final_nb"),
        pl.col("apos_gap").sum().alias("n_apos_gap"),
        (pl.col("apos_gap") & pl.col("nb")).sum().alias("n_apos_gap_nb"),
        (cab <= CABINE_CURTA_S).sum().alias("n_cab_curta"),
        ((cab <= CABINE_CURTA_S) & pl.col("nb")).sum().alias("n_cab_curta_nb"),
        cab.filter(pl.col("nb")).median().alias("cab_med_nb"),
        cab.filter(~pl.col("nb")).median().alias("cab_med_b"),
        cab.median().alias("cab_med"),
        # anomalias
        pl.col("ts_habilitado").is_null().sum().alias("a_hab_nulo"),
        pl.col("ts_voto_presidente").is_null().sum().alias("a_pres_nulo"),
        (pl.col("ts_computado") < pl.col("ts_habilitado")).sum().alias("a_comp_antes_hab"),
        (pl.col("ts_habilitado") < pl.col("ts_identificador")).sum().alias("a_hab_antes_ident"),
        (cab < 0).sum().alias("a_cabine_neg"),
        pl.col("desordem").sum().alias("a_desordem"),
        (pl.col("gap_s") < 0).sum().alias("a_sobreposto"),
        (pl.col("tc_bsb").dt.hour() >= 17).sum().alias("n_apos_17_bsb"),
        (pl.col("ti_bsb").dt.hour() < 8).sum().alias("n_antes_8_bsb"),
        pl.col("gap_s").max().alias("max_gap_s"),
        pl.col("ordem").n_unique().alias("ordens_unicas"),
    ).join(run_sec, on=["cd_municipio_tse", "zona", "secao"], how="left").with_columns(
        pl.col("max_run_nb").fill_null(0), pl.lit(uf).alias("sg_uf"))

    cab_c = cab.clip(-1, 301)
    hist = df.group_by("classe", cab_c.alias("seg")).agg(pl.len().alias("n"))
    hora = df.group_by("classe", (pl.col("tc_bsb").dt.truncate("10m").dt.time()).alias("faixa")).agg(
        pl.len().alias("n")).with_columns(pl.lit(uf).alias("sg_uf"))
    tent = df.group_by("classe", "n_tentativas_digital").agg(pl.len().alias("n"))
    return sec, hist, hora, tent


def _adicionar_p(sec: pl.DataFrame) -> pl.DataFrame:
    from scipy.stats import hypergeom

    t0 = time.time()
    trip = sec.select("n", "n_nb", "max_run_nb").unique()
    ps = [p_max_run(int(n), int(k), int(r)) for n, k, r in trip.iter_rows()]
    trip = trip.with_columns(pl.Series("p_run", ps, dtype=pl.Float64))
    print(f"  p exato de {trip.height} trincas (n, k, r) em {time.time() - t0:.0f}s", flush=True)
    sec = sec.join(trip, on=["n", "n_nb", "max_run_nb"], how="left")
    N, K = sec["n"].cast(pl.Int64).to_numpy(), sec["n_nb"].cast(pl.Int64).to_numpy()
    # P(X >= x) para X ~ Hipergeométrica(N, K, m): concentração de "sem digital" na janela
    def sf(x, m):
        x, m = x.cast(pl.Int64).to_numpy(), m.cast(pl.Int64).to_numpy()
        return np.where(m > 0, hypergeom.sf(x - 1, N, K, m), 1.0)
    return sec.with_columns(
        pl.Series("p_final", sf(sec["n_final_nb"], sec["n_final"])),
        pl.Series("p_gap", sf(sec["n_apos_gap_nb"], sec["n_apos_gap"])),
    )


def gerar() -> None:
    secs, hists, horas, tents = [], [], [], []
    arquivos = sorted(DIR.glob("sg_uf=*/*.parquet"))
    t0 = time.time()
    for i, f in enumerate(arquivos, 1):
        uf = f.parent.name.split("=")[1]
        s, h, ho, te = _por_arquivo(f, uf)
        secs.append(s)
        hists.append(h)
        horas.append(ho)
        tents.append(te)
        if i % 20 == 0 or i == len(arquivos):
            print(f"  {i}/{len(arquivos)} arquivos ({time.time() - t0:.0f}s)", flush=True)
    sec = pl.concat(secs)
    dup = sec.group_by(SEC).len().filter(pl.col("len") > 1).height
    assert dup == 0, f"{dup} seções aparecem em mais de um arquivo"
    BASE.mkdir(parents=True, exist_ok=True)
    pl.concat(hists).group_by("classe", "seg").agg(pl.col("n").sum()).sort("classe", "seg").write_parquet(
        BASE / "log_hist_cabine.parquet")
    pl.concat(horas).group_by("sg_uf", "classe", "faixa").agg(pl.col("n").sum()).sort("sg_uf", "faixa").write_parquet(
        BASE / "log_hora.parquet")
    pl.concat(tents).group_by("classe", "n_tentativas_digital").agg(pl.col("n").sum()).sort(
        "classe", "n_tentativas_digital").write_parquet(BASE / "log_tentativas.parquet")
    sec.write_parquet(BASE / "log_secoes_sem_p.parquet")
    print("  agregados salvos; calculando p-valores", flush=True)
    sec = _adicionar_p(sec)
    sec.write_parquet(BASE / "log_secoes.parquet")
    print("  ok", flush=True)


def carregar(recalcular: bool = False) -> dict[str, pl.DataFrame]:
    nomes = ["log_secoes", "log_hist_cabine", "log_hora", "log_tentativas"]
    if recalcular or not all((BASE / f"{n}.parquet").exists() for n in nomes):
        gerar()
    return {n: pl.read_parquet(BASE / f"{n}.parquet") for n in nomes}


if __name__ == "__main__":
    # sanidade do nulo exato contra simulação
    rng = np.random.default_rng(1)
    for n, k, r in [(30, 6, 3), (200, 20, 4)]:
        sims = []
        for _ in range(4000):
            a = np.zeros(n, bool)
            a[rng.choice(n, k, replace=False)] = True
            best = cur = 0
            for v in a:
                cur = cur + 1 if v else 0
                best = max(best, cur)
            sims.append(best >= r)
        print(f"n={n} k={k} r={r}: exato={p_max_run(n, k, r):.4f} simulado={np.mean(sims):.4f}")
    carregar(recalcular=True)
