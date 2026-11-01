"""Experimento exploratório: conversão sintética de abstenção ou branco/nulo em Lula.

Usa BUs reais como referência, sem supor que sejam uma verdade independente.
Rode: OPENBLAS_NUM_THREADS=1 uv run python analises/14_poder_acrescimo.py
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy import stats

from comum import salvar_json

spec = importlib.util.spec_from_file_location("poder", Path(__file__).with_name("05_poder_detectores.py"))
poder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poder)
RNG = np.random.default_rng(20261031)


def main():
    _, a = poder.carregar()
    m = poder.covariaveis_municipais(a)
    l, f = a["l2"], a["f2"]
    n = l + f
    prob = l / np.maximum(n, 1)
    q = m["Q"]
    def calcular(l2, f2):
        lm, fm = m["soma"](l2), m["soma"](f2)
        nf = np.maximum(lm + fm, 1)
        y = fm / nf - m["sf1"]
        r = y - q @ (q.T @ y)
        z = np.column_stack([np.ones_like(nf), 1 / nf])
        ab = np.linalg.lstsq(z, r ** 2, rcond=None)[0]
        ps = np.sort(2 * stats.norm.sf(np.abs(r / np.sqrt(np.maximum(z @ ab, 1e-8)))))
        hits = np.flatnonzero(ps <= 0.05 * np.arange(1, len(ps) + 1) / len(ps))
        return np.array([hits[-1] + 1 if hits.size else 0, poder.chi2_digitos(l2, np.full(10, 0.1), "ultimo")])

    def sim_base():
        ll = RNG.binomial(n, prob)
        return ll, n - ll

    nulo = np.array([calcular(*sim_base()) for _ in range(80)])
    limites = np.quantile(nulo, [0.025, 0.975], axis=0)
    linhas = []
    for fonte in ("ausentes", "brancos_nulos"):
        capacidade = np.maximum(a["a2"] - a["c2"], 0) if fonte == "ausentes" else a["i2"]
        for forma in ("uniforme", "proporcional_lula"):
            for taxa in (0.01, 0.05, 0.10, 0.20):
                resultados, alterados = [], []
                for _ in range(20):
                    ll, ff = sim_base()
                    fator = np.ones(len(n)) if forma == "uniforme" else ll / np.maximum(n, 1)
                    # A mesma taxa alvo nacional, limitada a 100% por seção.
                    fator = fator / max(float(np.average(fator, weights=capacidade)), 1e-12)
                    add = RNG.binomial(capacidade, np.clip(taxa * fator, 0, 1))
                    resultados.append(calcular(ll + add, ff))
                    alterados.append(int(add.sum()))
                res = np.array(resultados)
                alarme = ((res < limites[0]) | (res > limites[1])).mean(axis=0)
                linhas.append({"fonte": "Abstenção" if fonte == "ausentes" else "Brancos/nulos",
                               "forma": "Uniforme" if forma == "uniforme" else "Proporcional à fatia de Lula",
                               "taxa": taxa, "votos_media": float(np.mean(alterados)),
                               "alarme_fdr": float(alarme[0]), "alarme_ultimo_digito": float(alarme[1])})
                print(linhas[-1], flush=True)
    salvar_json("ch05/poder-acrescimo", {"meta": {"script": "analises/14_poder_acrescimo.py", "fonte": "TSE — BUs; simulação própria", "descricao": "80 nulos binomiais, 20 réplicas por cenário; alerta fora do intervalo central de 95% do nulo. O nulo parte dos dados reais; não mede fraude existente. Retenção ecológica de Flávio com regressoras do 1º turno e F2 inalterados é invariável por construção; não é detector desses acréscimos.", "semente": 20261031, "limites_fdr": limites[:, 0].tolist(), "limites_ultimo_digito": limites[:, 1].tolist()}, "dados": linhas})


if __name__ == "__main__":
    main()
