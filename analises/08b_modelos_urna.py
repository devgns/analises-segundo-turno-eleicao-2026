"""Cap. 08b — Modelos de urna: o padrão de 2022 (UE2009–2015 "a favor de Lula") voltou em 2026?

Pista (pedronauck/eleicoes2022 e relatório do Instituto Voto Legal ao TSE, nov/2022): nas urnas antigas
(UE2009, 2010, 2011, 2013, 2015) Lula teria votação muito diferente da UE2020, só no Norte/Nordeste e
crescendo nas cidades menores; "possível manipulação algorítmica".

Testes (definidos ANTES de olhar os resultados controlados):
  0. Inferência do modelo pelo nº de série da urna (2022 não tem coluna de modelo). Validação com logs
     reais: amostra estratificada (540) + aleatória simples (400) baixadas por 08b_baixar_logs_2022.py;
     em 2026, a regra contra o modelo gravado no log de todas as seções do 2º turno.
  1. Reprodução honesta do padrão bruto (2022 2º turno): Lula por modelo × região × porte; votos por
     minuto de recebimento do BU (gráfico do pedronauck); por que CONTAGENS enganam.
  2. Comparação justa: mesma seção-alvo, mesmo prédio. Regressão da fatia de Lula (p.p.) em dummies de
     modelo com efeito fixo de UF / município / local de votação, ponderada por votos válidos, EP agrupado
     por município. 2022 e 2026, 1º e 2º turnos. Holm sobre a família de testes dentro do local.
  3. Δ 1º→2º turno por modelo (uma manipulação só no 2º turno teria de aparecer como Δ específico).
  4. Realocação 2022→2026: a mesma seção (mesma chave UF/município/zona/seção, mesmo local) trocou de
     urna entre as eleições. Se as urnas antigas inflassem Lula em 2022, as seções que perderam a urna
     antiga deveriam PERDER fatia relativa de Lula em 2026 (diferenças em diferenças, EF local).
     Também: a mesma urna física (mesmo nº de série) em 2022 e 2026 — o "viés" acompanha a urna?
  5. Por região e por porte do município (a alegação é só N/NE, crescendo nas cidades pequenas).

Uso: uv run python analises/08b_modelos_urna.py
(requer data/processed/base/cap08b_validacao_logs_2022*.parquet, gerados por 08b_baixar_logs_2022.py)
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import BASE, CHAVE, REGIAO, bweb, salvar_json, secoes_2026  # noqa: E402

SCRIPT = "analises/08b_modelos_urna.py"
HOJE = date.today().isoformat()
RES: dict = {}
MIN_CLUSTERS = 10  # mínimo de municípios com variação do regressor para reportar EP/IC/p

# Faixas de série -> modelo. Limites pelos vãos da distribuição de nº de série (2022 e 2026) e confirmados
# pelos logs (ver validação). Cada faixa: [início, próximo início).
FAIXAS = [
    (1_000_000, "UE2009"), (1_215_000, "UE2010"), (1_360_000, "UE2011"), (1_650_000, "UE2013"),
    (1_750_000, "UE2015"), (2_000_000, "UE2020"), (2_250_000, "UE2022"), (2_600_000, None),
]
ANTIGAS = ["UE2009", "UE2010", "UE2011", "UE2013", "UE2015"]  # o grupo do pedronauck/IVL
RETIRADAS = ["UE2009", "UE2010", "UE2011"]                   # não existem mais em 2026
MACRO = {"Norte": "N+NE", "Nordeste": "N+NE", "Sudeste": "S+SE+CO", "Sul": "S+SE+CO", "Centro-Oeste": "S+SE+CO"}
PORTES = [(0, "< 50 mil"), (50_000, "50–100 mil"), (100_000, "100–500 mil"), (500_000, "≥ 500 mil")]


def modelo_por_serie(col: str) -> pl.Expr:
    s = pl.col(col).cast(pl.Int64, strict=False)
    e = pl.lit(None, dtype=pl.String)
    for (lo, nome), (hi, _) in reversed(list(zip(FAIXAS[:-1], FAIXAS[1:]))):
        e = pl.when(s.is_between(lo, hi, closed="left")).then(pl.lit(nome)).otherwise(e)
    return e


def porte_expr(col: str) -> pl.Expr:
    e = pl.lit(PORTES[0][1])
    for lo, nome in PORTES[1:]:
        e = pl.when(pl.col(col) >= lo).then(pl.lit(nome)).otherwise(e)
    return e


def salvar(nome, df, titulo, descricao, fonte, **extra):
    if isinstance(df, pl.DataFrame):
        df = df.with_columns(pl.col(pl.Float64, pl.Float32).round(5)).to_dicts()
    salvar_json(f"ch08b/{nome}", {"meta": {"titulo": titulo, "fonte": fonte, "descricao": descricao,
                                           "gerado_em": HOJE, "script": SCRIPT}, "dados": df, **extra})


F22 = "TSE — boletins de urna (bweb) 2022, 2º turno; modelo inferido pelo nº de série da urna"
F26 = "TSE — bweb e logs das urnas 2026"
F2X = "TSE — bweb 2022 e 2026; logs das urnas; cálculo próprio"


# ----------------------------------------------------------------------------- dados
def dados_2022() -> pl.DataFrame:
    def turno(t):
        return bweb(2022, t).filter(pl.col("sg_uf") != "ZZ").select(
            *CHAVE, pl.col("nr_local_votacao").alias(f"local_{t}"),
            pl.col("votos_13").fill_null(0).alias(f"lula_{t}"), pl.col("votos_22").fill_null(0).alias(f"bolso_{t}"),
            pl.col("votos_validos").alias(f"validos_{t}"), pl.col("qt_comparecimento").alias(f"comp_{t}"),
            pl.col("nr_urna_efetivada").cast(pl.Int64, strict=False).alias(f"serie_{t}"),
            pl.col("dt_bu_recebido").alias(f"recebido_{t}"),
        ).collect()
    d = turno(1).join(turno(2), on=CHAVE, how="full", coalesce=True)
    d = d.with_columns(pl.coalesce("local_2", "local_1").alias("local")).drop("local_1", "local_2")
    return d.with_columns(
        modelo_por_serie("serie_1").alias("modelo_1"), modelo_por_serie("serie_2").alias("modelo_2"),
    )


def dados_2026() -> pl.DataFrame:
    s = secoes_2026().filter(pl.col("sg_uf") != "ZZ")
    return s.select(
        *CHAVE, "local", "lula_1", pl.col("flavio_1").alias("adv_1"), "validos_1", "comp_1",
        "lula_2", pl.col("flavio_2").alias("adv_2"), "validos_2", "comp_2",
        pl.col("nr_urna_1").cast(pl.Int64, strict=False).alias("serie_1"),
        pl.col("nr_urna_2").cast(pl.Int64, strict=False).alias("serie_2"),
        pl.col("bu_recebido_2").alias("recebido_2"), pl.col("modelo_urna").alias("modelo_log"),
    ).with_columns(
        modelo_por_serie("serie_1").alias("modelo_1"),
        pl.coalesce("modelo_log", modelo_por_serie("serie_2")).alias("modelo_2"),
    )


def enriquecer(d: pl.DataFrame) -> pl.DataFrame:
    d = d.with_columns(
        (pl.col("sg_uf") + pl.col("cd_municipio_tse")).alias("mun"),
        (pl.col("sg_uf") + pl.col("cd_municipio_tse") + pl.col("zona") + pl.col("local")).alias("local_id"),
        pl.col("sg_uf").replace_strict(REGIAO, default=None).alias("regiao"),
    ).with_columns(
        pl.col("regiao").replace_strict(MACRO, default=None).alias("macro"),
        pl.col("comp_2").sum().over("mun").alias("votantes_mun"),
    )
    return d.with_columns(porte_expr("votantes_mun").alias("porte"))


# ----------------------------------------------------------------------------- 0. validação
def validacao(d22: pl.DataFrame, d26: pl.DataFrame):
    linhas = []
    for arq, rot in (("cap08b_validacao_logs_2022.parquet", "2022 estratificada"),
                     ("cap08b_validacao_logs_2022_simples.parquet", "2022 aleatória simples")):
        v = pl.read_parquet(BASE / arq).with_columns(modelo_por_serie("serie").alias("modelo_inferido"))
        ok = (v["modelo_inferido"] == v["modelo_log"]).sum()
        n = v.height
        lo, hi = stats.beta.ppf(0.025, ok, n - ok + 1) if ok > 0 else 0, (stats.beta.ppf(0.975, ok + 1, n - ok) if ok < n else 1.0)
        RES.setdefault("validacao", {})[rot] = {"n": n, "acertos": int(ok), "acuracia": ok / n, "ic95": [float(lo), float(hi)],
                                                "ufs": v["sg_uf"].n_unique(),
                                                "votos_log_igual_comparecimento": float((v["n_votos_log"] == v["qt_comparecimento"]).mean())}
        # 3ª coluna do log (identificador): o "67305985" citado pelo IVL nos modelos antigos; na UE2020, o nº da urna
        ids = v.with_columns((pl.col("id_log") == "67305985").alias("id_67305985"),
                             (pl.col("id_log") == pl.col("nr_urna_efetivada").str.strip_chars_start("0")).alias("id_igual_serie"))
        RES["validacao"][rot]["id_log"] = ids.group_by("modelo_log").agg(
            pl.len().alias("logs"), pl.col("id_67305985").sum(), pl.col("id_igual_serie").sum()).sort("modelo_log").to_dicts()
        conf = v.group_by("modelo_log", "modelo_inferido").agg(pl.len().alias("secoes"),
                                                                 pl.col("serie").min().alias("serie_min"),
                                                                 pl.col("serie").max().alias("serie_max"))
        linhas.append(conf.with_columns(pl.lit(rot).alias("amostra")))
        print(rot, RES["validacao"][rot])
    # 2026: regra aplicada ao nº de série do 2º turno x modelo gravado no log (todas as seções com log)
    v26 = d26.filter(pl.col("modelo_log").is_not_null()).with_columns(modelo_por_serie("serie_2").alias("modelo_inferido"))
    ok = int((v26["modelo_inferido"] == v26["modelo_log"]).sum())
    RES["validacao"]["2026 (todas as seções com log)"] = {"n": v26.height, "acertos": ok, "acuracia": ok / v26.height}
    linhas.append(v26.group_by("modelo_log", "modelo_inferido").agg(
        pl.len().alias("secoes"), pl.col("serie_2").min().alias("serie_min"), pl.col("serie_2").max().alias("serie_max"))
        .with_columns(pl.lit("2026 (todas as seções com log)").alias("amostra")))
    # urnas de 2022 que reaparecem em 2026: a regra (2022) bate com o modelo do log de 2026?
    m26 = v26.select(pl.col("serie_2").alias("serie"), "modelo_log").unique("serie")
    x = d22.select(pl.col("serie_2").alias("serie"), "modelo_2").join(m26, on="serie")
    ok = int((x["modelo_2"] == x["modelo_log"]).sum())
    RES["validacao"]["2022→2026 mesma urna física"] = {"n": x.height, "acertos": ok, "acuracia": ok / x.height}
    print(RES["validacao"])
    conf = pl.concat(linhas, how="diagonal").sort("amostra", "modelo_log", "modelo_inferido")
    salvar("validacao", conf, "Validação: modelo inferido pelo nº de série × modelo gravado no log da urna",
           "Cada linha: amostra, modelo lido no log, modelo inferido pela faixa de série, nº de seções.",
           "TSE — arquivos de urna 2022 (pleito 407, CDN arqurnatot) e logs 2026; cálculo próprio",
           resumo=RES["validacao"])
    faixas = [{"modelo": nome, "serie_de": lo, "serie_ate": hi - 1} for (lo, nome), (hi, _) in zip(FAIXAS[:-1], FAIXAS[1:])]
    obs = []
    for f in faixas:
        o22 = d22.filter(pl.col("modelo_2") == f["modelo"])
        o26 = d26.filter(pl.col("modelo_2") == f["modelo"])
        obs.append({**f, "secoes_2022": o22.height, "serie_min_2022": o22["serie_2"].min(), "serie_max_2022": o22["serie_2"].max(),
                    "secoes_2026": o26.height, "serie_min_2026": o26["serie_2"].min(), "serie_max_2026": o26["serie_2"].max()})
    salvar("faixas", pl.DataFrame(obs), "Faixas de nº de série por modelo de urna",
           "Faixas usadas para inferir o modelo; mínimos e máximos observados no 2º turno de cada ano.", F2X)
    RES["faixas"] = obs


# ----------------------------------------------------------------------------- 1. bruto
def share(df, by):
    return df.group_by(by).agg(pl.len().alias("secoes"), pl.col("lula_2", "adv_2", "validos_2").sum()).with_columns(
        (pl.col("lula_2") / pl.col("validos_2")).alias("lula")).sort(by)


def bruto(d22, d26):
    a22 = d22.filter(pl.col("validos_2") > 0)
    a26 = d26.filter(pl.col("validos_2") > 0)
    out = []
    for ano, a in ((2022, a22), (2026, a26)):
        for reg in ["Brasil", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]:
            x = a if reg == "Brasil" else a.filter(pl.col("regiao") == reg)
            t = share(x, ["modelo_2"]).with_columns(pl.lit(ano).alias("ano"), pl.lit(reg).alias("regiao"))
            tot = x.select(pl.col("lula_2").sum() / pl.col("validos_2").sum()).item()
            out.append(t.with_columns((pl.col("secoes") / pl.col("secoes").sum()).alias("frac_secoes"),
                                      pl.lit(tot).alias("lula_regiao")))
    t = pl.concat(out).rename({"modelo_2": "modelo"}).select("ano", "regiao", "modelo", "secoes", "frac_secoes", "lula_2", "adv_2", "lula", "lula_regiao")
    print(t.filter(pl.col("regiao").is_in(["Brasil", "Nordeste"])))
    salvar("bruto_regiao", t, "Fatia de Lula por modelo de urna e região (2º turno), sem controles",
           "lula = votos de Lula / válidos nas seções daquele modelo; frac_secoes = fração das seções da região.", F2X)
    RES["bruto_regiao"] = t.to_dicts()

    # grupo antigas x UE2020 (2022) por macro x porte — a figura do pedronauck, em fatia e em contagem
    g = a22.with_columns(pl.when(pl.col("modelo_2").is_in(ANTIGAS)).then(pl.lit("UE2009–2015"))
                         .when(pl.col("modelo_2") == "UE2020").then(pl.lit("UE2020")).alias("grupo")).filter(pl.col("grupo").is_not_null())
    p = (g.group_by("macro", "porte", "grupo").agg(pl.len().alias("secoes"), pl.col("lula_2", "adv_2", "validos_2").sum())
         .with_columns((pl.col("lula_2") / pl.col("validos_2")).alias("lula"),
                       (pl.col("secoes") / pl.col("secoes").sum().over("macro", "porte")).alias("frac_secoes"))
         .sort("macro", "porte", "grupo"))
    # razão de votos de Lula antigas/novas (o "3x") e razão de seções
    piv = p.pivot(on="grupo", index=["macro", "porte"], values=["lula_2", "secoes", "lula"])
    piv = piv.with_columns(
        (pl.col("lula_2_UE2009–2015") / pl.col("lula_2_UE2020")).alias("razao_votos_lula"),
        (pl.col("secoes_UE2009–2015") / pl.col("secoes_UE2020")).alias("razao_secoes"),
        (pl.col("lula_UE2009–2015") - pl.col("lula_UE2020")).alias("dif_fatia"),
    )
    print(piv)
    salvar("bruto_porte", p, "2022, 2º turno: urnas UE2009–2015 × UE2020 por macrorregião e porte do município",
           "Porte = votantes do município no 2º turno. lula = fatia nos válidos; frac_secoes = fração das seções do estrato.",
           F22, razoes=piv.to_dicts())
    RES["bruto_porte"] = piv.to_dicts()

    # gráfico do pedronauck: votos por intervalo de 5 min de recebimento do BU (N+NE), antigas × novas
    def tempo(a, ano, antigas, novas, adv):
        x = a.filter(pl.col("macro") == "N+NE").with_columns(
            pl.when(pl.col("modelo_2").is_in(antigas)).then(pl.lit("antigas")).when(pl.col("modelo_2").is_in(novas))
            .then(pl.lit("novas")).alias("grupo"), pl.col("recebido_2").dt.truncate("5m").alias("t"))
        x = x.filter(pl.col("grupo").is_not_null() & pl.col("t").is_not_null())
        r = (x.group_by("grupo", "t").agg(pl.len().alias("secoes"), pl.col("lula_2", "adv_2", "validos_2").sum())
             .with_columns(pl.col("t").dt.strftime("%H:%M").alias("hora"), (pl.col("lula_2") / pl.col("validos_2")).alias("lula"))
             .sort("grupo", "t").drop("t"))
        r = r.filter(pl.col("hora") <= "23:55").with_columns(pl.lit(ano).alias("ano"))
        return r
    t22 = tempo(a22, 2022, ANTIGAS, ["UE2020"], "bolso_2")
    t26 = tempo(a26, 2026, ["UE2013", "UE2015"], ["UE2020", "UE2022"], "adv_2")
    salvar("tempo", pl.concat([t22, t26]), "Norte + Nordeste: votos por intervalo de 5 min de recebimento do BU, 2º turno",
           "Reprodução do gráfico do pedronauck/eleicoes2022. 2022: antigas = UE2009–2015, novas = UE2020. "
           "2026: antigas = UE2013–2015, novas = UE2020–2022. adv_2 = Bolsonaro (2022) / Flávio (2026).", F2X)
    RES["tempo_totais"] = pl.concat([t22, t26]).group_by("ano", "grupo").agg(pl.col("secoes", "lula_2", "adv_2", "validos_2").sum()).sort("ano", "grupo").to_dicts()


# ----------------------------------------------------------------------------- regressões
def fe_wls(d: pl.DataFrame, y: str, xs: list[str], fe: str | None, peso: str, cluster: str) -> dict:
    """WLS com efeito fixo absorvido por desvio da média PONDERADA do grupo; EP agrupado (CR1)."""
    d = d.drop_nulls([y, *xs, peso, cluster] + ([fe] if fe else [])).filter(pl.col(peso) > 0)
    cols = [y, *xs]
    if fe:
        w = pl.col(peso)
        d = d.with_columns([(pl.col(c) - (pl.col(c) * w).sum().over(fe) / w.sum().over(fe)).alias(c) for c in cols])
    Y = d[y].to_numpy().astype(float)
    X = d.select(xs).to_numpy().astype(float)
    if not fe:
        X = sm.add_constant(X)
    ok = np.abs(X).sum(0) > 1e-12
    if not ok.all():  # dummy sem variação dentro dos grupos: não identificada
        X = X[:, ok]
    g = d[cluster].rank("dense").to_numpy()
    if X.shape[1] == 0:
        return {"n": int(len(Y)), "clusters": int(len(np.unique(g)))}
    # nº de clusters (municípios) em que cada regressor varia: abaixo de MIN_CLUSTERS o coeficiente
    # não é identificado de forma confiável (ex.: N+NE 2026, UE2015×UE2020 só em 3 locais de 1 município)
    n_inf = [int(len(np.unique(g[np.abs(X[:, j]) > 1e-9]))) for j in range(X.shape[1])]
    res = sm.WLS(Y, X, weights=d[peso].to_numpy().astype(float)).fit(cov_type="cluster", cov_kwds={"groups": g})
    nomes = (["const"] if not fe else []) + xs
    nomes = [n for n, k in zip(nomes, ([True] if not fe else []) + list(ok if fe else ok[1:])) if k]
    ci = res.conf_int()
    out = {"n": int(len(Y)), "clusters": int(len(np.unique(g)))}
    for i, nm in enumerate(nomes):
        ok_id = nm == "const" or n_inf[i] >= MIN_CLUSTERS
        out[nm] = {"coef": float(res.params[i]), "ep": float(res.bse[i]) if ok_id else None,
                   "ic_inf": float(ci[i][0]) if ok_id else None, "ic_sup": float(ci[i][1]) if ok_id else None,
                   "p": float(res.pvalues[i]) if ok_id else None, "clusters_inf": n_inf[i], "identificado": ok_id}
    return out


def ponte(d: pl.DataFrame, fe: str | None, col: str, a: list[str], b: list[str]) -> int:
    """Nº de municípios com algum grupo de EF que contém seções dos dois lados (a e b).

    É o que de fato identifica um contraste entre grupos de modelos sob efeito fixo: se urnas antigas e
    novas nunca convivem no mesmo local, a comparação 'dentro do local' não existe, por mais seções que haja.
    """
    if fe is None:
        return 10**6
    g = d.group_by(fe).agg(pl.col(col).is_in(a).any().alias("a"), pl.col(col).is_in(b).any().alias("b"),
                           *([] if fe == "mun" else [pl.col("mun").first()]))
    return g.filter(pl.col("a") & pl.col("b"))["mun"].n_unique()


def marcar(linha: dict, n_ponte: int) -> dict:
    """Anula EP/IC/p quando o contraste entre grupos não é identificado (ponte < MIN_CLUSTERS)."""
    linha["municipios_ponte"] = n_ponte
    if n_ponte < MIN_CLUSTERS and linha.get("identificado", True):
        linha.update({"ep": None, "ic_inf": None, "ic_sup": None, "p": None, "identificado": False})
    return linha


def grupos_modelo(ano):
    return (ANTIGAS, ["UE2020"]) if ano == 2022 else (["UE2013", "UE2015"], ["UE2020", "UE2022"])


def painel(d, ano, turno):
    """Seções do turno com fatia de Lula em p.p. e modelo do turno."""
    v, l = f"validos_{turno}", f"lula_{turno}"
    return d.filter(pl.col(v) > 0).with_columns((100 * pl.col(l) / pl.col(v)).alias("y"), pl.col(f"modelo_{turno}").alias("modelo"))


def dummies(d, modelos, ref):
    xs = []
    for m in modelos:
        if m == ref:
            continue
        d = d.with_columns((pl.col("modelo") == m).cast(pl.Float64).alias(f"m_{m}"))
        xs.append(f"m_{m}")
    return d, xs


def mistos(d, min_secoes=1, min_por_modelo=1):
    """Locais com ≥2 modelos (cada um com ≥ min_por_modelo seções) e ≥ min_secoes seções."""
    c = d.group_by("local_id", "modelo").len()
    c = c.filter(pl.col("len") >= min_por_modelo)
    k = c.group_by("local_id").agg(pl.col("modelo").n_unique().alias("k"), pl.col("len").sum().alias("n"))
    ids = k.filter((pl.col("k") > 1) & (pl.col("n") >= min_secoes))["local_id"]
    return d.filter(pl.col("local_id").is_in(ids.implode()))


def modelos_do_ano(ano):
    return ["UE2009", "UE2010", "UE2011", "UE2013", "UE2015", "UE2020"] if ano == 2022 else ["UE2013", "UE2015", "UE2020", "UE2022"]


def regressoes(d22, d26):
    linhas = []
    amostras = {"Brasil": None, "N+NE": "N+NE", "S+SE+CO": "S+SE+CO"}
    for ano, d in ((2022, d22), (2026, d26)):
        for turno in (1, 2):
            p = painel(d, ano, turno)
            mods = modelos_do_ano(ano)
            for am, mac in amostras.items():
                x = p if mac is None else p.filter(pl.col("macro") == mac)
                x = x.filter(pl.col("modelo").is_in(mods))
                for ref in ("UE2020", "UE2013" if ano == 2026 else "UE2015", *(["UE2022"] if ano == 2026 else [])):
                    xx, xs = dummies(x, mods, ref)
                    specs = [("bruto", None), ("EF UF", "sg_uf"), ("EF município", "mun"), ("EF local", "local_id")] \
                        if ref == "UE2020" else [("EF local", "local_id")]
                    ga, gb = grupos_modelo(ano)
                    for spec, fe in specs:
                        r = fe_wls(xx, "y", xs, fe, f"validos_{turno}", "mun")
                        npt = ponte(xx, fe, "modelo", ga, gb)
                        for m in xs:
                            if m in r:
                                cruza = (m[2:] in ga) != (ref in ga)  # contraste antiga × nova?
                                linha = {"ano": ano, "turno": turno, "amostra": am, "ref": ref, "spec": spec,
                                         "modelo": m[2:], "n": r["n"], **r[m]}
                                linhas.append(marcar(linha, npt if cruza else 10**6))
            print(ano, turno, "ok", flush=True)
    t = pl.DataFrame(linhas)
    # Holm/BH na família principal: EF local, ref UE2020, todas as amostras/anos/turnos
    fam = (pl.col("spec") == "EF local") & (pl.col("ref") == "UE2020") & pl.col("identificado")
    pf = t.filter(fam)["p"].to_numpy()
    holm = multipletests(pf, method="holm")[1]
    fdr = multipletests(pf, method="fdr_bh")[1]
    t = t.with_row_index("i")
    idx = t.filter(fam)["i"].to_list()
    hmap = dict(zip(idx, holm)); fmap = dict(zip(idx, fdr))
    t = t.with_columns(pl.col("i").replace_strict(hmap, default=None, return_dtype=pl.Float64).alias("p_holm"),
                       pl.col("i").replace_strict(fmap, default=None, return_dtype=pl.Float64).alias("q_bh")).drop("i")
    RES["n_testes_familia"] = len(pf)
    with pl.Config(tbl_rows=200, tbl_cols=20):
        print(t.filter(pl.col("ref") == "UE2020").select("ano", "turno", "amostra", "spec", "modelo", "coef", "ic_inf", "ic_sup", "p", "p_holm"))
    salvar("regressoes", t, "Diferença na fatia de Lula (p.p.) por modelo de urna, por especificação",
           "Coeficiente de dummy de modelo vs. referência (ref). y = 100 × Lula/válidos por seção; WLS por válidos; "
           "EF absorvido; EP agrupado por município. p_holm/q_bh: família = todas as linhas 'EF local' com ref UE2020.", F2X)
    RES["regressoes"] = t.to_dicts()
    return t


def identificacao(d22, d26):
    """Em quantos locais cada par de modelos convive (o que identifica o EF local)."""
    out = []
    for ano, d in ((2022, d22), (2026, d26)):
        p = painel(d, ano, 2).filter(pl.col("modelo").is_in(modelos_do_ano(ano)))
        for mac in ("Brasil", "N+NE", "S+SE+CO"):
            x = p if mac == "Brasil" else p.filter(pl.col("macro") == mac)
            pres = x.group_by("local_id").agg(pl.col("modelo").unique())
            mods = modelos_do_ano(ano)
            for i, a in enumerate(mods):
                for b in mods[i + 1:]:
                    n = pres.filter(pl.col("modelo").list.contains(a) & pl.col("modelo").list.contains(b)).height
                    out.append({"ano": ano, "amostra": mac, "modelo_a": a, "modelo_b": b, "locais": n})
            m = mistos(x)
            out.append({"ano": ano, "amostra": mac, "modelo_a": "qualquer", "modelo_b": "misto", "locais": m["local_id"].n_unique(),
                        "secoes": m.height})
            ga, gb = grupos_modelo(ano)
            ab = x.group_by("local_id").agg(pl.col("modelo").is_in(ga).any().alias("a"), pl.col("modelo").is_in(gb).any().alias("b"),
                                            pl.col("mun").first(), pl.len().alias("n")).filter(pl.col("a") & pl.col("b"))
            out.append({"ano": ano, "amostra": mac, "modelo_a": "antiga", "modelo_b": "nova", "locais": ab.height,
                        "secoes": int(ab["n"].sum()), "municipios": ab["mun"].n_unique()})
    t = pl.DataFrame(out, infer_schema_length=None)
    salvar("identificacao", t, "Locais de votação onde dois modelos convivem (2º turno)",
           "Número de locais em que os dois modelos aparecem juntos; é isso que identifica a comparação dentro do local.", F2X)
    RES["identificacao"] = t.to_dicts()


def robustez_2026_ue2013(d22, d26):
    """O sinal de nível UE2013 em 2026 (replicação Codex: +0,76 p.p.): robustez e placebo do 1º turno."""
    out = []
    for ano, d in ((2022, d22), (2026, d26)):
        mods = modelos_do_ano(ano)
        for turno in (1, 2):
            p = painel(d, ano, turno).filter(pl.col("modelo").is_in(mods))
            for rot, kw, peso in (("todos os locais", {}, True), ("sem peso", {}, False),
                                  ("locais ≥ 6 seções", {"min_secoes": 6}, True),
                                  ("≥ 2 seções por modelo no local", {"min_por_modelo": 2}, True)):
                x = mistos(p, **kw) if kw else p
                xx, xs = dummies(x, mods, "UE2020")
                if not peso:
                    xx = xx.with_columns(pl.lit(1.0).alias("um"))
                r = fe_wls(xx, "y", xs, "local_id", f"validos_{turno}" if peso else "um", "mun")
                ga, gb = grupos_modelo(ano)
                npt = ponte(xx, "local_id", "modelo", ga, gb)
                for m in xs:
                    if m in r:
                        out.append(marcar({"ano": ano, "turno": turno, "variante": rot, "modelo": m[2:], "n": r["n"], **r[m]},
                                          npt if m[2:] in ga else 10**6))
    t = pl.DataFrame(out)
    with pl.Config(tbl_rows=200):
        print(t.select("ano", "turno", "variante", "modelo", "coef", "ic_inf", "ic_sup", "p"))
    salvar("robustez", t, "Robustez do efeito de nível por modelo (EF local, ref. UE2020)",
           "Variações: sem peso; só locais com ≥ 6 seções; só locais com ≥ 2 seções de cada modelo presente.", F2X)
    RES["robustez"] = t.to_dicts()


def delta_turnos(d22, d26):
    """Δ (2º − 1º turno) da fatia de Lula por modelo, dentro do local, seções com o mesmo modelo nos 2 turnos."""
    out = []
    for ano, d in ((2022, d22), (2026, d26)):
        mods = modelos_do_ano(ano)
        p = d.filter((pl.col("validos_1") > 0) & (pl.col("validos_2") > 0) & (pl.col("modelo_1") == pl.col("modelo_2"))
                     & pl.col("modelo_2").is_in(mods)).with_columns(
            (100 * (pl.col("lula_2") / pl.col("validos_2") - pl.col("lula_1") / pl.col("validos_1"))).alias("y"),
            pl.col("modelo_2").alias("modelo"))
        RES.setdefault("delta_amostra", {})[ano] = {"secoes": p.height, "mesma_urna": int((p["serie_1"] == p["serie_2"]).sum())}
        for mac in ("Brasil", "N+NE", "S+SE+CO"):
            x = p if mac == "Brasil" else p.filter(pl.col("macro") == mac)
            xx, xs = dummies(x, mods, "UE2020")
            for spec, fe in (("bruto", None), ("EF município", "mun"), ("EF local", "local_id")):
                r = fe_wls(xx, "y", xs, fe, "validos_2", "mun")
                ga, gb = grupos_modelo(ano)
                npt = ponte(xx, fe, "modelo", ga, gb)
                for m in xs:
                    if m in r:
                        out.append(marcar({"ano": ano, "amostra": mac, "spec": spec, "modelo": m[2:], "n": r["n"], **r[m]},
                                          npt if m[2:] in ga else 10**6))
        # médias brutas por modelo
        RES.setdefault("delta_medias", []).extend(
            p.group_by("modelo").agg(pl.len().alias("secoes"), (pl.col("lula_1").sum() / pl.col("validos_1").sum()).alias("lula_1"),
                                     (pl.col("lula_2").sum() / pl.col("validos_2").sum()).alias("lula_2"))
            .with_columns((pl.col("lula_2") - pl.col("lula_1")).alias("delta"), pl.lit(ano).alias("ano")).sort("modelo").to_dicts())
    t = pl.DataFrame(out)
    pf = t.filter((pl.col("spec") == "EF local") & pl.col("identificado"))["p"].to_numpy()
    RES["delta_holm_min"] = float(multipletests(pf, method="holm")[1].min())
    with pl.Config(tbl_rows=100):
        print(t.filter(pl.col("spec") == "EF local"))
    salvar("delta", t, "Δ da fatia de Lula entre turnos (p.p.) por modelo, vs. UE2020",
           "Seções com o mesmo modelo nos dois turnos. y = 100 × (Lula/válidos 2º − Lula/válidos 1º). WLS por válidos do 2º turno; EP por município.",
           F2X, medias=RES["delta_medias"])
    RES["delta"] = t.to_dicts()


# ----------------------------------------------------------------------------- 4. realocação 2022 → 2026
def realocacao(d22, d26):
    a = d22.filter((pl.col("validos_1") > 0) & (pl.col("validos_2") > 0)).select(
        *CHAVE, "local", "local_id", "mun", "macro", "porte", pl.col("modelo_2").alias("mod22"),
        pl.col("serie_2").alias("serie22"),
        (100 * pl.col("lula_2") / pl.col("validos_2")).alias("l22_2"), (100 * pl.col("lula_1") / pl.col("validos_1")).alias("l22_1"),
        pl.col("validos_2").alias("v22"))
    b = d26.filter((pl.col("validos_1") > 0) & (pl.col("validos_2") > 0)).select(
        *CHAVE, pl.col("local").alias("local26"), pl.col("modelo_2").alias("mod26"), pl.col("serie_2").alias("serie26"),
        (100 * pl.col("lula_2") / pl.col("validos_2")).alias("l26_2"), (100 * pl.col("lula_1") / pl.col("validos_1")).alias("l26_1"),
        pl.col("validos_2").alias("v26"))
    j = a.join(b, on=CHAVE, how="inner")
    RES["realocacao_chave"] = {"secoes_2022": a.height, "secoes_2026": b.height, "mesma_chave": j.height,
                               "mesma_chave_mesmo_local": int((j["local"] == j["local26"]).sum())}
    j = j.filter(pl.col("local") == pl.col("local26")).with_columns(
        (pl.col("l26_2") - pl.col("l22_2")).alias("d2"), (pl.col("l26_1") - pl.col("l22_1")).alias("d1"),
        pl.when(pl.col("mod22").is_in(RETIRADAS)).then(pl.lit("UE2009–2011 (retirada)"))
        .when(pl.col("mod22").is_in(["UE2013", "UE2015"])).then(pl.lit("UE2013–2015"))
        .when(pl.col("mod22") == "UE2020").then(pl.lit("UE2020")).alias("g22"),
        pl.when(pl.col("mod26").is_in(["UE2013", "UE2015"])).then(pl.lit("UE2013–2015"))
        .when(pl.col("mod26").is_in(["UE2020", "UE2022"])).then(pl.lit("UE2020–2022")).alias("g26"),
        (pl.col("serie22") == pl.col("serie26")).alias("mesma_urna"),
    ).with_columns(((pl.col("v22") + pl.col("v26")) / 2).alias("w"))
    j = j.filter(pl.col("g22").is_not_null() & pl.col("g26").is_not_null())
    # transições (quantas seções)
    trans = j.group_by("g22", "g26").agg(pl.len().alias("secoes"), pl.col("d2").mean().alias("d2_media_bruta")).sort("g22", "g26")
    print(trans)
    # DiD dentro do local: d2 ~ dummies(g22) + dummies(g26) | EF local. Ref: UE2020 em 2022, UE2020–2022 em 2026.
    j = j.with_columns(
        (pl.col("g22") == "UE2009–2011 (retirada)").cast(pl.Float64).alias("ret22"),
        (pl.col("g22") == "UE2013–2015").cast(pl.Float64).alias("ant22"),
        (pl.col("g26") == "UE2013–2015").cast(pl.Float64).alias("ant26"),
        # tratamento simples: a seção tinha urna antiga (UE2009–2015) em 2022 e nova (UE2020/22) em 2026
        ((pl.col("g22") != "UE2020") & (pl.col("g26") == "UE2020–2022")).cast(pl.Float64).alias("antiga_para_nova"),
        ((pl.col("g22") == "UE2020") & (pl.col("g26") == "UE2013–2015")).cast(pl.Float64).alias("nova_para_antiga"),
    )
    out = []
    amostras = {"Brasil": j, "N+NE": j.filter(pl.col("macro") == "N+NE"), "S+SE+CO": j.filter(pl.col("macro") == "S+SE+CO"),
                "N+NE · < 50 mil": j.filter((pl.col("macro") == "N+NE") & (pl.col("porte") == "< 50 mil")),
                "N+NE · 50–100 mil": j.filter((pl.col("macro") == "N+NE") & (pl.col("porte") == "50–100 mil"))}
    for mac, x in amostras.items():
        for yv, rot in (("d2", "2º turno: 2026 − 2022"), ("d1", "1º turno: 2026 − 2022")):
            for spec, fe in (("EF município", "mun"), ("EF local", "local_id")):
                r = fe_wls(x, yv, ["ret22", "ant22", "ant26"], fe, "w", "mun")
                p22 = ponte(x, fe, "g22", ["UE2009–2011 (retirada)", "UE2013–2015"], ["UE2020"])
                p26 = ponte(x, fe, "g26", ["UE2013–2015"], ["UE2020–2022"])
                for v in ("ret22", "ant22", "ant26"):
                    if v in r:
                        out.append(marcar({"amostra": mac, "y": rot, "spec": spec, "termo": v, "n": r["n"], **r[v]},
                                          p26 if v == "ant26" else p22))
                r = fe_wls(x, yv, ["antiga_para_nova", "nova_para_antiga"], fe, "w", "mun")
                for v in ("antiga_para_nova", "nova_para_antiga"):
                    if v in r:
                        out.append({"amostra": mac, "y": rot, "spec": spec, "termo": v, "n": r["n"], **r[v]})
    t = pl.DataFrame(out)
    with pl.Config(tbl_rows=100):
        print(t.filter(pl.col("spec") == "EF local"))

    # Persistência: diferença (EF município) entre as seções que tinham urna antiga em 2022 e as que tinham
    # UE2020, medida nas QUATRO eleições, nas MESMAS seções. Se a diferença fosse da urna, sumiria em 2026
    # nas seções que trocaram a antiga por uma nova.
    pers = []
    jj = j.with_columns((pl.col("g22") != "UE2020").cast(pl.Float64).alias("antiga22"))
    sub_nova = jj.filter((pl.col("g22") == "UE2020") | (pl.col("g26") == "UE2020–2022"))  # antigas que viraram novas
    for mac, x in {"Brasil": sub_nova, "N+NE": sub_nova.filter(pl.col("macro") == "N+NE"),
                   "N+NE · < 50 mil": sub_nova.filter((pl.col("macro") == "N+NE") & (pl.col("porte") == "< 50 mil")),
                   "S+SE+CO": sub_nova.filter(pl.col("macro") == "S+SE+CO")}.items():
        npt = ponte(x, "mun", "g22", ["UE2009–2011 (retirada)", "UE2013–2015"], ["UE2020"])
        for yv, rot in (("l22_1", "2022 · 1º turno"), ("l22_2", "2022 · 2º turno"), ("l26_1", "2026 · 1º turno"), ("l26_2", "2026 · 2º turno")):
            r = fe_wls(x, yv, ["antiga22"], "mun", "w", "mun")
            if "antiga22" in r:
                pers.append(marcar({"amostra": mac, "eleicao": rot, "n": r["n"], **r["antiga22"]}, npt))
    pers = pl.DataFrame(pers)
    with pl.Config(tbl_rows=100):
        print(pers.select("amostra", "eleicao", "coef", "ic_inf", "ic_sup", "municipios_ponte"))
    salvar("persistencia", pers, "A diferença acompanha o lugar, não a urna",
           "Mesmas seções nos dois anos. Diferença (p.p., EF município) na fatia de Lula entre as seções que em 2022 tinham "
           "urna UE2009–2015 e as que tinham UE2020; amostra = antigas de 2022 que receberam UE2020/2022 em 2026 + seções que já eram UE2020.",
           F2X)
    RES["persistencia"] = pers.to_dicts()
    # contagem de seções por tratamento, para o texto
    RES["realocacao_n"] = {
        "secoes_painel": j.height,
        "antiga_para_nova": int(j["antiga_para_nova"].sum()), "nova_para_antiga": int(j["nova_para_antiga"].sum()),
        "ret22": int(j["ret22"].sum()), "ret22_nne": int(j.filter(pl.col("macro") == "N+NE")["ret22"].sum()),
        "locais_com_ret22_e_ue2020": j.group_by("local_id").agg((pl.col("ret22") > 0).any().alias("a"), (pl.col("g22") == "UE2020").any().alias("b"))
        .filter(pl.col("a") & pl.col("b")).height,
    }
    salvar("realocacao", t, "Realocação de urnas 2022→2026: a fatia de Lula seguiu a urna?",
           "Painel de seções com a mesma chave e o mesmo local nos dois anos. y = variação (p.p.) da fatia de Lula 2026 − 2022. "
           "ret22 = tinha UE2009–2011 em 2022 (todas trocadas); ant22 = tinha UE2013–2015 em 2022; ant26 = tem UE2013–2015 em 2026. "
           "Ref.: UE2020 em 2022 e UE2020/2022 em 2026. Se as antigas tivessem inflado Lula em 2022, ret22 seria negativo.",
           F2X, transicoes=trans.to_dicts(), n=RES["realocacao_n"])
    RES["realocacao"] = t.to_dicts()
    RES["transicoes"] = trans.to_dicts()

    # nível local: fração de seções com urna retirada em 2022 x variação da fatia relativa ao município
    loc = j.group_by("local_id", "mun", "macro").agg(
        pl.col("ret22").mean().alias("frac_ret22"), pl.col("ant26").mean().alias("frac_ant26"), pl.len().alias("n"),
        ((pl.col("d2") * pl.col("w")).sum() / pl.col("w").sum()).alias("d2"), pl.col("w").sum())
    loc = loc.with_columns((pl.col("d2") - (pl.col("d2") * pl.col("w")).sum().over("mun") / pl.col("w").sum().over("mun")).alias("d2_rel"))
    bins = (loc.with_columns(pl.when(pl.col("frac_ret22") == 0).then(pl.lit("0%"))
                             .when(pl.col("frac_ret22") < 0.5).then(pl.lit("1–49%"))
                             .when(pl.col("frac_ret22") < 1).then(pl.lit("50–99%")).otherwise(pl.lit("100%")).alias("faixa"))
            .group_by("macro", "faixa").agg(pl.len().alias("locais"), ((pl.col("d2_rel") * pl.col("w")).sum() / pl.col("w").sum()).alias("d2_rel"),
                                           pl.col("d2_rel").std().alias("dp"))
            .sort("macro", "faixa"))
    print(bins)
    r = fe_wls(loc, "d2", ["frac_ret22", "frac_ant26"], "mun", "w", "mun")
    RES["realocacao_local"] = {"frac_ret22": r.get("frac_ret22"), "frac_ant26": r.get("frac_ant26"), "n": r["n"]}
    salvar("realocacao_locais", bins, "Locais de votação: fração de seções com UE2009–2011 em 2022 × variação relativa da fatia de Lula",
           "d2_rel = variação 2026−2022 (2º turno) da fatia de Lula no local menos a do município (p.p., ponderada).", F2X,
           regressao=RES["realocacao_local"])

    # mesma urna física: o desvio da seção (vs. o local) acompanha a urna quando ela muda de lugar?
    u22 = a.with_columns((pl.col("l22_2") - (pl.col("l22_2") * pl.col("v22")).sum().over("local_id") / pl.col("v22").sum().over("local_id")).alias("r22"),
                         pl.len().over("local_id").alias("n22"))
    b2 = b.join(d26.select(*CHAVE, "mun", "local_id"), on=CHAVE)
    u26 = b2.with_columns((pl.col("l26_2") - (pl.col("l26_2") * pl.col("v26")).sum().over("local_id") / pl.col("v26").sum().over("local_id")).alias("r26"),
                          pl.len().over("local_id").alias("n26"))
    uu = u22.filter(pl.col("n22") >= 2).select("serie22", "mod22", "mun", "local_id", *CHAVE, "r22").join(
        u26.filter(pl.col("n26") >= 2).select(pl.col("serie26").alias("serie22"), pl.col("mun").alias("mun26"),
                                              pl.col("local_id").alias("local26"), pl.col("secao").alias("secao26"), "r26"),
        on="serie22")
    uu = uu.with_columns(pl.when((pl.col("local_id") == pl.col("local26")) & (pl.col("secao") == pl.col("secao26"))).then(pl.lit("mesma seção"))
                         .when(pl.col("local_id") == pl.col("local26")).then(pl.lit("mesmo local, outra seção"))
                         .when(pl.col("mun") == pl.col("mun26")).then(pl.lit("mesmo município, outro local"))
                         .otherwise(pl.lit("outro município")).alias("destino"))
    rows = []
    for dest in ["mesma seção", "mesmo local, outra seção", "mesmo município, outro local", "outro município"]:
        for grp, filt in (("todas", None), ("UE2013–2015", ["UE2013", "UE2015"]), ("UE2020", ["UE2020"])):
            x = uu.filter(pl.col("destino") == dest)
            if filt:
                x = x.filter(pl.col("mod22").is_in(filt))
            if x.height < 30:
                continue
            rho, pv = stats.pearsonr(x["r22"].to_numpy(), x["r26"].to_numpy())
            rows.append({"destino": dest, "modelo_2022": grp, "urnas": x.height, "correlacao": float(rho), "p": float(pv)})
    t = pl.DataFrame(rows)
    print(t)
    salvar("urna_fisica", t, "A mesma urna física em 2022 e 2026: o desvio da seção acompanha a urna?",
           "Desvio = fatia de Lula da seção − média do seu local (2º turno). Correlação entre o desvio de 2022 e o de 2026 da MESMA urna (nº de série), por destino da urna.", F2X)
    RES["urna_fisica"] = t.to_dicts()


# ----------------------------------------------------------------------------- 5. região e porte
def regiao_porte(d22, d26):
    out = []
    for ano, d in ((2022, d22), (2026, d26)):
        antigas = ANTIGAS if ano == 2022 else ["UE2013", "UE2015"]
        novas = ["UE2020"] if ano == 2022 else ["UE2020", "UE2022"]
        for turno in (1, 2):
            p = painel(d, ano, turno).filter(pl.col("modelo").is_in(antigas + novas)).with_columns(
                pl.col("modelo").is_in(antigas).cast(pl.Float64).alias("antiga"))
            for dim, vals in (("regiao", ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]), ("macro_porte", None)):
                if dim == "regiao":
                    grupos = [(v, p.filter(pl.col("regiao") == v)) for v in vals]
                else:
                    grupos = [(f"{m} · {po}", p.filter((pl.col("macro") == m) & (pl.col("porte") == po)))
                              for m in ("N+NE", "S+SE+CO") for _, po in PORTES]
                for rot, x in grupos:
                    br = x.group_by("antiga").agg(pl.col(f"lula_{turno}").sum() / pl.col(f"validos_{turno}").sum())
                    bd = dict(zip(br["antiga"].to_list(), br[f"lula_{turno}"].to_list()))
                    linha = {"ano": ano, "turno": turno, "dim": dim, "grupo": rot, "secoes": x.height,
                             "secoes_antigas": int(x["antiga"].sum()),
                             "bruto": (bd.get(1.0, np.nan) - bd.get(0.0, np.nan)) * 100}
                    for spec, fe in (("mun", "mun"), ("local", "local_id")):
                        try:
                            r = fe_wls(x, "y", ["antiga"], fe, f"validos_{turno}", "mun")
                            c = r.get("antiga")
                        except Exception:  # noqa: BLE001
                            c = None
                        linha.update({f"{spec}_coef": c["coef"] if c else None, f"{spec}_ic_inf": c["ic_inf"] if c else None,
                                      f"{spec}_ic_sup": c["ic_sup"] if c else None, f"{spec}_p": c["p"] if c else None,
                                      f"{spec}_clusters": c["clusters_inf"] if c else 0,
                                      f"{spec}_ident": bool(c and c["identificado"])})
                    loc = mistos(x.with_columns(pl.col("antiga").cast(pl.String).alias("modelo")))
                    linha["locais_mistos"] = loc["local_id"].n_unique()
                    out.append(linha)
    t = pl.DataFrame(out)
    with pl.Config(tbl_rows=100, tbl_cols=20):
        print(t.select("ano", "turno", "grupo", "secoes_antigas", "locais_mistos", "bruto", "mun_coef", "local_coef", "local_ic_inf", "local_ic_sup"))
    salvar("regiao_porte", t, "Urnas antigas × novas: diferença na fatia de Lula (p.p.) por região e por porte",
           "antigas = UE2009–2015 (2022) / UE2013–2015 (2026); novas = UE2020 (2022) / UE2020–2022 (2026). "
           "bruto = diferença simples; mun/local = coeficiente com EF de município / local de votação (IC 95%, EP por município).", F2X)
    RES["regiao_porte"] = t.to_dicts()


def br(x: float, casas: int = 2) -> str:
    return f"{x:.{casas}f}".replace(".", ",").replace("-", "−")


def kpis():
    v = RES["validacao"]
    n_logs = v["2022 estratificada"]["n"] + v["2022 aleatória simples"]["n"]
    ok_logs = v["2022 estratificada"]["acertos"] + v["2022 aleatória simples"]["acertos"]
    tt = {(r["ano"], r["grupo"]): r for r in RES["tempo_totais"]}
    bruto = tt[(2022, "antigas")]["lula_2"] / tt[(2022, "antigas")]["validos_2"] - tt[(2022, "novas")]["lula_2"] / tt[(2022, "novas")]["validos_2"]
    pe = {(r["amostra"], r["eleicao"]): r for r in RES["persistencia"]}
    a, b = pe[("N+NE · < 50 mil", "2022 · 2º turno")], pe[("N+NE · < 50 mil", "2026 · 2º turno")]
    re = next(r for r in RES["realocacao"] if r["amostra"] == "Brasil" and r["termo"] == "ret22"
              and r["spec"] == "EF município" and r["y"].startswith("2º"))
    k = [
        {"rotulo": "Logs de urna de 2022 que confirmam o modelo inferido pelo nº de série", "valor": f"{ok_logs} de {n_logs}",
         "detalhe": "amostra estratificada + amostra aleatória simples"},
        {"rotulo": "N+NE 2022, 2º turno: Lula nas urnas UE2009–2015 menos nas UE2020 (bruto)", "valor": bruto, "formato": "pp",
         "detalhe": "a diferença que aparece nos gráficos do pedronauck", "cor": "lula"},
        {"rotulo": "Cidades < 50 mil do N+NE: diferença das mesmas seções depois de trocar a urna antiga por UE2020/2022", "valor": b["coef"] / 100,
         "formato": "pp", "detalhe": f"era {br(a['coef'], 1)} p.p. em 2022 (comparação dentro do mesmo município)"},
        {"rotulo": "Seções que perderam a UE2009–2011: variação relativa de Lula 2022→2026 (2º turno)", "valor": re["coef"] / 100,
         "formato": "pp", "detalhe": f"IC 95% {br(re['ic_inf'])} a {br(re['ic_sup'])} p.p.; comparação dentro do mesmo município"},
    ]
    salvar_json("ch08b/kpis", k)


def main():
    d22 = enriquecer(dados_2022())
    d26 = enriquecer(dados_2026())
    print("2022", d22.height, d22["modelo_2"].value_counts().sort("modelo_2"))
    print("2026", d26.height, d26["modelo_2"].value_counts().sort("modelo_2"))
    validacao(d22, d26)
    bruto(d22.with_columns(pl.col("bolso_2").alias("adv_2")), d26)
    identificacao(d22, d26)
    regressoes(d22, d26)
    robustez_2026_ue2013(d22, d26)
    delta_turnos(d22, d26)
    realocacao(d22, d26)
    regiao_porte(d22, d26)
    kpis()
    (BASE / "cap08b_resultados.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str))
    print("ok")


if __name__ == "__main__":
    main()
