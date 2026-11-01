"""Reexame exploratório de Maués/AM, zona 5, seção 176.

Rode: OPENBLAS_NUM_THREADS=1 uv run python analises/17_maues_zero.py
Os valores-p pressupõem dois turnos como amostras independentes com a mesma
proporção, hipótese que não é verificável e é inadequada para eleitores pareados.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import polars as pl
from scipy.special import betaln
from scipy.stats import hypergeom

from comum import salvar_json, secoes_2026


def main():
    s = secoes_2026().filter(pl.col("pareada") & (pl.col("validos_1") > 0) & (pl.col("validos_2") > 0))
    alvo = ((pl.col("sg_uf") == "AM") & (pl.col("cd_municipio_tse") == "02615") &
            (pl.col("zona") == "0005") & (pl.col("secao") == "0176"))
    d = s.filter(alvo)
    assert d.height == 1
    x = d.row(0, named=True)
    n1, n2, f1, f2 = (s[k].to_numpy().astype(np.int64) for k in ("validos_1", "validos_2", "flavio_1", "flavio_2"))
    # Fisher unilateral: proporção de Flávio não cai, supondo amostras independentes.
    p = hypergeom.sf(f1 - 1, n1 + n2, f1 + f2, n1)
    i = int(np.flatnonzero(s.select(alvo).to_series().to_numpy())[0])
    p0 = float(p[i])
    ordem = np.argsort(p, kind="stable")
    ordenados = p[ordem]
    m = len(p)
    rank_max = int(np.searchsorted(ordenados, p0, side="right"))
    holm = float(min(1, np.maximum.accumulate(ordenados * (m - np.arange(m)))[rank_max - 1]))
    bh = float(min(1, np.minimum.accumulate((ordenados * m / np.arange(1, m + 1))[::-1])[::-1][rank_max - 1]))
    amostra = s.filter(pl.col("flavio_1").is_between(10, 22) & pl.col("validos_1").is_between(250, 400) &
                       (pl.col("lula_1") / (pl.col("lula_1") + pl.col("flavio_1")) >= 0.85))
    peers = {"criterio": "10–22 votos em Flávio, 250–400 válidos e Lula ≥85% dos dois finalistas no 1º turno",
             "n_brasil_exterior": amostra.height, "zeros_2t": amostra.filter(pl.col("flavio_2") == 0).height,
             "n_am": amostra.filter(pl.col("sg_uf") == "AM").height,
             "zeros_am": amostra.filter((pl.col("sg_uf") == "AM") & (pl.col("flavio_2") == 0)).height,
             "observacao": "faixas escolhidas após a identificação de Maués; não são amostra aleatória nem teste confirmatório"}
    viz = s.filter((pl.col("sg_uf") == "AM") & (pl.col("cd_municipio_tse") == "02615") &
                   (pl.col("zona") == "0005") & (pl.col("local") == "1406"))
    mun = s.filter((pl.col("sg_uf") == "AM") & (pl.col("cd_municipio_tse") == "02615"))
    colunas = ["lula_1", "flavio_1", "outros_1", "brancos_1", "nulos_1", "validos_1", "comp_1", "aptos_1",
               "lula_2", "flavio_2", "brancos_2", "nulos_2", "validos_2", "comp_2", "aptos_2", "n_votos_log"]
    t1, t2, votos = x["validos_1"], x["validos_2"], x["flavio_1"]
    # Beta(1/2,1/2) ilustra a incerteza da taxa sob um modelo estacionário;
    # não corrige dependência ou mudanças entre turnos.
    beta_preditiva = float(np.exp(betaln(votos + .5, t1 - votos + .5 + t2) - betaln(votos + .5, t1 - votos + .5)))
    resultado = {
        "secao": {k: x[k] for k in colunas} | {"uf": "AM", "municipio": "Maués", "zona": "0005", "secao": "0176",
                                                 "local": x["local"], "urna_1": x["nr_urna_1"], "urna_2": x["nr_urna_2"]},
        "outra_secao_local": viz.select("secao", "lula_1", "flavio_1", "lula_2", "flavio_2", "comp_1", "comp_2").sort("secao").to_dicts(),
        "municipio": mun.select(pl.len().alias("secoes"), pl.col("lula_1", "flavio_1", "lula_2", "flavio_2", "comp_1", "comp_2").sum()).row(0, named=True),
        "comparaveis": peers,
        "testes_hipoteticos": {"fatia_fixa_p_zero": float((1 - votos / t1) ** t2),
                               "beta_jeffreys_p_zero": beta_preditiva,
                               "fisher_unilateral_p": p0, "familia_secoes": m,
                               "ordem_fisher": rank_max, "holm": holm, "bh_exploratorio": bh,
                               "metodo": "valores de dois turnos tratados como amostras independentes e sem mudança da proporção; premissas não demonstradas; filtros e caso escolhidos após observar os dados"},
    }
    salvar_json("ch09/maues-reexame", {"meta": {"script": "analises/17_maues_zero.py", "fonte": "TSE — BUs e resumo de logs por seção, 2026", "gerado_em": date.today().isoformat(),
                                                "descricao": "Análise exploratória, não mede probabilidade de fraude nem compara votos individuais."}, "dados": resultado})
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
