"""Capítulo 10 — Benford, dígitos e "impressão digital" da eleição.

1. Dígitos dos votos de Lula e de Flávio (Bolsonaro em 2022) por seção, em 2026 (1º e 2º turnos) e 2022 (2º turno):
   - 1º dígito (1BL), contagens >= 1;
   - 2º dígito (2BL, Mebane), contagens >= 10;
   - último dígito, contagens >= 100.
   Comparados (a) com a lei de Benford teórica (teste "ingênuo") e (b) com um NULO SIMULADO: cada seção sorteia
   seus votos com o seu tamanho real e a proporção suavizada do restante do seu local de votação, 200 vezes.
   Dois nulos: binomial puro e beta-binomial (com a sobredispersão estimada no capítulo 9).
   O mesmo teste ingênuo é aplicado às eleições simuladas — sem alteração inserida — para medir com que
   frequência ele "condenaria" uma eleição em que nada foi alterado na simulação.
2. Impressão digital (Klimek et al., 2012, PNAS): histograma 2D comparecimento x fatia de Lula por seção.

Rodar: uv run python analises/10_benford.py
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from comum import salvar_json  # noqa: E402

_spec = importlib.util.spec_from_file_location("extremos", AQUI / "09_extremos.py")
ext = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ext)

SCRIPT = "analises/10_benford.py"
HOJE = date.today().isoformat()
FONTE = "TSE — boletins de urna por seção (bweb), 2022 e 2026; nulo simulado próprio"
NSIM = 200
RNG = np.random.default_rng(13)

D1 = np.arange(1, 10)
BEN1 = np.log10(1 + 1 / D1)
BEN2 = np.array([sum(np.log10(1 + 1 / (10 * k + d)) for k in range(1, 10)) for d in range(10)])
UNIF = np.full(10, 0.1)
TESTES = {"1BL": (D1, BEN1), "2BL": (np.arange(10), BEN2), "ultimo": (np.arange(10), UNIF)}


def salvar(nome, dados, titulo, descricao, **extra):
    if isinstance(dados, pl.DataFrame):
        dados = dados.with_columns(pl.col(pl.Float64, pl.Float32).round(5)).to_dicts()
    salvar_json(f"ch10/{nome}", {"meta": {"titulo": titulo, "fonte": FONTE, "descricao": descricao,
                                          "gerado_em": HOJE, "script": SCRIPT}, "dados": dados, **extra})


def digitos(x: np.ndarray) -> dict[str, np.ndarray]:
    """Frequências absolutas de cada dígito para os três testes."""
    x = x.astype(np.int64)
    out = {}
    v = x[x >= 1]
    primeiro = v // 10 ** np.floor(np.log10(v)).astype(np.int64)
    out["1BL"] = np.bincount(primeiro, minlength=10)[1:10]
    v = x[x >= 10]
    segundo = (v // 10 ** (np.floor(np.log10(v)).astype(np.int64) - 1)) % 10
    out["2BL"] = np.bincount(segundo, minlength=10)
    v = x[x >= 100]
    out["ultimo"] = np.bincount(v % 10, minlength=10)
    return out


def chi2(obs, esp_frac):
    n = obs.sum()
    e = esp_frac * n
    return float(((obs - e) ** 2 / e).sum())


def mad(obs, esp_frac):
    return float(np.abs(obs / obs.sum() - esp_frac).mean())


def media_digito(obs, digs):
    return float((obs * digs).sum() / obs.sum())


def conjuntos():
    s26 = ext.base_2026()
    s22 = ext.base_2022()
    return [
        ("2026 · 2º turno", s26, "lula_2", "flavio_2", "validos_2", "comp_2", "aptos_2"),
        ("2026 · 1º turno", s26, "lula_1", "flavio_1", "validos_1", "comp_1", "aptos_1"),
        ("2022 · 2º turno", s22, "lula_2", "flavio_2", "validos_2", "comp_2", "aptos_2"),
    ]


def main():
    linhas_dig, linhas_teste, finger, finger_resumo = [], [], [], []
    for rot, df, yl, yf, n, comp, aptos in conjuntos():
        d = df.filter(pl.col(n) > 0)
        nn = d[n].to_numpy().astype(np.int64)
        obs_cand = {"Lula": d[yl].to_numpy(), "Flávio": d[yf].to_numpy()}
        for cand, y in (("Lula", yl), ("Flávio", yf)):
            dd = ext.loo(d, y, n, "v")
            p = dd["v_p"].fill_null(dd[y].sum() / dd[n].sum()).to_numpy()
            grupos = (dd["regiao"].fill_null("?") + "|" + dd["v_viz_local"].cast(pl.Utf8)).to_numpy()
            rho = ext.rho_momentos(dd[y].to_numpy().astype(float), nn.astype(float), p, grupos)
            r = np.array([rho[g] for g in grupos])
            phi = 1 / r - 1
            obs = digitos(obs_cand[cand])
            sims = {m: {t: [] for t in TESTES} for m in ("binomial", "betabinomial")}
            for _ in range(NSIM):
                for m in sims:
                    q = p if m == "binomial" else RNG.beta(p * phi, (1 - p) * phi)
                    ds = digitos(RNG.binomial(nn, q))
                    for t in TESTES:
                        sims[m][t].append(ds[t])
            for t, (digs, ben) in TESTES.items():
                o = obs[t]
                crit = stats.chi2.ppf(0.95, len(digs) - 1)
                linha = {"eleicao": rot, "candidato": cand, "teste": t, "n": int(o.sum()),
                         "chi2_benford": chi2(o, ben), "p_benford": float(stats.chi2.sf(chi2(o, ben), len(digs) - 1)),
                         "mad_benford": mad(o, ben), "media_digito": media_digito(o, digs),
                         "media_digito_benford": float((ben * digs).sum())}
                for m in sims:
                    S = np.array(sims[m][t])  # NSIM x ndig
                    fr = S / S.sum(1, keepdims=True)
                    esp = fr.mean(0)
                    c_obs = chi2(o, esp)
                    c_sim = np.array([chi2(S[i], esp) for i in range(NSIM)])
                    c_ben_sim = np.array([chi2(S[i], ben) for i in range(NSIM)])
                    medias = np.array([media_digito(S[i], digs) for i in range(NSIM)])
                    linha |= {
                        f"chi2_nulo_{m}": c_obs, f"p_nulo_{m}": float(((c_sim >= c_obs).sum() + 1) / (NSIM + 1)),
                        f"chi2_nulo_{m}_p95": float(np.percentile(c_sim, 95)),
                        f"mad_nulo_{m}": mad(o, esp),
                        f"rejeicao_ingenua_{m}": float((c_ben_sim > crit).mean()),
                        f"chi2_benford_sim_mediana_{m}": float(np.median(c_ben_sim)),
                        f"media_digito_{m}_p05": float(np.percentile(medias, 5)),
                        f"media_digito_{m}_p95": float(np.percentile(medias, 95)),
                    }
                    if m == "betabinomial":
                        for k, dg in enumerate(digs):
                            linhas_dig.append({"eleicao": rot, "candidato": cand, "teste": t, "digito": int(dg),
                                               "observado": float(o[k] / o.sum()), "benford": float(ben[k]),
                                               "nulo": float(esp[k]), "nulo_p025": float(np.percentile(fr[:, k], 2.5)),
                                               "nulo_p975": float(np.percentile(fr[:, k], 97.5))})
                linhas_teste.append(linha)
                print(rot, cand, t, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in linha.items()
                                      if k not in ("eleicao", "candidato", "teste")})

        # ---- impressão digital
        tt = (d[comp] / d[aptos]).to_numpy()
        sh = (d[yl] / d[n]).to_numpy()
        ok = np.isfinite(tt) & (d[aptos].to_numpy() > 0)
        H, xe, ye = np.histogram2d(np.clip(tt[ok], 0, 0.9999), np.clip(sh[ok], 0, 0.9999),
                                   bins=[np.linspace(0, 1, 51), np.linspace(0, 1, 51)])
        for i in range(50):
            for j in range(50):
                if H[i, j] > 0:
                    finger.append({"eleicao": rot, "comparecimento": round(float(xe[i] + 0.01), 3),
                                   "fatia_lula": round(float(ye[j] + 0.01), 3), "secoes": int(H[i, j])})
        c = d.with_columns((pl.col(comp) / pl.col(aptos)).alias("t"), (pl.col(yl) / pl.col(n)).alias("s"))
        tot = c.height
        r = {"eleicao": rot, "secoes": tot,
             "comparecimento_medio": float(c["t"].mean()),
             "corr_comparecimento_fatia_lula": float(np.corrcoef(c["t"].to_numpy(), c["s"].to_numpy())[0, 1]),
             "secoes_comp_ge95": int((c["t"] >= 0.95).sum()),
             "secoes_comp_ge95_lula_ge95": int(((c["t"] >= 0.95) & (c["s"] >= 0.95)).sum()),
             "secoes_comp_ge95_flavio_ge95": int(((c["t"] >= 0.95) & (c["s"] <= 0.05)).sum()),
             "fatia_lula_comp_ge95": float(c.filter(pl.col("t") >= 0.95).select(pl.col(yl).sum() / pl.col(n).sum()).item()),
             "fatia_lula_total": float(c.select(pl.col(yl).sum() / pl.col(n).sum()).item()),
             "secoes_comp_100": int((c["t"] >= 1).sum())}
        finger_resumo.append(r)
        print(r)

    td = pl.DataFrame(linhas_teste)
    with pl.Config(tbl_rows=40, tbl_cols=40, tbl_width_chars=300):
        print(td.select("eleicao", "candidato", "teste", "n", "chi2_benford", "p_benford", "rejeicao_ingenua_binomial",
                        "rejeicao_ingenua_betabinomial", "chi2_nulo_betabinomial", "p_nulo_betabinomial",
                        "chi2_nulo_binomial", "p_nulo_binomial"))
    salvar("testes", td, "Testes de dígitos: contra Benford e contra o nulo simulado",
           f"chi2/MAD contra Benford teórico e contra a distribuição esperada em {NSIM} eleições simuladas por nulo (binomial e beta-binomial). rejeicao_ingenua_* = fração das eleições simuladas (sem alteração inserida) que o teste de Benford ingênuo rejeitaria a 5%.")
    salvar("digitos", pl.DataFrame(linhas_dig), "Frequência de cada dígito: observado, Benford e nulo simulado",
           "Frações; nulo = média do nulo beta-binomial, com faixa de 95% (p025–p975).")
    salvar("impressao-digital", pl.DataFrame(finger), "Impressão digital: comparecimento x fatia de Lula por seção",
           "Nº de seções em cada célula de 2 p.p. x 2 p.p. (centro da célula). Fatia de Lula sobre os votos válidos (no 1º turno de 2026, sobre todos os nominais).",
           resumo=finger_resumo)
    salvar("impressao-resumo", pl.DataFrame(finger_resumo), "Impressão digital: resumo por eleição",
           "Seções com comparecimento >= 95% e fatia >= 95% para um candidato; correlação comparecimento x fatia de Lula.")


def klimek_2026():
    """Seções do 2º turno de 2026 com comparecimento >= 95% e Lula >= 95%: de onde vieram (1º turno)?
    E a variação de comparecimento entre turnos nos redutos de cada candidato (enchimento de urna elevaria
    o comparecimento justamente onde um candidato domina)."""
    s = ext.base_2026().with_columns(
        (pl.col("comp_2") / pl.col("aptos_2")).alias("t2"), (pl.col("comp_1") / pl.col("aptos_1")).alias("t1"),
        (pl.col("lula_2") / pl.col("validos_2")).alias("s2"),
        (pl.col("lula_1") / (pl.col("lula_1") + pl.col("flavio_1"))).alias("s1"))
    x = s.filter((pl.col("t2") >= 0.95) & (pl.col("s2") >= 0.95))
    res = [{"grupo": "comp>=95% e Lula>=95% no 2º turno", "secoes": x.height,
            "mediana_aptos": float(x["aptos_2"].median()), "mediana_comp_1t": float(x["t1"].median()),
            "com_comp_1t_ge90": int((x["t1"] >= 0.9).sum()), "com_lula_1t_ge95": int((x["s1"] >= 0.95).sum()),
            "margem_lula_2t": int((x["lula_2"] - x["flavio_2"]).sum()),
            "aumento_comparecimento": int((x["comp_2"] - x["comp_1"]).sum())}]
    for nome, cond in [("Lula >= 95% no 2º turno", pl.col("s2") >= 0.95), ("Flávio >= 95% no 2º turno", pl.col("s2") <= 0.05),
                       ("todas as seções", pl.lit(True))]:
        y = s.filter(cond & pl.col("t1").is_not_null())
        res.append({"grupo": nome, "secoes": y.height, "var_comparecimento_pp": float(100 * (y["t2"] - y["t1"]).mean())})
    print(res)
    salvar("klimek-2026", res, "Comparecimento x fatia extrema: persistência e variação entre turnos (2026)",
           "Se houvesse enchimento de urnas, o comparecimento subiria mais nos redutos do beneficiado.")


if __name__ == "__main__":
    main()
    klimek_2026()
