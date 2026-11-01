"""Capítulo 11 — As pesquisas erraram só para um lado?

As pesquisas foram conferidas na imprensa que reproduziu o registro (ver FONTES abaixo; acesso em 2026-10-29)
e na tabela consolidada da Wikipédia. A métrica comum é a fatia do candidato do PT entre os dois primeiros
colocados ("bipartidária"). No 2º turno de 2026, quando o instituto divulgou a estimativa de votos válidos,
usamos o número publicado (escala "válidos publicados"); só quando não divulgou recalculamos a partir dos
votos totais (escala "renormalizada"):
    fatia_pt = PT / (PT + adversário)
As duas medidas não são iguais: a renormalização de totais arredondados não acrescenta precisão (47/(47+48) =
49,47%, enquanto o Datafolha publicou 49% dos válidos). As duas ficam no JSON (fatia_pt_renormalizada).
Nos demais anos só temos uma das escalas. No 1º turno a renormalização permite comparar
institutos que divulgam brancos/indecisos de forma diferente. Erro = resultado − pesquisa (positivo = a
pesquisa subestimou o PT). Também calculamos o erro na fatia dos válidos de cada candidato no 1º turno
(válidos = 100 − brancos/nulos/indecisos, aproximação).

Rodar: uv run python analises/11_pesquisas.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import municipios_2022, salvar_json, secoes_2026  # noqa: E402

SCRIPT = "analises/11_pesquisas.py"
HOJE = date.today().isoformat()
WIKI26 = "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Brazilian_presidential_election"
WIKI22 = "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2022_Brazilian_presidential_election"
CNN26 = "https://www.cnnbrasil.com.br/eleicoes/ultimas-pesquisas-segundo-turno-eleicao/"

# (eleição, instituto, campo, amostra, PT, adversário, bnI, válidos_publicados_PT ou None, fonte)
# Valores = votos totais (estimulada) em %. bnI = brancos/nulos/indecisos somados.
# Conferência de fontes em 2026-10-30 (ver analises/achados/11-pesquisas.md, "Verificação de fontes"):
# corrigidos Veritá (rodada 19–23/10: 46,46 × 49,44, e não 47,8 × 49,8), Instituto França (Flávio 45,6, e não 45,1)
# e campo da Alfa (18–22/10). Colectta e Datatrends seguem só na Wikipédia (não localizados na imprensa).
P2_2026 = [
    ("Datafolha", "23–24/10", 4050, 47, 48, 5, 49, "https://diariodonordeste.verdesmares.com.br/pontopoder/datafolha-no-2-turno-flavio-bolsonaro-tem-51-e-lula-49-em-votos-validos-1.3800996"),
    ("Quaest", "23–24/10", 3702, 45, 46, 9, 49, "https://www.oliberal.com/politica/quaest-flavio-bolsonaro-tem-51-dos-votos-validos-e-lula-49-na-vespera-do-segundo-turno-1.1186432"),
    ("AtlasIntel", "18–23/10", 4990, 48.4, 49.9, 1.7, 49.2, "https://sbtnews.sbt.com.br/noticia/politica/atlas-intel-flavio-tem-50-8-contra-49-2-de-lula"),
    ("CNT/MDA", "21–23/10", 2032, 45.0, 46.3, 8.7, 49.3, "https://midiamax.com.br/brasil/2026/cnt-mda-flavio-bolsonaro-tem-507-votos-validos-lula-493/"),
    ("Real Time Big Data", "19–22/10", 2000, 45, 49, 6, 48, "https://www.dgabc.com.br/Noticia/4354342/real-time-big-data-flavio-tem-52-dos-votos-validos-contra-48-de-lula-em-empate-tecnico"),
    ("PoderData/Aya", "23–24/10", 4000, 48, 49, 4, 49, CNN26),
    ("Nexus/BTG", "23–24/10", 2000, 46, 47, 7, 49.5, CNN26),
    ("Palver", "22–24/10", 5000, 49, 50, 1, None, "https://tribunadejundiai.com.br/politica/eleicoes-2026/pesquisa-palver-flavio-bolsonaro-tem-50-e-lula-49-no-segundo-turno/"),
    ("Futura", "23–24/10", 2000, 47.9, 48.2, 3.9, 49.9, CNN26),
    ("Gerp", "22–24/10", 2400, 46, 49, 4, 48, CNN26),
    ("Colectta", "23/10", 3000, 46.5, 46, 7.5, None, WIKI26),
    ("Instituto França", "21–23/10", 1537, 43.1, 45.6, 11.3, 48.6, "https://timesbrasil.com.br/eleicoes-2026/decisao-2026-na-vespera-do-2o-turno-flavio-bolsonaro-tem-514-dos-votos-validos-contra-486-de-lula-diz-instituto-franca/"),
    ("Veritá", "19–23/10", 15554, 46.46, 49.44, 4.10, 48.44, "https://www.congressoemfoco.com.br/noticia/123609/flavio-tem-51-56-dos-votosvalidos-e-lula-48-44--diz-verita"),
    ("Ipespe", "20–22/10", 1500, 47, 48, 5, 49.5, "https://www.poder360.com.br/poder-eleicoes-2026/flavio-tem-505-contra-495-de-lula-diz-ipespe-abrapel/"),
    ("Vox Brasil", "20–22/10", 2100, 45.4, 44.3, 10.3, 50.6, "https://www.oliberal.com/politica/em-votos-validos-lula-tem-50-6-contra-49-4-de-flavio-mostra-pesquisa-vox-brasil-1.1185727"),
    ("Alfa", "18–22/10", 2700, 46, 49.9, 4.1, 48, "https://timesbrasil.com.br/brasil/decisao-2026-flavio-bolsonaro-tem-52-dos-votos-validos-contra-48-de-lula-no-2o-turno-aponta-pesquisa-alfa-inteligencia/"),
    ("Indexa", "20–21/10", 2000, 44.1, 45.2, 10.7, 49.4, "https://www.oliberal.com/politica/flavio-tem-45-2-ante-44-1-de-lula-em-empate-tecnico-mostra-pesquisa-indexa-broadcast-1.1185405"),
    ("Datatrends", "19–21/10", 2000, 46, 50, 4, None, WIKI26),
]
# 1º turno de 2026 (Lula, Flávio, bnI)
P1_2026 = [
    ("Datafolha", "3/10", 42, 40, 7), ("Quaest", "2–3/10", 40, 38, 13), ("Futura", "2–3/10", 40.5, 42.5, 2.6),
    ("Palver", "30/9–3/10", 43, 47, 0), ("PoderData/Aya", "30/9–2/10", 42, 41, 6), ("CNT/MDA", "29/9–2/10", 43.1, 38, 9.7),
    ("AtlasIntel", "27/9–2/10", 46.7, 43.8, 0.6), ("Vox Brasil", "29/9–1/10", 40.4, 41.2, 10.2),
]
# 2022, 2º turno (Lula, Bolsonaro, bnI)
P2_2022 = [
    ("Datafolha", "28–29/10", 49, 45, 7), ("Ipec", "27–29/10", 50, 43, 7), ("Quaest", "27–29/10", 45, 42, 13),
    ("AtlasIntel", "26–29/10", 52.4, 45.7, 1.9), ("CNT/MDA", "26–28/10", 46.9, 44.9, 8.2),
    ("Paraná Pesquisas", "26–28/10", 47.1, 46.3, 6.6), ("Futura", "24–26/10", 46.6, 47.2, 6.1), ("PoderData", "23–25/10", 49, 44, 7),
]
# 2022, 1º turno (Lula, Bolsonaro, bnI) — só institutos com campo nos 8 dias finais
P1_2022 = [
    ("Datafolha", "30/9–1/10", 48, 34, 5), ("Ipec", "29/9–1/10", 47, 34, 7), ("Quaest", "24–27/9", 46, 33, 9),
    ("AtlasIntel", "28–30/9", 49.8, 40.7, 1), ("CNT/MDA", "28–30/9", 44.2, 36.3, 8.5), ("Ideia", "23–28/9", 47, 37, 4),
]
# 2º turno de 2014 e 2018: só válidos publicados (PT = Dilma / Haddad)
P2_2014 = [("Datafolha", "24–25/10", 52), ("Ibope", "24–25/10", 53)]
P2_2018 = [("Datafolha", "26–27/10", 45), ("Ibope", "26–27/10", 46)]

RES = {  # fatia oficial (válidos) — 2014/2018: TSE; 2022/2026: calculado dos boletins
    "2014 · 2º turno": 51.64, "2018 · 2º turno": 44.87,
}

TRANSFER = [
    {"instituto": "Datafolha", "campo": "6–7/10", "grupo": "eleitores de Cury, Renan, Caiado e Zema",
     "flavio": 46, "lula": 32, "branco_nulo": 15, "verificado": True,
     "fonte": "https://www.dgabc.com.br/Noticia/4351747/46-dos-eleitores-de-cury-renan-santos-caiado-e-zema-migram-para-flavio-aonta-datafolha"},
    {"instituto": "Datafolha (citado em alegações que circulam)", "campo": "20–22/10", "grupo": "eleitores dos eliminados",
     "flavio": 47, "lula": 26, "branco_nulo": None, "verificado": False, "fonte": "alegação que circulou (não localizada na fonte primária)"},
    {"instituto": "Quaest", "campo": "divulgada em 22/10", "grupo": "eleitores de Cury, Caiado, Renan e Zema",
     "flavio": 43, "lula": 37, "branco_nulo": None, "verificado": True,
     "nota": "Mesma publicação: retenção de 95% (Lula) e 94% (Flávio); entre quem diz ter faltado ou votado branco/nulo no 1º turno, 40% Lula e 36% Flávio. Não informa os tamanhos das subamostras.",
     "fonte": "https://quaest.com.br/segundo-turno-2026-votos-brancos-nulos/"},
]


def main():
    s = secoes_2026()
    tot = s.select(pl.col("lula_1", "flavio_1", "validos_1", "lula_2", "flavio_2", "validos_2", "outros_1").sum()).row(0, named=True)
    m22 = municipios_2022()
    t22 = m22.select(pl.col("lula_1", "bolsonaro_1", "validos_1", "lula_2", "bolsonaro_2", "validos_2").sum()).row(0, named=True)
    RES["2026 · 2º turno"] = 100 * tot["lula_2"] / (tot["lula_2"] + tot["flavio_2"])
    RES["2026 · 1º turno"] = 100 * tot["lula_1"] / (tot["lula_1"] + tot["flavio_1"])
    RES["2022 · 2º turno"] = 100 * t22["lula_2"] / (t22["lula_2"] + t22["bolsonaro_2"])
    RES["2022 · 1º turno"] = 100 * t22["lula_1"] / (t22["lula_1"] + t22["bolsonaro_1"])
    val1 = {"2026 · 1º turno": (100 * tot["lula_1"] / tot["validos_1"], 100 * tot["flavio_1"] / tot["validos_1"]),
            "2022 · 1º turno": (100 * t22["lula_1"] / t22["validos_1"], 100 * t22["bolsonaro_1"] / t22["validos_1"])}
    print({k: round(v, 3) for k, v in RES.items()}, val1)

    linhas = []

    def add(eleicao, inst, campo, pt, adv, bni=None, n=None, publicado=None, fonte=None, so_valido=False):
        renorm = None if so_valido else 100 * pt / (pt + adv)
        if so_valido:
            fat, escala = pt, "válidos publicados"
        elif publicado is not None:
            fat, escala = publicado, "válidos publicados"
        else:
            fat, escala = renorm, "renormalizada"
        r = {"eleicao": eleicao, "instituto": inst, "campo": campo, "amostra": n,
             "fatia_pt_pesquisa": round(fat, 2), "fatia_pt_resultado": round(RES[eleicao], 2),
             "erro_pt": round(RES[eleicao] - fat, 2), "escala": escala,
             "fatia_pt_renormalizada": None if renorm is None else round(renorm, 2),
             "validos_pt_publicado": publicado, "fonte": fonte}
        if eleicao in val1 and bni is not None:
            v = 100 - bni
            r["erro_validos_pt"] = round(val1[eleicao][0] - 100 * pt / v, 2)
            r["erro_validos_adv"] = round(val1[eleicao][1] - 100 * adv / v, 2)
        linhas.append(r)

    for inst, campo, n, pt, adv, bni, pub, fonte in P2_2026:
        add("2026 · 2º turno", inst, campo, pt, adv, bni, n, pub, fonte)
    for inst, campo, pt, adv, bni in P1_2026:
        add("2026 · 1º turno", inst, campo, pt, adv, bni, fonte=WIKI26)
    for inst, campo, pt, adv, bni in P2_2022:
        add("2022 · 2º turno", inst, campo, pt, adv, bni, fonte=WIKI22)
    for inst, campo, pt, adv, bni in P1_2022:
        add("2022 · 1º turno", inst, campo, pt, adv, bni, fonte=WIKI22)
    for inst, campo, v in P2_2014:
        add("2014 · 2º turno", inst, campo, v, None, so_valido=True,
            fonte="https://www.jb.com.br/eleicoes-2014/noticias/2014/10/25/amp/dilma-na-frente-de-aecio-aponta-ultimas-pesquisas-do-ibope-e-datafolha.html")
    for inst, campo, v in P2_2018:
        add("2018 · 2º turno", inst, campo, v, None, so_valido=True, fonte="https://www.poder360.com.br/eleicoes/ibope-bolsonaro-54-x-46-haddad-datafolha-bolsonaro-55-x-45-haddad/")

    df = pl.DataFrame(linhas, infer_schema_length=None)
    ordem = ["2014 · 2º turno", "2018 · 2º turno", "2022 · 1º turno", "2022 · 2º turno", "2026 · 1º turno", "2026 · 2º turno"]
    resumo = (df.group_by("eleicao").agg(
        pl.len().alias("pesquisas"), pl.col("erro_pt").mean().alias("erro_medio"),
        pl.col("erro_pt").abs().mean().alias("erro_abs_medio"), pl.col("erro_pt").min().alias("erro_min"),
        pl.col("erro_pt").max().alias("erro_max"), (pl.col("erro_pt") > 0).sum().alias("subestimaram_pt"),
        pl.col("erro_validos_adv").mean().alias("erro_medio_validos_adv"),
        pl.col("erro_validos_pt").mean().alias("erro_medio_validos_pt"),
    ).with_columns(pl.col("eleicao").replace_strict({k: i for i, k in enumerate(ordem)}).alias("_o")).sort("_o").drop("_o"))
    with pl.Config(tbl_rows=60, tbl_cols=20, tbl_width_chars=250):
        print(df)
        print(resumo)

    # erro amostral esperado para a fatia bipartidária: n efetivo ~ n*(1-bni)
    d26 = df.filter(pl.col("eleicao") == "2026 · 2º turno")
    ns = np.array([r[2] * (1 - r[5] / 100) for r in P2_2026])
    ep = 100 * np.sqrt(0.5 * 0.5 / ns)
    z = d26["erro_pt"].to_numpy() / ep
    print("2026 2T: erro/EP amostral (sem efeito de desenho):", np.round(z, 2), "média erro", d26["erro_pt"].mean())
    # quantas pesquisas finais deram Lula à frente
    print("Lula à frente nas finais de 2026:", d26.filter(pl.col("fatia_pt_pesquisa") > 50)["instituto"].to_list())

    meta = lambda t, d: {"titulo": t, "fonte": "Institutos de pesquisa (via imprensa e Wikipédia); TSE", "descricao": d,  # noqa: E731
                         "gerado_em": HOJE, "script": SCRIPT}
    salvar_json("ch11/erros", {"meta": meta("Erro das pesquisas finais na fatia do PT entre os dois primeiros",
                                            "erro_pt = resultado − pesquisa, em p.p. da fatia do PT nos válidos entre os dois (positivo = subestimou o candidato do PT: Dilma 2014, Haddad 2018, Lula 2022/2026). escala = 'válidos publicados' (número divulgado pelo instituto) ou 'renormalizada' (PT/(PT+adversário) dos votos totais); fatia_pt_renormalizada mostra a segunda medida também quando a primeira existe."),
                               "dados": df.to_dicts()})
    salvar_json("ch11/resumo", {"meta": meta("Erro médio por eleição", "Médias simples entre institutos."),
                                "dados": resumo.with_columns(pl.col(pl.Float64).round(3)).to_dicts()})
    salvar_json("ch11/transferencia", {"meta": meta("Para onde as pesquisas diziam que iriam os eleitores dos eliminados",
                                                    "Percentuais entre eleitores de Cury, Renan, Caiado e Zema no 1º turno."),
                                       "dados": TRANSFER,
                                       "votos_eliminados_1t": int(tot["outros_1"])})


if __name__ == "__main__":
    main()
