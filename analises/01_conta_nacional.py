"""Capítulo 1 — A conta nacional: de onde vieram os 10,4 milhões de votos de Lula.

Temas: reconciliação, conta nacional, alegação "499.205 seções".

O que este script faz (tudo a partir dos boletins de urna oficiais do TSE, por seção):
  1. Reconciliação: identidades por seção nos dois turnos (comp = válidos + brancos + nulos;
     válidos = soma dos nominais; aptos >= comp), somas municipais dos 8 municípios do RJ cujo
     CSV derivado que circulou "não fechava", contagem de seções, totais vs tabela 1 das alegações.
  2. Conta nacional 1º -> 2º turno em 2026 e a MESMA conta em 2022 (linha de base).
  3. Teste do "reservatório" por seção (2026 e 2022): em quantas seções o ganho de um finalista
     excede tudo o que estava disponível sem tirar votos do adversário, e qual a migração direta
     mínima exigida (somada por seção, município, UF e país).

Rodar: uv run python analises/01_conta_nacional.py
Saídas: site/public/data/ch01/*.json, analises/achados/dados/01-*.json (números para o achados).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    ACHADOS, CAND_2022_T1, CAND_2022_T2, CHAVE, REGIAO, _nomes_municipios, _padronizar, bweb,
    municipios_2022, municipios_2026, salvar_json, secoes_2026,
)

SCRIPT = "analises/01_conta_nacional.py"
HOJE = str(date.today())
FONTE = "TSE — boletins de urna por seção (BWeb), 1º e 2º turnos"
SAIDA_NUM = ACHADOS / "dados"
SAIDA_NUM.mkdir(parents=True, exist_ok=True)
NUMEROS: dict = {}


def meta(titulo: str, descricao: str, fonte: str = FONTE) -> dict:
    return {"titulo": titulo, "fonte": fonte, "descricao": descricao, "gerado_em": HOJE, "script": SCRIPT}


def salvar(nome: str, titulo: str, descricao: str, dados, **extra) -> None:
    if isinstance(dados, pl.DataFrame):
        dados = dados.with_columns(pl.col(pl.Float64, pl.Float32).round(6)).to_dicts()
    salvar_json(f"ch01/{nome}", {"meta": meta(titulo, descricao), "dados": dados, **extra}, decimais=None)


# ----------------------------------------------------------------------------------------------
# Seções de 2022 (os dois turnos de 2022 casam entre si pela chave de seção)
# ----------------------------------------------------------------------------------------------
def secoes_2022() -> pl.DataFrame:
    t1 = _padronizar(2022, 1, CAND_2022_T1).drop("local")
    t2 = _padronizar(2022, 2, CAND_2022_T2).drop("local")
    return (
        t1.join(t2, on=CHAVE, how="full", coalesce=True)
        .join(_nomes_municipios(), on=["sg_uf", "cd_municipio_tse"], how="left")
        .with_columns(
            pl.col("sg_uf").replace_strict(REGIAO, default=None).alias("regiao"),
            (pl.col("lula_1").is_not_null() & pl.col("lula_2").is_not_null()).alias("pareada"),
        )
    )


# ----------------------------------------------------------------------------------------------
# 1. Reconciliação
# ----------------------------------------------------------------------------------------------
def reconciliacao(s: pl.DataFrame) -> None:
    r = {}
    r["secoes_t1"] = int(s["lula_1"].is_not_null().sum())
    r["secoes_t2"] = int(s["lula_2"].is_not_null().sum())
    r["secoes_pareadas"] = int(s["pareada"].sum())
    so1 = s.filter(~pl.col("pareada"))
    r["secoes_so_t1"] = so1.select("sg_uf", "cd_municipio_tse", "zona", "secao", "comp_1", "aptos_1").to_dicts()
    r["secoes_agregadas"] = int(s["agregadas_1"].is_not_null().sum())

    # identidades a partir do BWeb bruto (nominais somados coluna a coluna)
    for ano, turno in [(2026, 1), (2026, 2), (2022, 1), (2022, 2)]:
        lf = bweb(ano, turno)
        cols = lf.collect_schema().names()
        nom = [c for c in cols if c.startswith("votos_") and c.removeprefix("votos_").isdigit()]
        d = lf.select(
            *CHAVE,
            pl.sum_horizontal([pl.col(c).fill_null(0) for c in nom]).alias("nominais"),
            pl.col("votos_validos").alias("validos"), pl.col("votos_brancos").alias("brancos"),
            pl.col("votos_nulos").alias("nulos"), pl.col("qt_comparecimento").alias("comp"),
            pl.col("qt_aptos").alias("aptos"), pl.col("qt_abstencoes").alias("abst"),
        ).collect()
        k = f"{ano}_t{turno}"
        r[f"identidades_{k}"] = {
            "secoes": d.height,
            "comp_ne_validos_brancos_nulos": int((d["comp"] != d["validos"] + d["brancos"] + d["nulos"]).sum()),
            "validos_ne_soma_nominais": int((d["validos"] != d["nominais"]).sum()),
            "comp_maior_que_aptos": int((d["comp"] > d["aptos"]).sum()),
            "abst_ne_aptos_menos_comp": int((d["abst"] != d["aptos"] - d["comp"]).sum()),
            "soma_residuo_R": int((d["comp"] - d["validos"] - d["brancos"] - d["nulos"]).sum()),
        }
        # nota: em 2026 t1 o candidato 28 (anulado) aparece entre os nominais do BWeb mas fora de votos_validos
        if ano == 2026 and turno == 1:
            r[f"identidades_{k}"]["obs"] = "votos do candidato 28 (anulado) contados como nulos, como no painel"
            d28 = lf.select(pl.col("votos_28").fill_null(0).sum()).collect().item() if "votos_28" in cols else 0
            r[f"identidades_{k}"]["votos_candidato_28"] = int(d28)
            r[f"identidades_{k}"]["obs2"] = "votos_validos do BWeb inclui o 28; comum.py o move para nulos"

    # resíduos municipais nos 8 casos das alegações (Tabela 3) a partir das seções oficiais
    alegacao_R = {"Campos dos Goytacazes": 3, "Araruama": 2, "Armação dos Búzios": -9, "Arraial do Cabo": -2,
                "Cabo Frio": 98, "Iguaba Grande": -10, "São Pedro da Aldeia": -2, "Saquarema": -6,
                "Silva Jardim": None}
    m = municipios_2026().filter(pl.col("sg_uf") == "RJ")
    linhas = []
    for nome, rd in alegacao_R.items():
        x = m.filter(pl.col("nm_municipio").str.to_lowercase() == nome.lower())
        if x.height != 1:
            # tolera grafias (ex.: 'Armação dos Búzios')
            x = m.filter(pl.col("nm_municipio").str.to_lowercase().str.contains(nome.split()[-1].lower()))
        x = x.row(0, named=True)
        linhas.append({
            "municipio": x["nm_municipio"], "secoes": x["n_secoes"],
            "comp_2": x["comp_2"], "lula_2": x["lula_2"], "flavio_2": x["flavio_2"],
            "brancos_2": x["brancos_2"], "nulos_2": x["nulos_2"],
            "residuo_oficial_t1": x["comp_1"] - x["validos_1"] - x["brancos_1"] - x["nulos_1"],
            "residuo_oficial_t2": x["comp_2"] - x["lula_2"] - x["flavio_2"] - x["brancos_2"] - x["nulos_2"],
            "residuo_csv_alegacao": rd,
            "delta_lula": x["lula_2"] - x["lula_1"], "delta_flavio": x["flavio_2"] - x["flavio_1"],
        })
    rec = pl.DataFrame(linhas)
    salvar("reconciliacao-rj", "Resíduo R = comparecimento − (nominais + brancos + nulos), 2º turno",
           "Municípios do RJ citados nas alegações: resíduo em um CSV derivado que circulou vs. resíduo "
           "calculado somando as seções oficiais do TSE.", rec)
    r["rj"] = rec.to_dicts()
    NUMEROS["reconciliacao"] = r
    print(json.dumps({k: v for k, v in r.items() if k != "rj"}, ensure_ascii=False, indent=1, default=str))
    print(rec)


# ----------------------------------------------------------------------------------------------
# 2. Conta nacional 2026 e 2022
# ----------------------------------------------------------------------------------------------
def conta(m: pl.DataFrame, ano: int) -> dict:
    adv = "flavio" if ano == 2026 else "bolsonaro"
    t = m.select(pl.col([c for c in m.columns if c.endswith(("_1", "_2")) and m.schema[c].is_integer()]).sum()).row(0, named=True)
    c = {
        "ano": ano, "adversario": adv,
        "lula_1": t["lula_1"], "lula_2": t["lula_2"], "adv_1": t[f"{adv}_1"], "adv_2": t[f"{adv}_2"],
        "outros_1": t["outros_1"], "brancos_1": t["brancos_1"], "brancos_2": t["brancos_2"],
        "nulos_1": t["nulos_1"], "nulos_2": t["nulos_2"], "validos_1": t["validos_1"], "validos_2": t["validos_2"],
        "comp_1": t["comp_1"], "comp_2": t["comp_2"], "aptos_1": t["aptos_1"], "aptos_2": t["aptos_2"],
    }
    c["abst_1"] = c["aptos_1"] - c["comp_1"]
    c["abst_2"] = c["aptos_2"] - c["comp_2"]
    c["d_lula"] = c["lula_2"] - c["lula_1"]
    c["d_adv"] = c["adv_2"] - c["adv_1"]
    c["d_validos"] = c["validos_2"] - c["validos_1"]
    c["d_comp"] = c["comp_2"] - c["comp_1"]
    c["d_bn"] = (c["brancos_2"] + c["nulos_2"]) - (c["brancos_1"] + c["nulos_1"])
    c["sh_lula_1"] = c["lula_1"] / (c["lula_1"] + c["adv_1"])
    c["sh_lula_2"] = c["lula_2"] / (c["lula_2"] + c["adv_2"])
    c["d_sh_lula"] = c["sh_lula_2"] - c["sh_lula_1"]
    c["lula_val_1"] = c["lula_1"] / c["validos_1"]
    c["lula_val_2"] = c["lula_2"] / c["validos_2"]
    c["outros_sobre_validos_1"] = c["outros_1"] / c["validos_1"]
    # o ganho do candidato que estava atrás no 1º turno, comparado aos eliminados
    atras = "lula" if c["lula_1"] < c["adv_1"] else "adv"
    frente = "adv" if atras == "lula" else "lula"
    c["atras_no_1t"] = "Lula" if atras == "lula" else ("Flávio" if ano == 2026 else "Bolsonaro")
    c["ganho_atras"] = c[f"d_{atras}"]
    c["ganho_frente"] = c[f"d_{frente}"]
    c["ganho_atras_menos_eliminados"] = c["ganho_atras"] - c["outros_1"]
    c["ganho_atras_sobre_eliminados"] = c["ganho_atras"] / c["outros_1"]
    c["fatia_atras_no_ganho_conjunto"] = c["ganho_atras"] / (c["d_lula"] + c["d_adv"])
    c["ganho_conjunto"] = c["d_lula"] + c["d_adv"]
    # identidade: ΔL + ΔA = outros_1 + Δcomp − ΔBN
    c["identidade_fecha"] = c["d_lula"] + c["d_adv"] == c["outros_1"] + c["d_comp"] - c["d_bn"]
    return c


def contas_nacionais() -> tuple[dict, dict]:
    m26, m22 = municipios_2026(), municipios_2022()
    c26, c22 = conta(m26, 2026), conta(m22, 2022)
    NUMEROS["conta_2026"], NUMEROS["conta_2022"] = c26, c22
    for c in (c26, c22):
        print({k: (round(v, 6) if isinstance(v, float) else v) for k, v in c.items()})

    # tabela de contabilidade (linhas planas, uma por item × ano)
    linhas = []
    for c in (c26, c22):
        advn = "Flávio Bolsonaro" if c["ano"] == 2026 else "Jair Bolsonaro"
        itens = [
            ("Lula", c["lula_1"], c["lula_2"]),
            (advn, c["adv_1"], c["adv_2"]),
            ("Eliminados no 1º turno", c["outros_1"], 0),
            ("Brancos", c["brancos_1"], c["brancos_2"]),
            ("Nulos", c["nulos_1"], c["nulos_2"]),
            ("Votos válidos", c["validos_1"], c["validos_2"]),
            ("Comparecimento", c["comp_1"], c["comp_2"]),
            ("Abstenção", c["abst_1"], c["abst_2"]),
            ("Eleitorado apto", c["aptos_1"], c["aptos_2"]),
        ]
        for nome, a, b in itens:
            linhas.append({"ano": c["ano"], "item": nome, "turno_1": a, "turno_2": b, "delta": b - a})
    salvar("conta-nacional", "Conta nacional entre turnos, 2026 e 2022",
           "Somas de todas as seções (Brasil + exterior). Abstenção = aptos − comparecimento. "
           "Em 2026, votos do candidato 28 (anulado) somados aos nulos, como no painel do TSE.", linhas)

    # gráfico de cascata: de onde vem o ganho conjunto dos finalistas
    cascata = []
    for c in (c26, c22):
        cascata += [
            {"ano": c["ano"], "fonte": "Votos dos eliminados", "votos": c["outros_1"]},
            {"ano": c["ano"], "fonte": "Aumento do comparecimento", "votos": c["d_comp"]},
            {"ano": c["ano"], "fonte": "Queda de brancos e nulos", "votos": -c["d_bn"]},
            {"ano": c["ano"], "fonte": "Ganho de Lula", "votos": c["d_lula"]},
            {"ano": c["ano"], "fonte": "Ganho do adversário", "votos": c["d_adv"]},
        ]
    salvar("fontes-do-ganho", "Fontes contábeis do ganho dos finalistas",
           "Identidade: ganho de Lula + ganho do adversário = eliminados + Δcomparecimento − Δ(brancos+nulos). "
           "São saldos líquidos, não fluxos individuais.", cascata)

    kpis = [
        {"rotulo": "Ganho de Lula entre turnos (2026)", "valor": c26["d_lula"], "formato": "compacto", "cor": "lula",
         "detalhe": f"Flávio: +{c26['d_adv'] / 1e6:.2f} mi".replace(".", ",")},
        {"rotulo": "Ganho de Lula acima de todos os eliminados", "valor": c26["ganho_atras_menos_eliminados"],
         "formato": "num", "detalhe": "fechado por +2,96 mi de comparecimento e −1,82 mi de brancos/nulos"},
        {"rotulo": "Fatia do ganho conjunto que foi para quem estava atrás", "valor": c26["fatia_atras_no_ganho_conjunto"],
         "formato": "pct1", "detalhe": f"2022 (Bolsonaro): {c22['fatia_atras_no_ganho_conjunto'] * 100:.1f}%".replace(".", ",")},
        {"rotulo": "Aumento do comparecimento entre turnos", "valor": c26["d_comp"], "formato": "compacto",
         "detalhe": f"2022: +{c22['d_comp'] / 1e6:.2f} mi".replace(".", ",")},
    ]
    salvar_json("ch01/kpis", {"meta": meta("KPIs do capítulo 1", "Números-chave da conta nacional"), "dados": kpis})
    return c26, c22


# ----------------------------------------------------------------------------------------------
# 3. Reservatório por seção e migração direta mínima
# ----------------------------------------------------------------------------------------------
def reservatorio(s: pl.DataFrame, ano: int, adv: str) -> pl.DataFrame:
    """Para cada seção pareada calcula deltas e limites de migração direta entre finalistas.

    Identidade por seção: ΔL + ΔA = O1 + Δcomp − ΔBN  (O1 = votos nos eliminados no 1º turno).
    Logo 'ganho de Lula maior que o reservatório líquido (O1 + Δcomp − ΔBN)' ⇔ ΔA < 0.

    Migração direta mínima A→L sob a hipótese 'sem rotatividade' (ninguém que votou nos dois turnos
    sai para abstenção/branco/nulo; entradas só pelo saldo): max(0, ΔL − O1 − max(0,Δcomp) − max(0,−ΔBN)).
    Limite folgado (com rotatividade máxima, todo abstencionista do 1º turno podendo entrar):
    max(0, ΔL − O1 − BN1 − Abst1) — essencialmente nunca positivo; registrado para transparência.
    """
    s = s.filter(pl.col("pareada"))
    bn1 = pl.col("brancos_1") + pl.col("nulos_1")
    bn2 = pl.col("brancos_2") + pl.col("nulos_2")
    d = s.with_columns(
        (pl.col("lula_2") - pl.col("lula_1")).alias("dL"),
        (pl.col(f"{adv}_2") - pl.col(f"{adv}_1")).alias("dA"),
        (pl.col("comp_2") - pl.col("comp_1")).alias("dC"),
        (bn2 - bn1).alias("dBN"),
        bn1.alias("bn1"),
        (pl.col("aptos_1") - pl.col("comp_1")).alias("abst1"),
    ).with_columns(
        (pl.col("dL") - pl.col("outros_1") - pl.col("dC").clip(lower_bound=0) - (-pl.col("dBN")).clip(lower_bound=0))
        .clip(lower_bound=0).alias("min_A_para_L"),
        (pl.col("dA") - pl.col("outros_1") - pl.col("dC").clip(lower_bound=0) - (-pl.col("dBN")).clip(lower_bound=0))
        .clip(lower_bound=0).alias("min_L_para_A"),
        (pl.col("dL") - pl.col("outros_1") - pl.col("bn1") - pl.col("abst1")).clip(lower_bound=0).alias("min_A_para_L_folgado"),
        (pl.col("dA") - pl.col("outros_1") - pl.col("bn1") - pl.col("abst1")).clip(lower_bound=0).alias("min_L_para_A_folgado"),
        (-pl.col("dA")).clip(lower_bound=0).alias("perda_A"),
        (-pl.col("dL")).clip(lower_bound=0).alias("perda_L"),
    )
    return d.with_columns(pl.lit(ano).alias("ano"))


def resumo_reservatorio(d: pl.DataFrame, ano: int) -> dict:
    n = d.height
    tam = d["comp_1"].to_numpy()
    out = {
        "ano": ano, "secoes": n,
        "secoes_adv_perdeu": int((d["dA"] < 0).sum()), "secoes_lula_perdeu": int((d["dL"] < 0).sum()),
        "secoes_adv_perdeu_10mais": int((d["dA"] <= -10).sum()), "secoes_lula_perdeu_10mais": int((d["dL"] <= -10).sum()),
        "secoes_min_A_para_L_pos": int((d["min_A_para_L"] > 0).sum()),
        "secoes_min_L_para_A_pos": int((d["min_L_para_A"] > 0).sum()),
        "soma_min_A_para_L": int(d["min_A_para_L"].sum()), "soma_min_L_para_A": int(d["min_L_para_A"].sum()),
        "soma_min_A_para_L_folgado": int(d["min_A_para_L_folgado"].sum()),
        "soma_min_L_para_A_folgado": int(d["min_L_para_A_folgado"].sum()),
        "soma_perda_A": int(d["perda_A"].sum()), "soma_perda_L": int(d["perda_L"].sum()),
        "comp_1_total": int(tam.sum()),
    }
    out["frac_adv_perdeu"] = out["secoes_adv_perdeu"] / n
    out["frac_lula_perdeu"] = out["secoes_lula_perdeu"] / n
    # mesmas somas em níveis mais agregados (o saldo agregado "esconde" a migração local)
    for nivel, chaves in [("municipio", ["sg_uf", "cd_municipio_tse"]), ("uf", ["sg_uf"]), ("nacional", [])]:
        g = (d.group_by(chaves) if chaves else d.select(pl.all()).with_columns(pl.lit(1).alias("_k")).group_by("_k")).agg(
            pl.col("dL", "dA", "outros_1", "dC", "dBN").sum())
        g = g.with_columns(
            (pl.col("dL") - pl.col("outros_1") - pl.col("dC").clip(lower_bound=0) - (-pl.col("dBN")).clip(lower_bound=0))
            .clip(lower_bound=0).alias("mAL"),
            (pl.col("dA") - pl.col("outros_1") - pl.col("dC").clip(lower_bound=0) - (-pl.col("dBN")).clip(lower_bound=0))
            .clip(lower_bound=0).alias("mLA"),
        )
        out[f"soma_min_A_para_L_{nivel}"] = int(g["mAL"].sum())
        out[f"soma_min_L_para_A_{nivel}"] = int(g["mLA"].sum())
        out[f"unidades_adv_perdeu_{nivel}"] = int((g["dA"] < 0).sum())
        out[f"unidades_lula_perdeu_{nivel}"] = int((g["dL"] < 0).sum())
        out[f"unidades_{nivel}"] = g.height
    return out


def reservatorios(s26: pl.DataFrame, s22: pl.DataFrame) -> None:
    d26 = reservatorio(s26, 2026, "flavio")
    d22 = reservatorio(s22, 2022, "bolsonaro")
    r26, r22 = resumo_reservatorio(d26, 2026), resumo_reservatorio(d22, 2022)
    NUMEROS["reservatorio_2026"], NUMEROS["reservatorio_2022"] = r26, r22
    print(json.dumps(r26, indent=1)); print(json.dumps(r22, indent=1))

    # comparação lado a lado (o candidato "que ganhou fatia" e o "que perdeu fatia" em cada ano)
    comp = [
        {"ano": 2026, "medida": "Seções em que o adversário de Lula perdeu votos", "secoes": r26["secoes_adv_perdeu"],
         "fracao": r26["frac_adv_perdeu"]},
        {"ano": 2026, "medida": "Seções em que Lula perdeu votos", "secoes": r26["secoes_lula_perdeu"],
         "fracao": r26["frac_lula_perdeu"]},
        {"ano": 2022, "medida": "Seções em que o adversário de Lula perdeu votos", "secoes": r22["secoes_adv_perdeu"],
         "fracao": r22["frac_adv_perdeu"]},
        {"ano": 2022, "medida": "Seções em que Lula perdeu votos", "secoes": r22["secoes_lula_perdeu"],
         "fracao": r22["frac_lula_perdeu"]},
    ]
    salvar("secoes-perda", "Seções em que um finalista perdeu votos absolutos entre turnos",
           "Perder votos absolutos na mesma seção equivale a 'o ganho do outro superou todo o reservatório "
           "líquido' (eliminados + Δcomparecimento − Δbrancos/nulos).", comp)

    # migração mínima por nível de agregação
    niv = []
    for r, adv in ((r26, "Flávio"), (r22, "Bolsonaro")):
        for nivel, rot in [("secao", "Seção"), ("municipio", "Município"), ("uf", "UF"), ("nacional", "Brasil")]:
            kAL = "soma_min_A_para_L" if nivel == "secao" else f"soma_min_A_para_L_{nivel}"
            kLA = "soma_min_L_para_A" if nivel == "secao" else f"soma_min_L_para_A_{nivel}"
            niv.append({"ano": r["ano"], "nivel": rot, "min_adv_para_lula": r[kAL], "min_lula_para_adv": r[kLA],
                        "adversario": adv})
    salvar("migracao-minima", "Migração direta mínima entre finalistas exigida pela aritmética",
           "Soma, sobre as unidades, de max(0, ΔLula − eliminados − max(0, Δcomparecimento) − max(0, brancos/nulos do 1º "
           "turno − brancos/nulos do 2º)): o aumento de comparecimento e a queda de brancos/nulos só entram quando "
           "positivos. Hipóteses: o mesmo eleitorado nas duas datas e nenhum eleitor que votou nos dois turnos trocou "
           "finalista por abstenção/branco/nulo. É um piso sob essas hipóteses, não uma contagem de pessoas que trocaram "
           "de voto. Quanto mais agregado, mais o saldo esconde.", niv)

    # distribuição: histograma de ΔA/comp_1 e ΔL/comp_1 por seção, 2026 vs 2022 (em p.p. do comparecimento)
    bins = np.arange(-0.30, 0.3001, 0.01)
    hist = []
    for d, ano in ((d26, 2026), (d22, 2022)):
        base = d.filter(pl.col("comp_1") >= 50)
        for col, quem in (("dL", "Lula"), ("dA", "Adversário")):
            x = (base[col] / base["comp_1"]).to_numpy()
            h, _ = np.histogram(np.clip(x, bins[0], bins[-1] - 1e-9), bins=bins)
            for b, c in zip(bins[:-1], h):
                hist.append({"ano": ano, "candidato": quem, "faixa": round(float(b + 0.005), 3), "secoes": int(c)})
    salvar("hist-delta-secao", "Variação de votos por seção, em fração do comparecimento do 1º turno",
           "Seções pareadas com ≥ 50 votantes no 1º turno. Valores fora de ±30% acumulados nas pontas.", hist)

    # por UF: migração mínima A→L 2026 e L→A 2022 por seção, somada
    uf = []
    for d, ano in ((d26, 2026), (d22, 2022)):
        g = d.group_by("sg_uf").agg(
            pl.len().alias("secoes"), (pl.col("dA") < 0).mean().alias("frac_adv_perdeu"),
            (pl.col("dL") < 0).mean().alias("frac_lula_perdeu"),
            pl.col("min_A_para_L").sum().alias("min_adv_para_lula"), pl.col("min_L_para_A").sum().alias("min_lula_para_adv"),
            pl.col("comp_1").sum().alias("comp_1"),
        ).with_columns(pl.lit(ano).alias("ano"))
        uf.append(g)
    uf = pl.concat(uf).with_columns(
        (pl.col("min_adv_para_lula") / pl.col("comp_1")).alias("min_adv_para_lula_sobre_comp"),
        (pl.col("min_lula_para_adv") / pl.col("comp_1")).alias("min_lula_para_adv_sobre_comp"),
    ).sort("ano", "sg_uf", descending=[True, False])
    salvar("reservatorio-uf", "Seções com perda absoluta e migração mínima, por UF",
           "Por UF e ano: fração de seções em que cada finalista perdeu votos; soma por seção da migração "
           "direta mínima (hipótese sem rotatividade).", uf)

    # seções mais extremas (2026): maior perda absoluta de Flávio com ganho de Lula
    top = (d26.filter(pl.col("dA") < 0).sort(["min_A_para_L", "dA"], descending=[True, False]).head(30)
           .select("sg_uf", "nm_municipio", "zona", "secao", "comp_1", "comp_2", "lula_1", "lula_2",
                   pl.col("flavio_1"), pl.col("flavio_2"), "outros_1", "dL", "dA", "min_A_para_L"))
    salvar("secoes-maior-perda-flavio", "Seções com maior migração direta mínima Flávio → Lula (2026)",
           "Top 30 por migração mínima (hipótese sem rotatividade): ganho de Lula acima de eliminados + aumento do "
           "comparecimento + queda de brancos/nulos.", top)
    NUMEROS["top_perda_flavio"] = top.head(10).to_dicts()
    top22 = (d22.filter(pl.col("dL") < 0).sort("dL").head(10)
             .select("sg_uf", "nm_municipio", "zona", "secao", "comp_1", "comp_2", "lula_1", "lula_2",
                     "bolsonaro_1", "bolsonaro_2", "outros_1", "dL", "dA"))
    NUMEROS["top_perda_lula_2022"] = top22.to_dicts()


def main() -> None:
    s26 = secoes_2026()
    s22 = secoes_2022()
    NUMEROS["secoes_2022"] = {"total": s22.height, "pareadas": int(s22["pareada"].sum())}
    reconciliacao(s26)
    contas_nacionais()
    reservatorios(s26, s22)
    (SAIDA_NUM / "01-conta-nacional.json").write_text(json.dumps(NUMEROS, ensure_ascii=False, indent=1, default=str))
    print("ok")


if __name__ == "__main__":
    main()
