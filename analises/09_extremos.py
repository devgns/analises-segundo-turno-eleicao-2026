"""Capítulo 09 — Seções extremas.

Perguntas:
  1. Quantas seções deram 100% / >=95% / >=90% dos votos válidos a cada candidato no 2º turno de 2026,
     no 1º turno de 2026 (mesmas seções) e no 2º turno de 2022 (seção a seção)?
  2. Esse número é maior do que o esperado por acaso, dado o tamanho de cada seção e a preferência local?
     Nulo: hierárquico beta-binomial. Para cada seção, a proporção esperada é a do restante do local de
     votação (leave-one-out; se o local tiver só essa seção, o restante do município). A seção sorteia a
     sua proporção de uma Beta com essa média e sobredispersão rho estimada por momentos (por região e
     tipo de vizinhança); os votos saem de uma binomial com o nº real de válidos. 400 simulações.
     O mesmo nulo é aplicado ao 1º turno de 2026 e aos dois turnos de 2022 (calibração).
  3. Extremos persistentes x novos (posição no 1º turno).
  4. Peso dos extremos na margem.
  5. Seções que mais destoam do próprio local de votação no 2º turno sem destoar no 1º (diferença-em-
     diferenças em logito, cauda beta-binomial, FDR de Benjamini–Hochberg), em 2026 e, como linha de base,
     em 2022 (1º -> 2º turno de 2022, mesmas seções).

Rodar: uv run python analises/09_extremos.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import ACHADOS, bweb, salvar_json, secoes_2026  # noqa: E402,F401
from comum import REGIAO  # noqa: E402

SCRIPT = "analises/09_extremos.py"
HOJE = date.today().isoformat()
RNG = np.random.default_rng(20261025)
NSIM = 400
LIMIARES = [1.0, 0.95, 0.90]
FONTE = "TSE — boletins de urna por seção (bweb), 2022 e 2026"


def meta(titulo: str, descricao: str) -> dict:
    return {"titulo": titulo, "fonte": FONTE, "descricao": descricao, "gerado_em": HOJE, "script": SCRIPT}


def salvar(nome: str, df: pl.DataFrame | list, titulo: str, descricao: str, **extra):
    if isinstance(df, pl.DataFrame):
        df = df.with_columns(pl.col(pl.Float64, pl.Float32).round(5)).to_dicts()
    salvar_json(f"ch09/{nome}", {"meta": meta(titulo, descricao), "dados": df, **extra})


# ---------------------------------------------------------------- dados
def base_2022() -> pl.DataFrame:
    chave = ["sg_uf", "cd_municipio_tse", "zona", "secao"]
    t = {}
    for turno in (1, 2):
        t[turno] = bweb(2022, turno).select(
            *chave, pl.col("nr_local_votacao").alias("local"),
            pl.col("votos_13").fill_null(0).alias(f"lula_{turno}"),
            pl.col("votos_22").fill_null(0).alias(f"flavio_{turno}"),
            pl.col("votos_validos").alias(f"validos_{turno}"),
            pl.col("qt_comparecimento").alias(f"comp_{turno}"),
            pl.col("qt_aptos").alias(f"aptos_{turno}"),
        ).collect()
    return (t[1].join(t[2].drop("local"), on=chave, how="inner")
            .with_columns(pl.col("sg_uf").replace_strict(REGIAO, default=None).alias("regiao")))


def base_2026() -> pl.DataFrame:
    return secoes_2026().filter(pl.col("pareada")).select(
        "sg_uf", "cd_municipio_tse", "zona", "secao", "local", "nm_municipio", "regiao", "capital",
        "lula_1", "flavio_1", "validos_1", "comp_1", "aptos_1",
        "lula_2", "flavio_2", "validos_2", "comp_2", "aptos_2",
    )


# ---------------------------------------------------------------- vizinhança (leave-one-out)
def loo(df: pl.DataFrame, y: str, n: str, nome: str) -> pl.DataFrame:
    """Proporção do restante do local (ou do município, se o local não tiver outra seção com votos)."""
    loc = ["sg_uf", "cd_municipio_tse", "zona", "local"]
    mun = ["sg_uf", "cd_municipio_tse"]
    return df.with_columns(
        (pl.col(y).sum().over(loc) - pl.col(y)).alias("_yl"),
        (pl.col(n).sum().over(loc) - pl.col(n)).alias("_nl"),
        (pl.col(y).sum().over(mun) - pl.col(y)).alias("_ym"),
        (pl.col(n).sum().over(mun) - pl.col(n)).alias("_nm"),
    ).with_columns(
        (pl.col("_nl") >= 20).alias(f"{nome}_viz_local"),
        pl.when(pl.col("_nl") >= 20).then(pl.col("_yl") / pl.col("_nl"))
        .when(pl.col("_nm") > 0).then(pl.col("_ym") / pl.col("_nm"))
        .otherwise(None).clip(0.002, 0.998).alias(f"{nome}_p"),
    ).drop("_yl", "_nl", "_ym", "_nm")


def rho_momentos(y, n, p, grupos) -> dict:
    """Sobredispersão intraclasse por grupo: E[(y/n-p)^2] = p(1-p)[1/n + rho(1-1/n)]."""
    out = {}
    m = n >= 20
    for g in np.unique(grupos):
        s = m & (grupos == g)
        r = ((y[s] / n[s] - p[s]) ** 2 / (p[s] * (1 - p[s])) - 1 / n[s]).mean() / (1 - 1 / n[s]).mean()
        out[g] = float(np.clip(r, 1e-4, 0.5))
    return out


def simular(y, n, p, rho, nsim=NSIM, rng=RNG):
    """Devolve, por simulação, a contagem de seções acima de cada limiar para cada candidato."""
    phi = 1 / rho - 1
    a, b = p * phi, (1 - p) * phi
    ok = n > 0
    a, b, n_ = a[ok], b[ok], n[ok]
    res = {(c, t): [] for c in ("lula", "flavio") for t in LIMIARES}
    res50 = {(c, t): [] for c in ("lula", "flavio") for t in LIMIARES}
    grande = n_ >= 50
    for _ in range(nsim):
        q = rng.beta(a, b)
        ys = rng.binomial(n_, q)
        share = ys / n_
        for t in LIMIARES:
            L = share >= t - 1e-12
            F = (1 - share) >= t - 1e-12
            res[("lula", t)].append(int(L.sum()))
            res[("flavio", t)].append(int(F.sum()))
            res50[("lula", t)].append(int((L & grande).sum()))
            res50[("flavio", t)].append(int((F & grande).sum()))
    return res, res50


def observado(y, n):
    ok = n > 0
    share = y[ok] / n[ok]
    g = n[ok] >= 50
    o, o50 = {}, {}
    for t in LIMIARES:
        L, F = share >= t - 1e-12, (1 - share) >= t - 1e-12
        o[("lula", t)], o[("flavio", t)] = int(L.sum()), int(F.sum())
        o50[("lula", t)], o50[("flavio", t)] = int((L & g).sum()), int((F & g).sum())
    return o, o50


# ---------------------------------------------------------------- diferença-em-diferenças por local
def did_outliers(df: pl.DataFrame, rotulo: str) -> pl.DataFrame:
    """Seção x restante do local, 2º turno contra 1º turno (proporção de Lula entre os dois finalistas)."""
    d = df.with_columns(
        (pl.col("lula_1") + pl.col("flavio_1")).alias("n1"),
        pl.col("validos_2").alias("n2"),
    ).filter((pl.col("n1") >= 10) & (pl.col("n2") >= 10))
    d = loo(d, "lula_1", "n1", "t1")
    d = loo(d, "lula_2", "n2", "t2")
    d = d.filter(pl.col("t1_p").is_not_null() & pl.col("t2_p").is_not_null())
    lg = lambda x: np.log(x / (1 - x))  # noqa: E731
    y1, n1 = d["lula_1"].to_numpy().astype(float), d["n1"].to_numpy().astype(float)
    y2, n2 = d["lula_2"].to_numpy().astype(float), d["n2"].to_numpy().astype(float)
    p1s = (y1 + 0.5) / (n1 + 1)
    pe = 1 / (1 + np.exp(-(lg(d["t2_p"].to_numpy()) + lg(p1s) - lg(d["t1_p"].to_numpy()))))
    pe = np.clip(pe, 0.002, 0.998)
    viz = d["t2_viz_local"].to_numpy()
    grupos = np.where(viz, "local", "municipio")
    rho = rho_momentos(y2, n2, pe, grupos)
    r = np.array([rho[g] for g in grupos])
    phi = 1 / r - 1
    bb = stats.betabinom(n2.astype(int), pe * phi, (1 - pe) * phi)
    p_sup = bb.sf(y2 - 1)  # P(Y >= y): excesso pró-Lula
    p_inf = bb.cdf(y2)  # P(Y <= y): excesso pró-Flávio
    # BH sobre todos os 2N testes unilaterais
    pv = np.concatenate([p_sup, p_inf])
    m = len(pv)
    ordem = np.argsort(pv)
    q = np.empty(m)
    q[ordem] = np.minimum.accumulate((pv[ordem] * m / np.arange(1, m + 1))[::-1])[::-1]
    q = np.minimum(q, 1)
    N = len(d)
    return d.with_columns(
        pl.Series("p_esperado", pe), pl.Series("p_sup", p_sup), pl.Series("p_inf", p_inf),
        pl.Series("q_lula", q[:N]), pl.Series("q_flavio", q[N:]), pl.Series("rho", r),
        pl.lit(rotulo).alias("eleicao"),
    ).with_columns(
        (pl.col("lula_2") - pl.col("n2") * pl.col("p_esperado")).alias("excesso_lula"),
        (pl.col("lula_1") / pl.col("n1")).alias("p1"),
        (pl.col("lula_2") / pl.col("n2")).alias("p2"),
    ), rho


# ---------------------------------------------------------------- principal
def main():
    s26 = base_2026()
    s22 = base_2022()
    print("seções 2026 pareadas:", len(s26), "| 2022:", len(s22))

    # conjuntos: (rótulo, df, y, n). 1º turno usa a disputa Lula x Flávio (Bolsonaro em 2022)
    conjuntos = [
        ("2026 · 2º turno", s26, "lula_2", "validos_2"),
        ("2026 · 1º turno", s26.with_columns((pl.col("lula_1") + pl.col("flavio_1")).alias("n_fin_1")), "lula_1", "n_fin_1"),
        ("2022 · 2º turno", s22, "lula_2", "validos_2"),
        ("2022 · 1º turno", s22.with_columns((pl.col("lula_1") + pl.col("flavio_1")).alias("n_fin_1")), "lula_1", "n_fin_1"),
    ]
    linhas, hist = [], []
    rhos = {}
    for rot, df, y, n in conjuntos:
        d = loo(df.filter(pl.col(n) > 0), y, n, "v")
        d = d.filter(pl.col("v_p").is_not_null())
        yy, nn, pp = (d[c].to_numpy().astype(float) for c in (y, n, "v_p"))
        grupos = (d["regiao"].fill_null("?") + "|" + d["v_viz_local"].cast(pl.Utf8)).to_numpy()
        rho = rho_momentos(yy, nn, pp, grupos)
        rhos[rot] = rho
        rr = np.array([rho[g] for g in grupos])
        sim, sim50 = simular(yy, nn.astype(int), pp, rr)
        obs, obs50 = observado(yy, nn)
        for (c, t), v in sim.items():
            v = np.array(v)
            v50 = np.array(sim50[(c, t)])
            linhas.append({
                "eleicao": rot, "candidato": c, "limiar": t,
                "observado": obs[(c, t)], "esperado": float(v.mean()),
                "p05": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95)),
                "p_sim": float(((v >= obs[(c, t)]).sum() + 1) / (len(v) + 1)),
                "observado_50": obs50[(c, t)], "esperado_50": float(v50.mean()),
                "p05_50": float(np.percentile(v50, 5)), "p95_50": float(np.percentile(v50, 95)),
            })
            if t == 1.0:
                vals, cont = np.unique(v, return_counts=True)
                for a, b in zip(vals, cont):
                    hist.append({"eleicao": rot, "candidato": c, "contagem": int(a), "freq": int(b) / len(v)})
        print(rot, {k: round(v, 4) for k, v in rho.items()})
    cont = pl.DataFrame(linhas)
    with pl.Config(tbl_rows=50, tbl_cols=20):
        print(cont)
    salvar("contagens", cont, "Seções extremas: observado x nulo beta-binomial",
           f"Contagem de seções com Lula (ou Flávio/Bolsonaro) >= limiar dos votos válidos da disputa; nulo com {NSIM} simulações. *_50 = só seções com >= 50 votos válidos.")
    salvar("hist-nulo", pl.DataFrame(hist), "Distribuição simulada do nº de seções com 100%",
           f"Frequência relativa de cada contagem em {NSIM} simulações do nulo beta-binomial.")

    # ---- caracterização das seções 100% em 2026 (2º turno)
    ext = s26.with_columns(
        (pl.col("lula_2") / pl.col("validos_2")).alias("p2"),
        (pl.col("lula_1") / (pl.col("lula_1") + pl.col("flavio_1"))).alias("p1"),
        (pl.col("lula_1") / pl.col("validos_1")).alias("p1_nominal"),
        (pl.col("comp_2") / pl.col("aptos_2")).alias("comparecimento_2"),
    )
    ext = loo(ext, "lula_2", "validos_2", "viz2")
    ext = loo(ext.with_columns((pl.col("lula_1") + pl.col("flavio_1")).alias("nf1")), "lula_1", "nf1", "viz1")
    cem = ext.filter((pl.col("p2") == 1) | (pl.col("p2") == 0)).with_columns(
        pl.when(pl.col("p2") == 1).then(pl.lit("Lula")).otherwise(pl.lit("Flávio")).alias("candidato"),
    ).select(
        "candidato", "sg_uf", "nm_municipio", "regiao", "zona", "secao", "local", "aptos_2", "comp_2", "validos_2",
        "lula_2", "flavio_2", "comparecimento_2", "lula_1", "flavio_1", "p1", "p1_nominal",
        pl.col("viz2_p").alias("viz_p2"), pl.col("viz1_p").alias("viz_p1"), pl.col("viz2_viz_local").alias("viz_e_local"),
    ).sort("candidato", "validos_2", descending=[False, True])
    print(cem.group_by("candidato", "regiao").len().sort("candidato", "len", descending=True))
    print(cem.group_by("candidato").agg(
        pl.col("validos_2").median().alias("mediana_validos"), pl.col("validos_2").max().alias("max_validos"), pl.col("validos_2").sum().alias("soma_validos"),
        (pl.col("p1") >= 0.95).sum().alias("p1_ge95"), (pl.col("p1") >= 0.90).sum().alias("p1_ge90"),
        (pl.col("p1") == 1).sum().alias("p1_100"), (pl.col("viz_p2") >= 0.9).sum().alias("viz_ge90"),
        pl.col("viz_e_local").sum(),
    ))
    print(cem.group_by("candidato", "sg_uf", "nm_municipio").len().sort("len", descending=True).head(25))
    salvar("secoes-100", cem, "Seções com 100% dos válidos para um candidato — 2º turno de 2026",
           "p1 = fatia de Lula entre Lula e Flávio no 1º turno; viz_p2/viz_p1 = fatia de Lula no restante do local de votação (ou município).")

    # ---- persistência: fatia de Lula no 1º turno das seções extremas do 2º (>= 95%)
    pers = []
    for c, cond, cond1 in [("Lula", pl.col("p2") >= 0.95, pl.col("p1") >= 0.90),
                           ("Flávio", pl.col("p2") <= 0.05, pl.col("p1") <= 0.10)]:
        e = ext.filter(cond & (pl.col("validos_2") > 0))
        pers.append({"candidato": c, "secoes_ge95": len(e), "persistentes_ge90_no_1t": int(e.filter(cond1).height),
                     "novas": int(e.filter(~cond1).height)})
    print(pers)
    # novas extremas (>=95% no 2º, <90% no 1º) por faixa de 1º turno
    faixa = ext.filter(pl.col("validos_2") > 0).with_columns(
        pl.when(pl.col("p2") >= 0.95).then(pl.lit("Lula")).when(pl.col("p2") <= 0.05).then(pl.lit("Flávio"))
        .otherwise(None).alias("candidato"),
    ).filter(pl.col("candidato").is_not_null()).with_columns(
        pl.when(pl.col("candidato") == "Lula").then(pl.col("p1")).otherwise(1 - pl.col("p1")).alias("p1_cand"),
    ).with_columns(((pl.col("p1_cand") * 20).floor().clip(0, 19) / 20).alias("faixa_1t"))
    faixa = faixa.group_by("candidato", "faixa_1t").len().sort("candidato", "faixa_1t")
    salvar("persistencia", faixa, "Seções >= 95% para um candidato no 2º turno de 2026, pela fatia do mesmo candidato no 1º turno",
           "faixa_1t = limite inferior da faixa de 5 p.p. da fatia do candidato entre os dois finalistas, no 1º turno, na mesma seção.",
           resumo=pers)

    # ---- peso na margem
    margem_nac = int(s26["lula_2"].sum() - s26["flavio_2"].sum())
    peso = []
    for t in LIMIARES:
        for c, cond in [("Lula", pl.col("p2") >= t - 1e-12), ("Flávio", (1 - pl.col("p2")) >= t - 1e-12)]:
            e = ext.filter(cond & (pl.col("validos_2") > 0))
            m2 = int(e["lula_2"].sum() - e["flavio_2"].sum())
            m1 = int(e["lula_1"].sum() - e["flavio_1"].sum())
            peso.append({"candidato": c, "limiar": t, "secoes": len(e), "margem_lula_2t": m2, "margem_lula_1t": m1,
                         "ganho_de_margem": m2 - m1, "fracao_margem_nacional": m2 / margem_nac})
    peso = pl.DataFrame(peso)
    print("margem nacional", margem_nac)
    print(peso)
    salvar("peso-margem", peso, "Peso das seções extremas na margem nacional",
           f"Margem de Lula (Lula − Flávio) somada nas seções extremas; margem nacional (seções pareadas) = {margem_nac}.",
           margem_nacional=margem_nac)

    # ---- diferença-em-diferenças por local
    o26, rho26 = did_outliers(s26, "2026")
    o22, rho22 = did_outliers(s22, "2022")
    print("rho DiD 2026", rho26, "2022", rho22)
    res = []
    for o in (o26, o22):
        for alvo in (0.05, 0.01):
            for c, qc, sinal in [("Lula", "q_lula", 1), ("Flávio", "q_flavio", -1)]:
                f = o.filter(pl.col(qc) < alvo)
                res.append({"eleicao": o["eleicao"][0], "fdr": alvo, "direcao": c, "secoes": f.height,
                            "secoes_testadas": o.height, "excesso_votos_lula": float(f["excesso_lula"].sum()),
                            "excesso_margem": float(2 * f["excesso_lula"].sum())})
    res = pl.DataFrame(res)
    print(res)
    salvar("did-resumo", res, "Seções que destoam do próprio local no 2º turno, controlando o 1º (FDR)",
           "Contagem de seções com q (Benjamini–Hochberg) abaixo do alvo, por direção; excesso = votos de Lula acima do esperado (negativo = a favor do adversário). 2022 compara 1º e 2º turnos de 2022.",
           rho_2026=rho26, rho_2022=rho22)

    cols = ["eleicao", "sg_uf", "cd_municipio_tse", "zona", "secao", "local", "n1", "n2", "p1", "t1_p", "p2", "t2_p",
            "p_esperado", "excesso_lula", "q_lula", "q_flavio"]
    mun = s26.select("sg_uf", "cd_municipio_tse", "nm_municipio").unique()
    top = []
    for o in (o26, o22):
        for qc, desc in (("q_lula", True), ("q_flavio", False)):
            top.append(o.sort([qc, "excesso_lula"], descending=[False, desc]).head(25).select(cols)
                       .with_columns(pl.lit("Lula" if qc == "q_lula" else "Flávio/Bolsonaro").alias("favorece"),
                                     pl.min_horizontal("q_lula", "q_flavio").alias("q")))
    top = pl.concat(top).join(mun, on=["sg_uf", "cd_municipio_tse"], how="left").drop("q_lula", "q_flavio")
    with pl.Config(tbl_rows=100, tbl_cols=30, tbl_width_chars=250):
        print(top.filter(pl.col("eleicao") == "2026"))
    salvar("did-top", top, "As seções mais surpreendentes em relação ao 1º turno e ao próprio local de votação",
           "p1/p2 = fatia de Lula na seção (1º turno: entre Lula e Flávio/Bolsonaro); t1_p/t2_p = fatia no restante do local; p_esperado = previsão do 2º turno mantendo a distância da seção ao local no 1º turno (logito); q = valor-q BH.")

    # histograma dos z-escores DiD para 2026 e 2022 (simetria)
    zh = []
    for o in (o26, o22):
        z = stats.norm.isf(np.clip(o["p_sup"].to_numpy(), 1e-300, 1))  # z>0: pró-Lula
        z = np.clip(z, -8, 8)
        h, e = np.histogram(z, bins=np.arange(-8, 8.01, 0.25))
        for a, b in zip(e[:-1], h):
            zh.append({"eleicao": o["eleicao"][0], "z": float(a + 0.125), "secoes": int(b)})
    salvar("did-z", pl.DataFrame(zh), "Distribuição dos desvios de cada seção em relação ao seu local (z), 2026 x 2022",
           "z > 0: seção mais pró-Lula no 2º turno do que o previsto pelo 1º turno e pelo local; truncado em ±8.")


if __name__ == "__main__":
    main()
