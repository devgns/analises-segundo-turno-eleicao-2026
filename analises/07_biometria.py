"""Capítulo 07 — Biometria: eleitores habilitados sem digital.

Suspeita (versão mais forte): votos de eleitores habilitados sem digital poderiam ter sido "inseridos"
por mesários (liberação manual de eleitores ausentes), a favor de Lula, no 2º turno.

Testes (definidos antes de olhar o resultado):
  (a) correlação, entre seções, da taxa de habilitação sem biometria com a fatia de Lula (2º turno) e da
      variação dessa taxa (2º−1º) com a variação da fatia de Lula, com controles (EF de UF e de município,
      porte, fatia no 1º turno, modelo de urna). EP agrupado por município.
  (b) efeito implícito: se TODO voto sem biometria fosse de Lula, quanto da margem? (teto) versus o que a
      regressão ecológica estima.
  (c) rajadas: maior sequência de habilitações sem digital por seção, com nulo exato de permutação da
      ordem dentro da seção; concentração na última meia hora e logo após longos períodos ociosos
      (hipergeométrica). BH entre seções. Seções sinalizadas pendem mais para Lula que no 1º turno?
      (teste simétrico: e para Flávio?)
  (d) tempo entre habilitação e voto computado (seg_na_cabine) para sem-digital vs biometria.
  (e) seções em que a fração sem biometria salta entre turnos (teste de duas proporções + BH).

Entrada: secoes_2026() (bweb) + agregados do log por eleitor (logs_eleitor_agregado.py).
Saída: site/public/data/ch07/*.json; números impressos para analises/achados/07-biometria.md.
Uso: uv run python analises/07_biometria.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import BASE, salvar_json, secoes_2026  # noqa: E402
from estat_fe import bh, ols_fe  # noqa: E402
from logs_eleitor_agregado import carregar  # noqa: E402

SCRIPT = "analises/07_biometria.py"
HOJE = date.today().isoformat()
FONTE_BU = "TSE — boletins de urna por seção (bweb), 1º e 2º turnos 2026"
FONTE_LOG = "TSE — logs das urnas do 2º turno 2026 (registro por eleitor)"
SEC = ["sg_uf", "cd_municipio_tse", "zona", "secao"]
RES: dict = {}


def salvar(nome, df, titulo, descricao, fonte=FONTE_BU, **extra):
    if isinstance(df, pl.DataFrame):
        df = df.with_columns(pl.col(pl.Float64, pl.Float32).round(5)).to_dicts()
    salvar_json(f"ch07/{nome}", {"meta": {"titulo": titulo, "fonte": fonte, "descricao": descricao,
                                          "gerado_em": HOJE, "script": SCRIPT}, "dados": df, **extra})


def base() -> pl.DataFrame:
    s = secoes_2026()
    return s.with_columns(
        (pl.col("lula_2") / pl.col("validos_2")).alias("lula2"),
        (pl.col("lula_1") / pl.col("validos_1")).alias("lula1"),
        (pl.col("flavio_1") / pl.col("validos_1")).alias("flavio1"),
        (pl.col("biom_sh_2") / pl.col("comp_2")).alias("tx2"),
        (pl.col("biom_sh_1") / pl.col("comp_1")).alias("tx1"),
        pl.col("comp_2").log().alias("log_comp"),
        (pl.col("sg_uf") + pl.col("cd_municipio_tse")).alias("mun"),
        (pl.col("sg_uf") + pl.col("cd_municipio_tse") + pl.col("zona") + pl.col("local")).alias("local_id"),
    ).with_columns(
        (pl.col("lula2") - pl.col("lula1")).alias("dlula"),
        (pl.col("tx2") - pl.col("tx1")).alias("dtx"),
    )


# ------------------------------------------------------------------ totais
def totais(s: pl.DataFrame):
    t = s.select(pl.col("biom_sh_1", "biom_sh_2", "comp_1", "comp_2", "lula_2", "flavio_2").sum()).row(0, named=True)
    t_br = s.filter(pl.col("sg_uf") != "ZZ").select(pl.col("biom_sh_1", "biom_sh_2").sum()).row(0, named=True)
    RES["totais"] = {**t, "taxa_1": t["biom_sh_1"] / t["comp_1"], "taxa_2": t["biom_sh_2"] / t["comp_2"],
                     "biom_sh_2_sem_zz": t_br["biom_sh_2"], "biom_sh_1_sem_zz": t_br["biom_sh_1"],
                     "margem_2": t["lula_2"] - t["flavio_2"]}
    print("TOTAIS", json.dumps(RES["totais"], indent=1, default=str))
    uf = (s.group_by("sg_uf").agg(pl.col("biom_sh_1", "biom_sh_2", "comp_1", "comp_2", "lula_2", "validos_2").sum())
          .with_columns((pl.col("biom_sh_1") / pl.col("comp_1")).alias("taxa_1"),
                        (pl.col("biom_sh_2") / pl.col("comp_2")).alias("taxa_2"),
                        (pl.col("lula_2") / pl.col("validos_2")).alias("lula_2t"))
          .with_columns((pl.col("taxa_2") - pl.col("taxa_1")).alias("delta"))
          .select("sg_uf", "biom_sh_1", "biom_sh_2", "taxa_1", "taxa_2", "delta", "lula_2t").sort("taxa_2", descending=True))
    print(uf)
    r_uf = stats.spearmanr(uf.filter(pl.col("sg_uf") != "ZZ")["taxa_2"], uf.filter(pl.col("sg_uf") != "ZZ")["lula_2t"])
    RES["uf_spearman_taxa_lula"] = {"rho": r_uf.statistic, "p": r_uf.pvalue}
    salvar("uf", uf.rename({"lula_2t": "lula_2_fatia"}), "Habilitação sem biometria por UF",
           "Eleitores com biometria cadastrada habilitados sem digital (qt_elei_biom_sem_habilitacao) / comparecimento.")
    mod = (s.filter(pl.col("modelo_urna").is_not_null()).group_by("modelo_urna")
           .agg(pl.col("biom_sh_1", "biom_sh_2", "comp_1", "comp_2").sum(), pl.len().alias("secoes"))
           .with_columns((pl.col("biom_sh_1") / pl.col("comp_1")).alias("taxa_1"),
                         (pl.col("biom_sh_2") / pl.col("comp_2")).alias("taxa_2")).sort("modelo_urna"))
    print(mod)
    salvar("modelo", mod, "Habilitação sem biometria por modelo de urna (modelo usado no 2º turno)",
           "Taxa = habilitados sem biometria / comparecimento. O modelo vem do log do 2º turno; no 1º turno a seção pode ter usado outra urna.")
    # dentro do mesmo local de votação: modelo explica a taxa?
    m = ols_fe(s.filter(pl.col("sg_uf") != "ZZ"), "tx2", [], "local_id", "mun", dummies=["modelo_urna"])
    RES["modelo_dentro_local"] = m
    print("taxa ~ modelo | local", {k: (round(v["coef"], 5), round(v["p"], 4)) for k, v in m.items() if isinstance(v, dict)})


# ------------------------------------------------------------------ (a) regressões
def regressoes(s: pl.DataFrame):
    d = s.filter(pl.col("pareada") & (pl.col("sg_uf") != "ZZ") & (pl.col("validos_1") > 0) & (pl.col("validos_2") > 0)
                 & (pl.col("comp_1") > 0) & pl.col("modelo_urna").is_not_null())
    RES["n_regressao"] = d.height
    # correlações simples
    cor = {
        "pearson_tx2_lula2": stats.pearsonr(d["tx2"], d["lula2"]).statistic,
        "spearman_tx2_lula2": stats.spearmanr(d["tx2"], d["lula2"]).statistic,
        "pearson_dtx_dlula": stats.pearsonr(d["dtx"], d["dlula"]).statistic,
        "spearman_dtx_dlula": stats.spearmanr(d["dtx"], d["dlula"]).statistic,
        "pearson_tx1_lula1": stats.pearsonr(d["tx1"], d["lula1"]).statistic,
    }
    RES["correlacoes"] = cor
    print("correlações", cor)
    linhas = []
    specs = [
        ("Nível, 2º turno: fatia de Lula ~ taxa sem biometria", "lula2", ["tx2"], None, ["sg_uf", "modelo_urna"]),
        ("Nível, 2º turno + controles do 1º turno (EF UF)", "lula2", ["tx2", "lula1", "flavio1", "log_comp"], None, ["sg_uf", "modelo_urna"]),
        ("Nível, 2º turno + controles do 1º turno (EF município)", "lula2", ["tx2", "lula1", "flavio1", "log_comp"], "mun", ["modelo_urna"]),
        ("Nível, 1º turno (placebo: mesma relação já existia?) (EF município)", "lula1", ["tx1", "log_comp"], "mun", ["modelo_urna"]),
        ("Variação: Δ fatia de Lula ~ Δ taxa (EF UF)", "dlula", ["dtx", "tx1", "lula1", "flavio1", "log_comp"], None, ["sg_uf", "modelo_urna"]),
        ("Variação: Δ fatia de Lula ~ Δ taxa (EF município)", "dlula", ["dtx", "tx1", "lula1", "flavio1", "log_comp"], "mun", ["modelo_urna"]),
        ("Variação: Δ fatia de Lula ~ Δ taxa (EF local de votação)", "dlula", ["dtx", "tx1", "lula1", "flavio1", "log_comp"], "local_id", ["modelo_urna"]),
    ]
    for nome, y, xs, fe, dum in specs:
        r = ols_fe(d, y, xs, fe, "mun", dummies=dum)
        alvo = xs[0]
        c = r[alvo]
        linhas.append({"modelo": nome, "variavel": alvo, "coef": c["coef"], "ic_inf": c["ic_inf"], "ic_sup": c["ic_sup"],
                       "p": c["p"], "n": r["n"], "r2": r["r2"]})
        print(f"{nome}: {alvo} coef={c['coef']:.4f} IC=[{c['ic_inf']:.4f},{c['ic_sup']:.4f}] p={c['p']:.3g} n={r['n']} r2={r['r2']:.3f}")
    RES["regressoes"] = linhas
    salvar("regressoes", pl.DataFrame(linhas), "Taxa de habilitação sem biometria e voto em Lula — regressões por seção",
           "Coeficiente = variação da fatia de Lula (fração) para +1 (100 p.p.) na taxa sem biometria; multiplique por 0,01 para +1 p.p. "
           "EP agrupado por município. Controles: fatia de Lula e de Flávio no 1º turno, log do comparecimento, modelo de urna.")

    # binscatter: Δ taxa vs Δ Lula, ambos sem a média do município
    dm = d.with_columns([(pl.col(c) - pl.col(c).mean().over("mun")).alias(c + "_w") for c in ("dtx", "dlula", "tx2", "lula2")])
    def binsc(x, y, nb=20):
        q = dm.with_columns(pl.col(x).qcut(nb, labels=[str(i) for i in range(nb)], allow_duplicates=True).alias("b"))
        return q.group_by("b").agg(pl.col(x).mean().alias("x"), pl.col(y).mean().alias("y"), pl.len().alias("n")).sort("x")
    b1 = binsc("dtx_w", "dlula_w").with_columns(pl.lit("delta").alias("painel"))
    b2 = binsc("tx2_w", "lula2_w").with_columns(pl.lit("nivel").alias("painel"))
    b0 = (d.with_columns(pl.col("tx2").qcut(20, labels=[str(i) for i in range(20)], allow_duplicates=True).alias("b"))
          .group_by("b").agg(pl.col("tx2").mean().alias("x"), pl.col("lula2").mean().alias("y"), pl.len().alias("n"))
          .sort("x").with_columns(pl.lit("bruto").alias("painel")))
    salvar("binscatter", pl.concat([b0, b2, b1]).drop("b"),
           "Fatia de Lula por vintil da taxa sem biometria",
           "bruto: níveis do 2º turno; nivel: ambos sem a média do município; delta: Δ (2º−1º) de ambos, sem a média do município. Médias por vintil.")
    return d


# ------------------------------------------------------------------ (b) efeito implícito
def efeito_implicito(s: pl.DataFrame, d: pl.DataFrame, reg_nivel: dict):
    t = RES["totais"]
    margem = t["margem_2"]
    # teto 1: todos os 8,6 mi sem biometria seriam votos de Lula inseridos
    teto_total = t["biom_sh_2"]
    # teto 2: só o aumento entre turnos, seção a seção (soma dos Δ positivos)
    dpos = s.select(pl.when(pl.col("biom_sh_2") > pl.col("biom_sh_1")).then(pl.col("biom_sh_2") - pl.col("biom_sh_1"))
                    .otherwise(0).sum()).item()
    dliq = t["biom_sh_2"] - t["biom_sh_1"]
    # ecológico: a fatia de Lula entre sem-biometria vs com biometria, dentro do município (coef do nível com EF município, sem controles)
    r = ols_fe(d, "lula2", ["tx2"], "mun", "mun")
    dif = r["tx2"]["coef"]  # ≈ p_sem - p_com (fatia nos válidos)
    # conta ilustrativa, não causal: biom_sh * dif = votos de Lula "a mais" entre os sem biometria (dif é ecológica,
    # e biom_sh conta comparecimento, não válidos). O efeito sobre a margem Lula−Flávio é o dobro disso.
    implicito = t["biom_sh_2"] * dif
    # mesma regressão no 1º turno (base de comparação)
    r1 = ols_fe(d, "lula1", ["tx1"], "mun", "mun")
    RES["efeito"] = {"margem": margem, "teto_total": teto_total, "teto_aumento_secoes": dpos, "aumento_liquido": dliq,
                     "dif_ecologica_2": dif, "ic_2": [r["tx2"]["ic_inf"], r["tx2"]["ic_sup"]],
                     "dif_ecologica_1": r1["tx1"]["coef"], "ic_1": [r1["tx1"]["ic_inf"], r1["tx1"]["ic_sup"]],
                     "votos_lula_implicitos": implicito, "margem_implicita": 2 * implicito,
                     "frac_margem_implicita": 2 * implicito / margem,
                     "teto_aumento_frac_margem": dpos / margem}
    print("EFEITO", json.dumps(RES["efeito"], indent=1))


# ------------------------------------------------------------------ (c)(d) logs por eleitor
def logs(s: pl.DataFrame):
    L = carregar()
    ls = L["log_secoes"]
    tot = ls.select(pl.col("n", "n_nb", "n_nt").sum()).row(0, named=True)
    j = s.join(ls, on=SEC, how="inner")
    jc = j.filter(pl.col("n") == pl.col("comp_2"))  # log completo
    conf = jc.select(pl.col("biom_sh_2").sum().alias("bweb"), pl.col("n_nt").sum().alias("log_nt"),
                     pl.corr("biom_sh_2", "n_nt").alias("r"), (pl.col("biom_sh_2") == pl.col("n_nt")).mean().alias("igual"),
                     (pl.col("biom_sh_2") - pl.col("n_nt")).abs().le(2).mean().alias("ate2")).row(0, named=True)
    RES["log_conferencia"] = {**tot, **conf, "secoes_log": ls.height, "secoes_log_completo": jc.height}
    print("LOG x BWEB", RES["log_conferencia"])
    tent = L["log_tentativas"]
    print(tent)
    salvar("tentativas", tent, "Tentativas de captura de digital por tipo de habilitação",
           "B = habilitado por biometria; NT = sem biometria após ≥1 tentativa; N0 = sem biometria, nenhuma tentativa.", fonte=FONTE_LOG)

    # horário (Brasília, faixas de 10 min), nacional sem exterior
    h = (L["log_hora"].filter(pl.col("sg_uf") != "ZZ").group_by("faixa", "classe").agg(pl.col("n").sum())
         .pivot(on="classe", index="faixa", values="n").fill_null(0).sort("faixa")
         .with_columns((pl.col("B") + pl.col("NT") + pl.col("N0")).alias("total"))
         .with_columns(((pl.col("NT") + pl.col("N0")) / pl.col("total")).alias("frac_sem_digital"),
                       (pl.col("NT") / pl.col("total")).alias("frac_nt"))
         .filter(pl.col("total") >= 1000)
         .with_columns(pl.col("faixa").cast(pl.String).str.slice(0, 5)))
    print(h)
    salvar("hora", h, "Habilitações sem digital ao longo do dia (horário de Brasília)",
           "Faixas de 10 min pelo horário em que o voto foi computado; exclui exterior e faixas com < 1.000 votos.", fonte=FONTE_LOG)

    # cabine
    hc = L["log_hist_cabine"].with_columns(pl.when(pl.col("classe") == "B").then(pl.lit("B")).otherwise(pl.lit("SD")).alias("g"))
    hc = hc.group_by("g", "seg").agg(pl.col("n").sum()).with_columns((pl.col("n") / pl.col("n").sum().over("g")).alias("frac"))
    cab = {}
    for g in ("B", "SD"):
        x = hc.filter(pl.col("g") == g).sort("seg")
        tot_g = x["n"].sum()
        seg, n = x["seg"].to_numpy(), x["n"].to_numpy()
        cum = np.cumsum(n) / tot_g
        cab[g] = {"n": int(tot_g), "mediana": int(seg[np.searchsorted(cum, 0.5)]),
                  "ate5": float(n[seg <= 5].sum() / tot_g), "ate3": float(n[seg <= 3].sum() / tot_g),
                  "ate2": float(n[seg <= 2].sum() / tot_g), "neg": int(n[seg < 0].sum()), "acima300": float(n[seg > 300].sum() / tot_g)}
    RES["cabine"] = cab
    print("CABINE", cab)
    hcp = hc.filter(pl.col("seg").is_between(0, 120)).pivot(on="g", index="seg", values="frac").fill_null(0).sort("seg")
    salvar("cabine", hcp.rename({"B": "biometria", "SD": "sem_digital"}),
           "Segundos entre a habilitação e o voto computado",
           "Fração dos eleitores de cada grupo por segundo (0–120 s).", fonte=FONTE_LOG)

    # rajadas e janelas: distribuição de p sob o nulo
    jj = j.filter(pl.col("sg_uf") != "ZZ")
    p_run, p_fin, p_gap = jj["p_run"].to_numpy(), jj["p_final"].to_numpy(), jj["p_gap"].to_numpy()
    calib = []
    for lim in (0.05, 0.01, 0.001, 0.0001):
        calib.append({"limiar": lim, "rajada": float((p_run <= lim).mean()), "final": float((p_fin <= lim).mean()),
                      "apos_ocio": float((p_gap <= lim).mean())})
    RES["calibracao_p"] = calib
    print(pl.DataFrame(calib))
    salvar("calibracao", pl.DataFrame(calib), "Fração de seções com p-valor abaixo do limiar, por teste",
           "Sob o nulo (ordem aleatória), a fração esperada é no máximo o próprio limiar (testes exatos discretos são conservadores).",
           fonte=FONTE_LOG)
    jj = jj.with_columns(pl.Series("q_run", bh(p_run)), pl.Series("q_final", bh(p_fin)), pl.Series("q_gap", bh(p_gap)))
    jj = jj.with_columns(pl.min_horizontal("q_run", "q_final", "q_gap").alias("q_min"))
    jj = jj.with_columns((pl.col("dlula") - pl.col("dlula").mean().over("mun")).alias("dlula_w"),
                         (pl.col("q_min") < 0.05).alias("sinal"))
    comp = []
    for nome, filtro in [("rajada", pl.col("q_run") < 0.05), ("ultima_meia_hora", pl.col("q_final") < 0.05),
                         ("apos_ociosidade", pl.col("q_gap") < 0.05), ("qualquer", pl.col("q_min") < 0.05)]:
        a = jj.filter(filtro)["dlula_w"].drop_nulls().to_numpy()
        b = jj.filter(~filtro)["dlula_w"].drop_nulls().to_numpy()
        if len(a) < 2:
            comp.append({"teste": nome, "secoes": len(a)})
            continue
        t_ = stats.ttest_ind(a, b, equal_var=False)
        # teste simétrico: as sinalizadas caem mais na cauda de Lula ou na de Flávio?
        lo, hi = np.quantile(b, [0.1, 0.9])
        ep = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        dif = a.mean() - b.mean()
        comp.append({"teste": nome, "secoes": len(a), "dlula_w_media": float(a.mean()), "dlula_w_demais": float(b.mean()),
                     "diferenca": float(dif), "ic_inf": float(dif - 1.96 * ep), "ic_sup": float(dif + 1.96 * ep),
                     "p": float(t_.pvalue), "cauda_lula": float((a > hi).mean()), "cauda_flavio": float((a < lo).mean())})
    RES["sinalizadas_vs_demais"] = comp
    print(pl.DataFrame(comp))
    salvar("sinalizadas_delta", pl.DataFrame(comp), "Δ da fatia de Lula nas seções sinalizadas vs demais",
           "dlula_w = Δ (2º−1º) da fatia de Lula nos válidos menos a média do município. IC 95% (Welch). "
           "cauda_lula/cauda_flavio = fração das sinalizadas acima do 90º / abaixo do 10º percentil das demais (esperado: 10% cada).",
           fonte=FONTE_LOG + "; " + FONTE_BU)
    RES["n_sinalizadas"] = {k: int(jj.filter(pl.col(k) < 0.05).height) for k in ("q_run", "q_final", "q_gap", "q_min")}
    print("sinalizadas", RES["n_sinalizadas"])
    # regressão: Δ Lula ~ sinal + controles, EF município
    r = ols_fe(jj.with_columns(pl.col("sinal").cast(pl.Float64)).filter(pl.col("pareada")), "dlula",
               ["sinal", "lula1", "flavio1", "log_comp", "tx1"], "mun", "mun")
    RES["reg_sinal"] = r["sinal"]
    print("Δlula ~ sinal", r["sinal"])
    # nível: fração sem digital (log, inclui N0) e voto em Lula, EF município
    jl = jj.filter((pl.col("n") == pl.col("comp_2")) & pl.col("pareada")).with_columns(
        (pl.col("n_nb") / pl.col("n")).alias("tx_sd"), (pl.col("n_n0") / pl.col("n")).alias("tx_n0"),
        (pl.col("n_cab_curta_nb") / pl.col("n")).alias("tx_curta_sd"))
    r2 = ols_fe(jl, "dlula", ["tx_sd", "lula1", "flavio1", "log_comp", "tx1"], "mun", "mun")
    r3 = ols_fe(jl, "dlula", ["tx_curta_sd", "tx_sd", "lula1", "flavio1", "log_comp"], "mun", "mun")
    RES["reg_log"] = {"tx_sd": r2["tx_sd"], "tx_curta_sd": r3["tx_curta_sd"]}
    salvar("regressoes-log", pl.DataFrame([{"variavel": k, **v} for k, v in RES["reg_log"].items()]),
           "Regressões com taxa sem digital medida nos logs",
           "Coeficientes em frações; efeito fixo e erro-padrão agrupado por município. Associação ecológica, não causal.",
           fonte=FONTE_LOG + "; " + FONTE_BU)
    print("Δlula ~ tx_sd", r2["tx_sd"], "\nΔlula ~ tx_curta_sd", r3["tx_curta_sd"])

    # tabela de seções sinalizadas (explorador)
    tab = (jj.sort("q_min").head(1000)
           .with_columns((pl.col("n_nb") / pl.col("n")).alias("frac_sd"),
                         pl.col("max_run_ini").dt.strftime("%H:%M").alias("rajada_inicio"),
                         pl.col("max_run_fim").dt.strftime("%H:%M").alias("rajada_fim"),
                         pl.when(pl.col("q_run") < 0.05).then(pl.lit("rajada")).otherwise(pl.lit("")).alias("t1"),
                         pl.when(pl.col("q_final") < 0.05).then(pl.lit("fim do dia")).otherwise(pl.lit("")).alias("t2"),
                         pl.when(pl.col("q_gap") < 0.05).then(pl.lit("após ociosidade")).otherwise(pl.lit("")).alias("t3"))
           .with_columns(pl.concat_str(["t1", "t2", "t3"], separator=", ").str.replace_all(r"^(, )+|(, )+$", "")
                         .str.replace_all(r"(, ){2,}", ", ").alias("sinal_tipo"))
           .select(pl.col("sg_uf").alias("uf"), pl.col("nm_municipio").alias("municipio"), "zona", "secao",
                   pl.col("n").alias("votos_log"), pl.col("n_nb").alias("sem_digital"), "frac_sd",
                   pl.col("max_run_nb").alias("maior_rajada"), "rajada_inicio", "rajada_fim",
                   pl.col("n_final_nb").alias("sd_ultima_meia_hora"), pl.col("n_final").alias("votos_ultima_meia_hora"),
                   "sinal_tipo", "q_min", "lula1", "lula2", "dlula", "dlula_w")
           .sort("q_min"))
    RES["tabela_sinalizadas_n"] = tab.height
    print(tab.head(20))
    tab = tab.with_columns(pl.when(pl.col("q_min") < 0.05).then(pl.col("sinal_tipo")).otherwise(pl.lit("(não significativa)")).alias("sinal_tipo"))
    salvar("sinalizadas", tab, "As 1.000 seções com sequências/concentrações de habilitação sem digital mais improváveis (q < 0,05 = sinalizada)",
           "Nulo: permutação aleatória da ordem dos eleitores dentro da seção (exato). q = Benjamini–Hochberg sobre ~499 mil seções. "
           "dlula_w = Δ da fatia de Lula menos a média do município.", fonte=FONTE_LOG + "; " + FONTE_BU)
    return jj


def composicao_rajadas(jj: pl.DataFrame):
    """Nas seções sinalizadas por rajada: a sequência é de 'falhou após tentativas' (NT) ou 'sem tentativa' (N0)?"""
    from comum import PROC
    fl = jj.filter(pl.col("q_run") < 0.05).select("sg_uf", "cd_municipio_tse", "zona", "secao", "max_run_nb", "n", "biom_sh_1", "comp_1", "biom_sh_2")
    linhas = []
    for (uf,), g in fl.group_by("sg_uf"):
        e = (pl.scan_parquet(PROC / "logs_urna" / "eleitores" / f"sg_uf={uf}" / "*.parquet")
             .join(g.select("cd_municipio_tse", "zona", "secao").lazy(), on=["cd_municipio_tse", "zona", "secao"])
             .select("cd_municipio_tse", "zona", "secao", "ordem", "tipo_habilitacao", "n_tentativas_digital").collect())
        for (mu, zo, se), x in e.group_by("cd_municipio_tse", "zona", "secao"):
            x = x.sort("ordem")
            nb = x["tipo_habilitacao"].is_null().to_list()
            melhor, ini, cur, st = 0, 0, 0, 0
            for i, v in enumerate(nb):
                cur = cur + 1 if v else 0
                if cur == 1:
                    st = i
                if cur > melhor:
                    melhor, ini = cur, st
            run = x[ini:ini + melhor]
            linhas.append({"sg_uf": uf, "run": melhor, "run_n0": int((run["n_tentativas_digital"] == 0).sum()),
                           "run_4mais": int((run["n_tentativas_digital"] >= 4).sum()), "ate_o_fim": ini + melhor == x.height})
    d = pl.DataFrame(linhas)
    t = fl.select(pl.col("biom_sh_1").sum(), pl.col("comp_1").sum(), pl.col("biom_sh_2").sum(), pl.col("n").sum()).row(0, named=True)
    RES["rajadas_composicao"] = {"secoes": d.height, "eleitores_nas_rajadas": int(d["run"].sum()),
                                 "frac_n0": float(d["run_n0"].sum() / d["run"].sum()),
                                 "frac_4_tentativas": float(d["run_4mais"].sum() / d["run"].sum()),
                                 "secoes_rajada_ate_o_fim": int(d["ate_o_fim"].sum()),
                                 "taxa_bweb_1": t["biom_sh_1"] / t["comp_1"], "taxa_bweb_2": t["biom_sh_2"] / t["n"]}
    print("COMPOSICAO RAJADAS", RES["rajadas_composicao"])


# ------------------------------------------------------------------ (e) saltos entre turnos
def saltos(s: pl.DataFrame):
    d = s.filter(pl.col("pareada") & (pl.col("sg_uf") != "ZZ") & (pl.col("comp_1") > 0) & (pl.col("comp_2") > 0))
    x1, n1, x2, n2 = (d[c].cast(pl.Float64).to_numpy() for c in ("biom_sh_1", "comp_1", "biom_sh_2", "comp_2"))
    p = (x1 + x2) / (n1 + n2)
    se = np.sqrt(np.clip(p * (1 - p) * (1 / n1 + 1 / n2), 1e-12, None))
    z = (x2 / n2 - x1 / n1) / se
    pv = stats.norm.sf(z)  # unilateral: aumento
    q = bh(pv)
    d = d.with_columns(pl.Series("z", z), pl.Series("q", q)).with_columns(
        (pl.col("dlula") - pl.col("dlula").mean().over("mun")).alias("dlula_w"))
    sal = d.filter(pl.col("q") < 0.05)
    a, b = sal["dlula_w"].to_numpy(), d.filter(pl.col("q") >= 0.05)["dlula_w"].to_numpy()
    t_ = stats.ttest_ind(a, b, equal_var=False)
    # simétrico: quedas da taxa
    qd = bh(stats.norm.cdf(z))
    queda = d.filter(pl.Series(qd < 0.05))
    RES["saltos"] = {"n_aumento": sal.height, "n_queda": queda.height, "dlula_w_aumento": float(a.mean()),
                     "dlula_w_demais": float(b.mean()), "p": float(t_.pvalue),
                     "dlula_w_queda": float(queda["dlula_w"].mean()) if queda.height else None,
                     "biom_extra_aumento": int((sal["biom_sh_2"] - sal["biom_sh_1"]).sum())}
    print("SALTOS", RES["saltos"])
    # binscatter de z vs dlula_w (já salvo o Δ no binscatter); tabela dos saltos
    tab = (sal.sort("z", descending=True).head(1500)
           .select(pl.col("sg_uf").alias("uf"), pl.col("nm_municipio").alias("municipio"), "zona", "secao",
                   "biom_sh_1", "comp_1", "biom_sh_2", "comp_2", "tx1", "tx2", "z", "lula1", "lula2", "dlula", "dlula_w"))
    salvar("saltos", tab, "Seções em que a habilitação sem biometria saltou do 1º para o 2º turno (q < 0,05)",
           "Teste de duas proporções unilateral por seção; q de Benjamini–Hochberg. Ordenado por z.")


def main():
    s = base()
    totais(s)
    d = regressoes(s)
    efeito_implicito(s, d, {})
    jj = logs(s)
    composicao_rajadas(jj)
    saltos(s)
    t = RES["totais"]
    kpis = [
        {"rotulo": "Habilitados sem biometria, 2º turno", "valor": t["biom_sh_2"], "formato": "num",
         "detalhe": f"{t['taxa_2'] * 100:.2f}% do comparecimento".replace(".", ",")},
        {"rotulo": "Mesmo indicador no 1º turno", "valor": t["biom_sh_1"], "formato": "num",
         "detalhe": f"{t['taxa_1'] * 100:.2f}% do comparecimento".replace(".", ",")},
        {"rotulo": "Margem de Lula no 2º turno", "valor": t["margem_2"], "formato": "num", "detalhe": "votos", "cor": "lula"},
        {"rotulo": "Seções com rajada/concentração (q < 0,05)", "valor": RES["n_sinalizadas"]["q_min"], "formato": "num",
         "detalhe": "de ~499 mil, com nulo de permutação"},
    ]
    salvar("kpis", kpis, "Números-chave do capítulo 7", "")
    (BASE / "cap07_resultados.json").write_text(json.dumps(RES, indent=1, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
