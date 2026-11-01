"""Capítulo 08 — Os logs das urnas: modelos, alertas, substituições (e outros logs).

Testes (definidos antes de olhar):
  1. Modelo de urna (UE2013/2015/2020/2022): fatia de Lula e Δ entre turnos por modelo, bruto e
     controlado. Como os modelos são distribuídos geograficamente, o teste limpo é DENTRO do mesmo local de
     votação onde modelos diferentes convivem (experimento natural): Δ ~ modelo | EF local.
  2. Seções com n_votos_log < comparecimento (1.435; −157.290 votos): são substituições de urna? Reconciliação
     com os logs internos do log.jez (analises/08_substituicoes.py). Δ da fatia de Lula vs seções do mesmo município.
  3. Alertas, erros e habilitações sem voto: distribuições e relação com Δ.
  4. Relógio: urna pronta antes das 8h (Brasília), abertura tardia, votos após 17h, ordem dos eventos.
  5. tipo_urna no bweb (Apurada/contingência/voto manual) nos dois turnos.
  6. Esquisitices do log por eleitor: voto computado antes da habilitação, habilitação ausente, ordem fora
     de sequência, eleitores sobrepostos, votos antes das 8h etc. (contagens, mesmo que minúsculas).

Uso: uv run python analises/08_logs.py   (requer logs_eleitor_agregado.py e 08_substituicoes.py já rodados)
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
from estat_fe import ols_fe  # noqa: E402
from logs_eleitor_agregado import carregar  # noqa: E402

SCRIPT = "analises/08_logs.py"
HOJE = date.today().isoformat()
FONTE = "TSE — logs das urnas e boletins de urna (bweb), 2º turno 2026"
SEC = ["sg_uf", "cd_municipio_tse", "zona", "secao"]
RES: dict = {}


def salvar(nome, df, titulo, descricao, fonte=FONTE, **extra):
    if isinstance(df, pl.DataFrame):
        df = df.with_columns(pl.col(pl.Float64, pl.Float32).round(5)).to_dicts()
    salvar_json(f"ch08/{nome}", {"meta": {"titulo": titulo, "fonte": fonte, "descricao": descricao,
                                          "gerado_em": HOJE, "script": SCRIPT}, "dados": df, **extra})


def base() -> pl.DataFrame:
    s = secoes_2026()
    bsb = lambda c: (pl.col(c) - pl.duration(hours=pl.col("fuso_brasilia_h").fill_null(0).cast(pl.Int64)))  # noqa: E731
    return s.with_columns(
        (pl.col("lula_2") / pl.col("validos_2")).alias("lula2"),
        (pl.col("lula_1") / pl.col("validos_1")).alias("lula1"),
        (pl.col("flavio_1") / pl.col("validos_1")).alias("flavio1"),
        pl.col("comp_2").log().alias("log_comp"),
        (pl.col("sg_uf") + pl.col("cd_municipio_tse")).alias("mun"),
        (pl.col("sg_uf") + pl.col("cd_municipio_tse") + pl.col("zona") + pl.col("local")).alias("local_id"),
        bsb("ts_urna_pronta").alias("pronta_bsb"), bsb("ts_ultimo_voto").alias("ultimo_bsb"),
        bsb("ts_primeiro_voto").alias("primeiro_bsb"),
    ).with_columns((pl.col("lula2") - pl.col("lula1")).alias("dlula")).with_columns(
        (pl.col("dlula") - pl.col("dlula").mean().over("mun")).alias("dlula_w"))


def apto(s):
    return s.filter(pl.col("pareada") & (pl.col("sg_uf") != "ZZ") & (pl.col("validos_1") > 0) & (pl.col("validos_2") > 0))


# ------------------------------------------------------------------ 1. modelos
def modelos(s):
    d = apto(s).filter(pl.col("modelo_urna").is_not_null())
    tab = (d.group_by("modelo_urna").agg(pl.len().alias("secoes"), pl.col("lula_1", "validos_1", "lula_2", "validos_2", "comp_2").sum(),
                                         pl.col("mun").n_unique().alias("municipios"))
           .with_columns((pl.col("lula_1") / pl.col("validos_1")).alias("lula_1t"), (pl.col("lula_2") / pl.col("validos_2")).alias("lula_2t"))
           .with_columns((pl.col("lula_2t") - pl.col("lula_1t")).alias("delta")).sort("modelo_urna"))
    print(tab)
    # locais com >1 modelo
    loc = d.group_by("local_id").agg(pl.col("modelo_urna").n_unique().alias("k"), pl.len().alias("n"))
    mist = loc.filter(pl.col("k") > 1)
    dm = d.join(mist.select("local_id"), on="local_id")
    RES["modelos_mistos"] = {"locais": mist.height, "secoes": dm.height, "locais_total": loc.height}
    print("locais mistos", RES["modelos_mistos"])
    regs = []
    for nome, df, fe, xs in [
        ("Bruto (sem controles)", d, None, []),
        ("Controles do 1º turno + EF de UF", d, None, ["lula1", "flavio1", "log_comp"]),
        ("Controles + EF de município", d, "mun", ["lula1", "flavio1", "log_comp"]),
        ("Dentro do mesmo local de votação (EF local)", dm, "local_id", ["lula1", "flavio1", "log_comp"]),
    ]:
        dum = ["modelo_urna"] + (["sg_uf"] if nome.startswith("Controles do 1º") else [])
        r = ols_fe(df, "dlula", xs, fe, "mun", dummies=dum)
        for m in ("UE2015", "UE2020", "UE2022"):
            c = r[f"modelo_urna={m}"]
            regs.append({"especificacao": nome, "modelo": m, "coef": c["coef"], "ic_inf": c["ic_inf"], "ic_sup": c["ic_sup"],
                         "p": c["p"], "n": r["n"]})
    regs = pl.DataFrame(regs)
    print(regs)
    RES["modelos_reg"] = regs.to_dicts()
    # placebo: mesma regressão no NÍVEL do 1º turno (o modelo do 2º turno "prevê" o 1º?)
    r = ols_fe(dm, "lula1", ["log_comp"], "local_id", "mun", dummies=["modelo_urna"])
    RES["modelos_placebo_t1"] = {m: r[f"modelo_urna={m}"] for m in ("UE2015", "UE2020", "UE2022")}
    salvar("modelos", tab.rename({"lula_1t": "lula_1_fatia", "lula_2t": "lula_2_fatia"}),
           "Fatia de Lula por modelo de urna", "Fatia de Lula nos votos válidos; modelo identificado no log do 2º turno.")
    salvar("modelos_reg", regs, "Diferença no Δ da fatia de Lula por modelo, relativa à UE2013",
           "Coeficiente em fração (0,01 = 1 p.p.). EP agrupado por município. A linha 'dentro do mesmo local' usa só locais de votação com mais de um modelo.")


# ------------------------------------------------------------------ 2. déficit / substituições
def deficit(s):
    d = s.filter(pl.col("n_votos_log") < pl.col("comp_2"))
    RES["deficit"] = {"secoes": d.height, "votos": int((d["comp_2"] - d["n_votos_log"]).sum()),
                      "secoes_log_zero": d.filter(pl.col("n_votos_log") == 0).height}
    sub_path = BASE / "substituicoes_logs.parquet"
    if not sub_path.exists():
        print("rode analises/08_substituicoes.py")
        return
    sl = pl.read_parquet(sub_path)
    # cada urna conta uma vez (o mesmo log pode vir repetido); soma votos do dia de todas as urnas
    por_urna = sl.group_by(*SEC, "grupo", "urna").agg(pl.col("n_votos").max(), pl.col("n_sem_digital").max(),
                                                      pl.col("ts_pronta").min(), pl.col("interno").min(),
                                                      pl.col("contingencia").any())
    sec = (por_urna.group_by(*SEC, "grupo").agg(
        pl.col("n_votos").sum().alias("votos_todos_logs"),
        (pl.col("n_votos") > 0).sum().alias("urnas_com_voto"),
        pl.len().alias("urnas_no_pacote"),
        pl.col("n_votos").filter(~pl.col("interno")).sum().alias("votos_log_principal"),
        pl.col("n_sem_digital").sum().alias("sem_digital_todos"))
           .join(s.select(*SEC, "comp_2", "n_votos_log", "biom_sh_2", "nm_municipio", "pronta_bsb", "primeiro_bsb",
                          "modelo_urna", "dlula", "dlula_w", "lula1", "lula2", "n_alertas", "n_erros"), on=SEC, how="left")
           .with_columns((pl.col("votos_todos_logs") - pl.col("comp_2")).alias("dif_bu")))
    resumo = sec.group_by("grupo").agg(
        pl.len().alias("secoes"), (pl.col("dif_bu") == 0).sum().alias("fecha_exato"),
        (pl.col("dif_bu").abs() <= 2).sum().alias("fecha_ate2"), pl.col("dif_bu").sum().alias("dif_total"),
        (pl.col("urnas_com_voto") >= 2).sum().alias("com_2_urnas_votando"),
        pl.col("votos_todos_logs").sum(), pl.col("comp_2").sum())
    print(resumo)
    RES["deficit_reconciliacao"] = resumo.to_dicts()
    # o nº da urna no bweb (nr_urna_efetivada) é o da última urna do log? e mudou entre turnos?
    princ = (sl.filter(~pl.col("interno")).select(*SEC, "grupo", "urna")
             .join(s.select(*SEC, "nr_urna_1", "nr_urna_2"), on=SEC)
             .with_columns(pl.col("urna").cast(pl.Int64).alias("u"), pl.col("nr_urna_2").cast(pl.Int64).alias("n2"),
                           pl.col("nr_urna_1").cast(pl.Int64).alias("n1")))
    RES["bweb_vs_log_urna"] = (princ.group_by("grupo").agg(pl.len().alias("secoes"), (pl.col("n2") == pl.col("u")).sum().alias("bweb_igual_log"),
                                                         (pl.col("n1") == pl.col("n2")).sum().alias("mesma_urna_t1_t2")).to_dicts())
    print(RES["bweb_vs_log_urna"])
    nao = sec.filter((pl.col("grupo") == "deficit") & (pl.col("dif_bu") != 0))
    print("não fecham:", nao.select(*SEC, "comp_2", "n_votos_log", "votos_todos_logs", "urnas_com_voto", "urnas_no_pacote").head(30))
    RES["deficit_nao_fecham"] = nao.select(*SEC, "comp_2", "n_votos_log", "votos_todos_logs", "urnas_com_voto").to_dicts()
    # horário da troca (urna pronta do log principal, Brasília)
    df = sec.filter(pl.col("grupo") == "deficit")
    hh = (df.with_columns(pl.col("pronta_bsb").dt.hour().alias("hora")).group_by("hora").agg(pl.len().alias("secoes")).sort("hora"))
    RES["deficit_hora_troca"] = hh.to_dicts()
    # Δ Lula: seções substituídas vs mesmo município
    sall = apto(s)
    flag = sall.join(df.select(SEC).with_columns(pl.lit(1.0).alias("subst")), on=SEC, how="left").with_columns(
        pl.col("subst").fill_null(0.0))
    r = ols_fe(flag, "dlula", ["subst", "lula1", "flavio1", "log_comp"], "mun", "mun")
    RES["deficit_dlula"] = r["subst"]
    print("Δlula ~ substituída", r["subst"])
    # sem digital no pacote todo vs bweb
    RES["deficit_sem_digital"] = {"bweb_biom_sh": int(df["biom_sh_2"].sum()), "log_sem_digital_todos": int(df["sem_digital_todos"].sum())}
    tab = (df.sort("dif_bu", "comp_2", descending=[True, True])
           .select(pl.col("sg_uf").alias("uf"), pl.col("nm_municipio").alias("municipio"), "zona", "secao",
                   pl.col("comp_2").alias("comparecimento"), pl.col("n_votos_log").alias("votos_ultima_urna"),
                   "votos_todos_logs", "dif_bu", "urnas_com_voto", pl.col("pronta_bsb").dt.strftime("%H:%M").alias("troca_bsb"),
                   "modelo_urna", "lula1", "lula2", "dlula", "dlula_w"))
    salvar("substituicoes", tab, "Seções com menos votos no log principal que no BU: reconciliação",
           "votos_ultima_urna = votos no logd.dat da última urna; votos_todos_logs = soma de todos os logs do pacote log.jez "
           "(urnas substituídas incluídas). dif_bu = votos_todos_logs − comparecimento. troca_bsb = hora em que a última urna ficou pronta.")


# ------------------------------------------------------------------ 3. alertas/erros
def alertas(s, ls):
    d = apto(s).filter(pl.col("n_votos_log") > 0).join(ls.select(*SEC, "n"), on=SEC, how="left")
    d = d.with_columns((pl.col("n_alertas") / pl.col("n_votos_log") * 100).alias("alertas_100"))
    desc = {c: d[c].describe().to_dicts() for c in ("n_alertas", "n_erros", "n_habilitacoes_sem_voto")}
    tot = s.select(pl.col("n_alertas", "n_erros", "n_habilitacoes_sem_voto").sum()).row(0, named=True)
    vc_err = d["n_erros"].value_counts().sort("n_erros").head(12)
    vc_hsv = d["n_habilitacoes_sem_voto"].value_counts().sort("n_habilitacoes_sem_voto").head(12)
    print(tot, vc_err, vc_hsv)
    RES["alertas_tot"] = tot
    RES["erros_dist"] = vc_err.to_dicts()
    RES["hsv_dist"] = vc_hsv.to_dicts()
    RES["alertas_quantis"] = {q: float(d["n_alertas"].quantile(q)) for q in (0.5, 0.9, 0.99, 0.999)}
    RES["alertas_max"] = int(d["n_alertas"].max())
    # correlação alertas por voto com taxa sem biometria (alertas de digital não reconhecida?)
    RES["corr_alertas_biom"] = float(stats.spearmanr(d["n_alertas"], d["biom_sh_2"]).statistic)
    dec = (d.with_columns(pl.col("alertas_100").qcut(10, labels=[f"D{i}" for i in range(1, 11)], allow_duplicates=True).alias("decil"))
           .group_by("decil").agg(pl.col("alertas_100").mean().alias("alertas_por_100"), pl.col("dlula_w").mean(),
                                  pl.col("dlula").mean(), pl.len().alias("secoes")).sort("alertas_por_100"))
    print(dec)
    salvar("alertas_decis", dec.with_columns(pl.col("decil").cast(pl.String)),
           "Δ da fatia de Lula (vs média do município) por decil de alertas no log",
           "Alertas por 100 votos registrados no log do 2º turno. dlula_w = Δ (2º−1º) da fatia de Lula menos a média do município.")
    regs = {}
    dd = d.with_columns((pl.col("n_alertas") + 1).log().alias("log_alertas"), (pl.col("n_erros") > 1).cast(pl.Float64).alias("erro_extra"),
                        (pl.col("n_habilitacoes_sem_voto") > 0).cast(pl.Float64).alias("tem_hsv"))
    for x in ("log_alertas", "erro_extra", "tem_hsv"):
        r = ols_fe(dd, "dlula", [x, "lula1", "flavio1", "log_comp"], "mun", "mun", dummies=["modelo_urna"])
        regs[x] = r[x]
    RES["alertas_reg"] = regs
    print(regs)


# ------------------------------------------------------------------ 4/6. relógio e esquisitices
def relogio(s, ls):
    d = s.filter(pl.col("sg_uf") != "ZZ")
    hora = lambda c: pl.col(c).dt.hour().cast(pl.Int32) * 60 + pl.col(c).dt.minute().cast(pl.Int32)  # noqa: E731
    x = d.with_columns(hora("pronta_bsb").alias("m_pronta"), hora("primeiro_bsb").alias("m_prim"), hora("ultimo_bsb").alias("m_ult"))
    sub = s.filter(pl.col("n_votos_log") < pl.col("comp_2")).select(SEC).with_columns(pl.lit(True).alias("subst"))
    x = x.join(sub, on=SEC, how="left").with_columns(pl.col("subst").fill_null(False))
    r = {
        "pronta_antes_8h": x.filter(pl.col("m_pronta") < 480).height,
        "pronta_antes_7h30": x.filter(pl.col("m_pronta") < 450).height,
        "pronta_apos_8h30": x.filter(pl.col("m_pronta") >= 510).height,
        "pronta_apos_8h30_sem_subst": x.filter((pl.col("m_pronta") >= 510) & ~pl.col("subst")).height,
        "pronta_apos_9h_sem_subst": x.filter((pl.col("m_pronta") >= 540) & ~pl.col("subst")).height,
        "primeiro_voto_antes_8h": x.filter(pl.col("m_prim") < 480).height,
        "ultimo_voto_apos_17h": x.filter(pl.col("m_ult") >= 17 * 60).height,
        "ultimo_voto_apos_17h30": x.filter(pl.col("m_ult") >= 17 * 60 + 30).height,
        "ultimo_voto_apos_18h": x.filter(pl.col("m_ult") >= 18 * 60).height,
    }
    # bweb: abertura/encerramento (relógio local)
    r["bweb_abertura_null"] = d.filter(pl.col("abertura_2").is_null()).height
    print("RELOGIO", r)
    RES["relogio"] = r
    hist = (x.filter(pl.col("m_pronta").is_not_null()).with_columns(((pl.col("m_pronta") // 5) * 5).clip(420, 1020).alias("min"))
            .group_by("min", "subst").agg(pl.len().alias("secoes")).sort("min"))
    hist = hist.pivot(on="subst", index="min", values="secoes").fill_null(0).rename({"true": "substituida", "false": "normal"}).sort("min")
    hist = hist.with_columns((pl.format("{}:{}", (pl.col("min") // 60).cast(pl.String).str.zfill(2),
                                        (pl.col("min") % 60).cast(pl.String).str.zfill(2))).alias("hora"))
    salvar("pronta", hist, "Hora em que a urna (a última usada na seção) ficou pronta para receber votos",
           "Horário de Brasília, faixas de 5 min; extremos agrupados em 07:00 e 17:00. Exclui exterior.")
    # esquisitices por eleitor
    a = ls.filter(pl.col("sg_uf") != "ZZ")
    cols = ["a_hab_nulo", "a_pres_nulo", "a_comp_antes_hab", "a_hab_antes_ident", "a_cabine_neg", "a_desordem", "a_sobreposto",
            "n_apos_17_bsb", "n_antes_8_bsb"]
    esq = []
    rot = {"a_hab_nulo": "Voto computado sem registro de habilitação", "a_pres_nulo": "Voto computado sem confirmação de voto para Presidente",
           "a_comp_antes_hab": "Voto computado antes da habilitação", "a_hab_antes_ident": "Habilitação antes de o mesário digitar o título",
           "a_cabine_neg": "Tempo de cabine negativo", "a_desordem": "Voto computado antes do voto anterior (fora de ordem)",
           "a_sobreposto": "Eleitor identificado antes de o anterior terminar (sobreposição)",
           "n_apos_17_bsb": "Votos computados a partir das 17h (Brasília)", "n_antes_8_bsb": "Eleitores identificados antes das 8h (Brasília)"}
    # O leitor (scripts/baixar_logs_urna.py) monta cada registro na ordem das linhas do log e só guarda sequências
    # completas: mensagens de voto fora de uma sequência aberta eram descartadas sem contagem. Por isso os testes de
    # ordem abaixo checam os relógios entre registros já pareados, não a ordem bruta das mensagens.
    nota = {"a_comp_antes_hab": "relógio, entre registros pareados", "a_hab_antes_ident": "relógio, entre registros pareados",
            "a_cabine_neg": "relógio, entre registros pareados", "a_desordem": "relógio, entre registros pareados",
            "a_sobreposto": "relógio, entre registros pareados"}
    for c in cols:
        esq.append({"item": rot[c], "chave": c, "eleitores": int(a[c].sum()), "secoes": int((a[c] > 0).sum()),
                    "nota": nota.get(c, "")})
    esq.append({"item": "Habilitações sem voto computado (log; piso)", "chave": "hsv", "nota": "não conta pendências no fim do arquivo",
                "eleitores": int(d["n_habilitacoes_sem_voto"].sum()), "secoes": int((d["n_habilitacoes_sem_voto"] > 0).sum())})
    esq.append({"item": "Seções sem log de votação publicado", "chave": "sem_log",
                "eleitores": int(d.filter(pl.col("n_votos_log").is_null())["comp_2"].sum() or 0),
                "secoes": d.filter(pl.col("n_votos_log").is_null()).height})
    esq = pl.DataFrame(esq)
    print(esq)
    RES["esquisitices"] = esq.to_dicts()
    salvar("esquisitices", esq, "Inconsistências procuradas no log por eleitor (2º turno, Brasil)",
           "Contagens sobre ~128 milhões de registros pareados pelo leitor. 'eleitores' = nº de registros afetados; 'secoes' = seções com ≥1 caso. Mensagens fora de uma sequência completa (voto computado sem identificação aberta, segunda mensagem de computação, habilitação pendente no fim do arquivo) não eram contadas nesta versão do leitor; os itens de ordem checam relógios entre registros pareados.")
    # gaps longos
    g = a.select((pl.col("max_gap_s") >= 3600).sum().alias("gap_1h"), (pl.col("max_gap_s") >= 7200).sum().alias("gap_2h"),
                 pl.col("max_gap_s").median().alias("gap_mediana")).row(0, named=True)
    RES["gaps"] = g
    print("gaps", g)
    # votos depois das 17h por UF (relógio do log)
    RES["votos_apos_17"] = int(a["n_apos_17_bsb"].sum())
    RES["secoes_apos_17"] = int((a["n_apos_17_bsb"] > 0).sum())


def tipo_urna(s):
    out = []
    for t in (1, 2):
        vc = s.group_by(f"tipo_urna_{t}").agg(pl.len().alias("secoes"), pl.col(f"comp_{t}").sum().alias("comparecimento"),
                                              pl.col(f"lula_{t}").sum().alias("lula"), pl.col(f"flavio_{t}").sum().alias("flavio"))
        for r in vc.to_dicts():
            out.append({"turno": t, "tipo_urna": r[f"tipo_urna_{t}"] or "(vazio)", **{k: r[k] for k in ("secoes", "comparecimento", "lula", "flavio")}})
    RES["tipo_urna"] = out
    print(pl.DataFrame(out))
    nul = s.filter(pl.col("tipo_urna_2").is_null()).select(*SEC, "comp_1", "comp_2", "lula_1", "lula_2", "n_votos_log")
    RES["tipo_urna_nulo"] = nul.to_dicts()
    print(nul)
    # nr_urna mudou entre turnos?
    m = s.filter(pl.col("pareada"))
    RES["nr_urna_igual"] = {"igual": m.filter(pl.col("nr_urna_1") == pl.col("nr_urna_2")).height, "total": m.height}
    salvar("tipo_urna", pl.DataFrame(out), "Tipo de urna declarado no boletim (bweb)", "Contagem de seções por ds_tipo_urna, por turno.")


def main():
    s = base()
    L = carregar()
    ls = L["log_secoes"]
    tipo_urna(s)
    modelos(s)
    deficit(s)
    alertas(s, ls)
    relogio(s, ls)
    kpis = [
        {"rotulo": "Seções com log menor que o BU", "valor": RES["deficit"]["secoes"], "formato": "num",
         "detalhe": f"{RES['deficit']['votos']:,} votos fora do log principal".replace(",", ".")},
        {"rotulo": "Locais de votação com mais de um modelo de urna", "valor": RES["modelos_mistos"]["locais"], "formato": "num",
         "detalhe": f"{RES['modelos_mistos']['secoes']:,} seções na comparação dentro do local".replace(",", ".")},
        {"rotulo": "Votos computados a partir das 17h (log)", "valor": RES["votos_apos_17"], "formato": "num",
         "detalhe": "TSE informou 34.393"},
        {"rotulo": "Votos computados antes da habilitação", "valor": next(e["eleitores"] for e in RES["esquisitices"] if e["chave"] == "a_comp_antes_hab"),
         "formato": "num", "detalhe": "em ~128 milhões de registros"},
    ]
    rec = [r for r in RES.get("deficit_reconciliacao", []) if r["grupo"] == "deficit"]
    if rec:
        kpis.insert(1, {"rotulo": "…das quais fecham com o BU somando os logs internos", "valor": rec[0]["fecha_exato"], "formato": "num",
                        "detalhe": f"de {rec[0]['secoes']} baixadas de novo"})
    salvar("kpis", kpis, "Números-chave do capítulo 8", "")
    (BASE / "cap08_resultados.json").write_text(json.dumps(RES, indent=1, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
