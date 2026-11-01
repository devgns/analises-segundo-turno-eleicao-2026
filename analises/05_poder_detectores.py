"""Capítulo 05 — Os detectores conseguem ver uma alteração uniforme? (testes de poder)

Tese testada: uma alteração nacional e quase uniforme desloca a média; comparações entre unidades
(outliers, resíduos de regressão, FDR) não a enxergam. Aqui isso é medido, não suposto.

Desenho
-------
* Mundo "limpo" de referência = os dados reais de 2026, por seção (499.205 seções pareadas).
  Cada réplica re-sorteia a divisão Lula/Flávio de cada seção (binomial com a própria fatia),
  para que o detector enfrente o ruído amostral.
* Manipulação sintética aplicada a cópias: votos de Flávio passam para Lula. O tamanho é
  medido em % dos votos NACIONAIS de Flávio (k). Cenários:
    uniforme       k% dos votos de Flávio em toda seção
    proporcional   taxa ∝ fatia de Flávio na seção (mais onde ele é forte), mesmo total nacional
    secoes10       só 10% das seções (sorteadas), mesmo total
    municipios10   só 10% dos municípios (sorteados), mesmo total
    urna_ue2020    só urnas modelo UE2020, mesmo total
    tardias        só seções que encerraram após 17h05 (horário local), mesmo total
* Detectores (o que um analista faria com os dados de 2026):
    D1 outliers de seção (z robusto da variação da fatia de Lula, |z|>4)
    D2 municípios sinalizados por FDR (resíduo de regressão com regressoras do 1º turno e coeficientes reajustados a cada réplica, q<0,05)
    D3 desvio-padrão do resíduo municipal (dispersão)
    D4 Benford, 2º dígito dos votos de Lula por seção (χ²)
    D5 último dígito dos votos de Lula por seção (χ²)
    D6 seções "extremas": Flávio perde ≥20% dos votos do 1º turno (com ≥50 votos)
    D7 impressão digital comparecimento × voto (inclinação da fatia de Lula sobre o comparecimento)
    D8 dispersão municipal da oscilação comparada com 2022 (razão de desvios-padrão)
    D9 forma da distribuição 1º × 2º turno (KS entre fatias padronizadas de Flávio por seção)
    S1 retenção de Flávio estimada (regressão ecológica por seção) — assinatura de "nível"
  Alarme: estatística fora do intervalo central de 95% das réplicas sem manipulação. Isso é um
  detector "oráculo" (sabe como os dados limpos seriam, a menos do ruído amostral): o poder
  medido é um LIMITE SUPERIOR do poder de um analista real.
* Assinaturas que uma transferência uniforme deixaria, medidas nos dados reais e comparadas com 2022
  e com as pesquisas: retenção líquida por candidato (regressão ecológica), ganho de Lula acima do
  "estoque" disponível, seções sem eliminados.

Rodar: uv run python analises/05_poder_detectores.py   (≈10–20 min; usa ~2 GB de RAM)
      uv run python analises/05_poder_detectores.py --so-assinaturas   (só a parte de assinaturas)
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
from scipy import optimize, stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import ACHADOS, municipios_2022, municipios_2026, salvar_json, secoes_2026  # noqa: E402

SCRIPT = "analises/05_poder_detectores.py"
HOJE = date.today().isoformat()
FONTE = "TSE — boletins de urna por seção, 2026 (e municípios, 2022); manipulações sintéticas; cálculo próprio"
KS_ = [0.0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.06, 0.08]
CENARIOS = ["uniforme", "proporcional", "secoes10", "municipios10", "urna_ue2020", "tardias"]
NOMES_CEN = {
    "uniforme": "Uniforme (mesma % dos votos de Flávio em toda seção)",
    "proporcional": "Proporcional à força de Flávio na seção",
    "secoes10": "Concentrada em 10% das seções",
    "municipios10": "Concentrada em 10% dos municípios",
    "urna_ue2020": "Só urnas modelo UE2020",
    "tardias": "Só seções que encerraram após 17h05",
}
DETECTORES = {
    "d1_outliers_secao": "Outliers de seção (|z| robusto > 4)",
    "d2_fdr_municipios": "Municípios sinalizados por FDR (regressão com regressoras do 1º turno)",
    "d3_dispersao_residuo": "Dispersão do resíduo municipal",
    "d4_benford2": "Benford, 2º dígito (votos de Lula por seção)",
    "d5_ultimo_digito": "Último dígito (votos de Lula por seção)",
    "d6_extremos": "Seções em que Flávio perde ≥ 20% dos votos",
    "d7_digital": "Impressão digital comparecimento × voto",
    "d8_disp_vs_2022": "Dispersão municipal comparada com 2022",
    "d9_forma_1t2t": "Forma da distribuição 1º × 2º turno",
    "s1_retencao_f": "Retenção de Flávio (regressão ecológica)",
}
N_NULO = 80
N_ALT = 20


# ------------------------------------------------------------------ dados
def carregar():
    s = (secoes_2026().filter(pl.col("pareada") & (pl.col("sg_uf") != "ZZ"))
         .with_columns((pl.col("encerramento_2").dt.hour().cast(pl.Int32) * 60
                        + pl.col("encerramento_2").dt.minute().cast(pl.Int32)).alias("enc_min")))
    mun_id = s["cd_municipio_ibge"].to_numpy()
    codigos, inv = np.unique(mun_id, return_inverse=True)
    A = {
        "l1": s["lula_1"].to_numpy().astype(np.int64), "f1": s["flavio_1"].to_numpy().astype(np.int64),
        "o1": s["outros_1"].to_numpy().astype(np.int64),
        "i1": (s["brancos_1"] + s["nulos_1"]).to_numpy().astype(np.int64),
        "c1": s["comp_1"].to_numpy().astype(np.int64), "a1": s["aptos_1"].to_numpy().astype(np.int64),
        "l2": s["lula_2"].to_numpy().astype(np.int64), "f2": s["flavio_2"].to_numpy().astype(np.int64),
        "i2": (s["brancos_2"] + s["nulos_2"]).to_numpy().astype(np.int64),
        "c2": s["comp_2"].to_numpy().astype(np.int64), "a2": s["aptos_2"].to_numpy().astype(np.int64),
        "ue2020": (s["modelo_urna"] == "UE2020").fill_null(False).to_numpy(),
        "tardia": (s["enc_min"] >= 17 * 60 + 5).fill_null(False).to_numpy(),
        "mun": inv, "codigos": codigos,
        "regiao": s["regiao"].to_numpy(), "uf": s["sg_uf"].to_numpy(),
    }
    return s, A


def covariaveis_municipais(A):
    """Matriz de desenho municipal com covariáveis SÓ do 1º turno (fixa entre réplicas)."""
    nm = len(A["codigos"])
    soma = lambda v: np.bincount(A["mun"], weights=v, minlength=nm)  # noqa: E731
    l1, f1, o1, i1, c1, a1 = (soma(A[k]) for k in ("l1", "f1", "o1", "i1", "c1", "a1"))
    sf1 = f1 / np.maximum(l1 + f1, 1)
    val1 = l1 + f1 + o1
    o1s = o1 / np.maximum(val1, 1)
    reg_mun = np.empty(nm, dtype=object)
    reg_mun[A["mun"]] = A["regiao"]
    cols = [np.ones(nm), sf1, sf1 ** 2, sf1 ** 3, o1s, o1s ** 2, sf1 * o1s, i1 / np.maximum(c1, 1),
            c1 / np.maximum(a1, 1), np.log(np.maximum(a1, 1)), np.log(np.maximum(a1, 1)) ** 2]
    for g in sorted(set(reg_mun))[1:]:
        cols.append((reg_mun == g).astype(float))
    X = np.column_stack(cols)
    return {"X": X, "Q": np.linalg.qr(X)[0], "sf1": sf1, "nm": nm, "soma": soma}


# ------------------------------------------------------------------ manipulação
def taxas(cen: str, k: float, A, l2, f2, rng) -> np.ndarray:
    """Taxa por seção (fração dos votos de Flávio que vira Lula) com total nacional = k·ΣF."""
    n = len(f2)
    F = f2.astype(float)
    tot = k * F.sum()
    if k == 0:
        return np.zeros(n)
    if cen == "uniforme":
        return np.full(n, k)
    if cen == "proporcional":
        w = f2 / np.maximum(l2 + f2, 1)
    elif cen == "secoes10":
        w = (rng.random(n) < 0.10).astype(float)
    elif cen == "municipios10":
        escolhidos = rng.random(len(A["codigos"])) < 0.10
        w = escolhidos[A["mun"]].astype(float)
    elif cen == "urna_ue2020":
        w = A["ue2020"].astype(float)
    elif cen == "tardias":
        w = A["tardia"].astype(float)
    else:
        raise ValueError(cen)
    t = w * tot / np.sum(w * F)
    return np.minimum(t, 0.95)


# ------------------------------------------------------------------ detectores
DIG2 = np.array([sum(np.log10(1 + 1 / (10 * d1 + d2)) for d1 in range(1, 10)) for d2 in range(10)])


def chi2_digitos(v: np.ndarray, esperado: np.ndarray, pos: str) -> float:
    if pos == "ultimo":
        x = v[v >= 10] % 10
    else:  # segundo dígito
        x = v[v >= 10]
        x = (x // 10 ** (np.floor(np.log10(x)).astype(int) - 1)) % 10
    obs = np.bincount(x.astype(int), minlength=10)
    e = esperado * obs.sum()
    return float(np.sum((obs - e) ** 2 / e))


def ks_padronizado(a: np.ndarray, b: np.ndarray) -> float:
    za = (a - a.mean()) / a.std()
    zb = (b - b.mean()) / b.std()
    za.sort()
    zb.sort()
    tudo = np.concatenate([za, zb])
    cdf_a = np.searchsorted(za, tudo, side="right") / len(za)
    cdf_b = np.searchsorted(zb, tudo, side="right") / len(zb)
    return float(np.max(np.abs(cdf_a - cdf_b)))  # estatística D de Kolmogorov–Smirnov


def detectores(A, M, l2, f2, sd22: float, X1eco: np.ndarray) -> dict:
    l1, f1 = A["l1"], A["f1"]
    fin1, fin2 = l1 + f1, l2 + f2
    ok = (fin1 >= 100) & (fin2 >= 100)
    sl1 = l1[ok] / fin1[ok]
    sl2 = l2[ok] / fin2[ok]
    dsh = sl2 - sl1
    med = np.median(dsh)
    mad = 1.4826 * np.median(np.abs(dsh - med))
    z = (dsh - med) / mad
    out = {"d1_outliers_secao": float(np.sum(np.abs(z) > 4))}

    # municipal: regressão com covariáveis do 1º turno (coeficientes reajustados ao 2º), resíduo heterocedástico, FDR
    L2m, F2m = M["soma"](l2), M["soma"](f2)
    nfin = np.maximum(L2m + F2m, 1)
    y = F2m / nfin - M["sf1"]
    Q = M["Q"]
    r = y - Q @ (Q.T @ y)
    # variância = a + b/n, por momentos
    Z = np.column_stack([np.ones_like(nfin), 1 / nfin])
    ab = np.linalg.lstsq(Z, r ** 2, rcond=None)[0]
    var = np.maximum(Z @ ab, 1e-8)
    zr = r / np.sqrt(var)
    p = 2 * stats.norm.sf(np.abs(zr))
    o = np.argsort(p)
    crit = p[o] <= 0.05 * np.arange(1, len(p) + 1) / len(p)
    nflag = int(np.max(np.where(crit)[0]) + 1) if crit.any() else 0
    out["d2_fdr_municipios"] = float(nflag)
    out["_flag_idx"] = o[:nflag]
    out["d3_dispersao_residuo"] = float(np.std(r))
    out["d4_benford2"] = chi2_digitos(l2, DIG2, "segundo")
    out["d5_ultimo_digito"] = chi2_digitos(l2, np.full(10, 0.1), "ultimo")
    out["d6_extremos"] = float(np.sum((f1 >= 50) & (f2 <= 0.8 * f1)))
    turn2 = A["c2"][ok] / np.maximum(A["a2"][ok], 1)
    out["d7_digital"] = float(np.polyfit(turn2, sl2, 1)[0])
    out["d8_disp_vs_2022"] = float(np.std(y) / sd22)
    out["d9_forma_1t2t"] = ks_padronizado(1 - sl1, 1 - sl2)
    # S1: retenção de Flávio = coeficiente de F1 na regressão (sem intercepto) de F2 sobre os estoques do 1º turno
    beta = np.linalg.lstsq(X1eco, f2.astype(float), rcond=None)[0]
    out["s1_retencao_f"] = float(beta[1])
    return out


# ------------------------------------------------------------------ assinaturas nos dados reais
def ecologica(L1, F1, O1, I1, AB1, alvo) -> np.ndarray:
    X = np.column_stack([L1, F1, O1, I1, AB1]).astype(float)
    return optimize.nnls(X, alvo.astype(float))[0]


def assinaturas(A) -> dict:
    ab1 = A["a1"] - A["c1"]
    sec = {
        "lula": ecologica(A["l1"], A["f1"], A["o1"], A["i1"], ab1, A["l2"]),
        "flavio": ecologica(A["l1"], A["f1"], A["o1"], A["i1"], ab1, A["f2"]),
    }
    m26 = municipios_2026().filter(pl.col("sg_uf") != "ZZ")
    m22 = municipios_2022().filter(pl.col("sg_uf") != "ZZ")

    def eco_mun(m, cand):
        L1, F1 = m["lula_1"].to_numpy(), m[f"{cand}_1"].to_numpy()
        O1, I1 = m["outros_1"].to_numpy(), (m["brancos_1"] + m["nulos_1"]).to_numpy()
        AB1 = (m["aptos_1"] - m["comp_1"]).to_numpy()
        return {"lula": ecologica(L1, F1, O1, I1, AB1, m["lula_2"].to_numpy()),
                "direita": ecologica(L1, F1, O1, I1, AB1, m[f"{cand}_2"].to_numpy())}

    mun26, mun22 = eco_mun(m26, "flavio"), eco_mun(m22, "bolsonaro")
    # incerteza: bootstrap de municípios (300 réplicas) das taxas de retenção dos dois candidatos
    rngb = np.random.default_rng(5)
    boot = {"2026": [], "2022": []}
    for ano, m, cand in (("2026", m26, "flavio"), ("2022", m22, "bolsonaro")):
        for _ in range(300):
            mb = m[rngb.integers(0, m.height, m.height)]
            e = eco_mun(mb, cand)
            boot[ano].append((e["lula"][0], e["direita"][1]))
    ic = {ano: {"ret_lula": np.quantile([b[0] for b in v], [0.025, 0.975]).round(4).tolist(),
                "ret_direita": np.quantile([b[1] for b in v], [0.025, 0.975]).round(4).tolist()} for ano, v in boot.items()}

    # ganho de Lula acima do "estoque" disponível: eliminados + brancos/nulos + aumento de comparecimento
    dl = A["l2"] - A["l1"]
    dfv = A["f2"] - A["f1"]
    estoque = A["o1"] + A["i1"] + np.maximum(A["c2"] - A["c1"], 0)
    fin1 = A["l1"] + A["f1"]
    sf1 = A["f1"] / np.maximum(fin1, 1)
    faixas = [(0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 1.01)]
    excesso = []
    for lo, hi in faixas:
        mk = (sf1 >= lo) & (sf1 < hi) & (fin1 >= 50)
        excesso.append({
            "faixa_f1": f"{int(lo * 100)}–{min(int(hi * 100), 100)}%", "secoes": int(mk.sum()),
            "pct_lula_acima_estoque": float(np.mean(dl[mk] > estoque[mk])),
            "pct_flavio_acima_estoque": float(np.mean(dfv[mk] > estoque[mk])),
            "pct_flavio_perde": float(np.mean(dfv[mk] < 0)), "pct_lula_perde": float(np.mean(dl[mk] < 0)),
            "delta_f_rel": float(dfv[mk].sum() / A["f1"][mk].sum()), "delta_l_rel": float(dl[mk].sum() / A["l1"][mk].sum()),
        })
    # seções quase sem eliminados (<2% dos válidos) e sem crescimento de comparecimento
    val1 = A["l1"] + A["f1"] + A["o1"]
    poucos = (A["o1"] < 0.02 * val1) & (A["c2"] <= A["c1"]) & (val1 >= 50)
    pe = {
        "secoes": int(poucos.sum()), "lula_1": int(A["l1"][poucos].sum()), "flavio_1": int(A["f1"][poucos].sum()),
        "eliminados_1": int(A["o1"][poucos].sum()), "invalidos_1": int(A["i1"][poucos].sum()),
        "delta_lula": int(dl[poucos].sum()), "delta_flavio": int(dfv[poucos].sum()),
        "delta_invalidos": int((A["i2"] - A["i1"])[poucos].sum()), "delta_comp": int((A["c2"] - A["c1"])[poucos].sum()),
    }
    # o simétrico: seções quase sem eliminados onde Flávio é forte
    pe_f = (A["o1"] < 0.02 * val1) & (A["c2"] <= A["c1"]) & (val1 >= 50) & (sf1 > 0.6)
    pe["fortes_flavio"] = {"secoes": int(pe_f.sum()), "delta_lula": int(dl[pe_f].sum()), "delta_flavio": int(dfv[pe_f].sum()),
                           "eliminados_1": int(A["o1"][pe_f].sum()), "invalidos_1": int(A["i1"][pe_f].sum()),
                           "flavio_1": int(A["f1"][pe_f].sum()), "lula_1": int(A["l1"][pe_f].sum())}
    # contrafactual: se uma transferência uniforme de k_virada (votos que viram o resultado) tivesse ocorrido,
    # quanto Lula teria ganho, sem ela, nas seções fortes de Flávio quase sem eliminados e com comparecimento em queda?
    k_v = float((A["l2"].sum() - A["f2"].sum()) / 2 / A["f2"].sum())
    pe["fortes_flavio"]["k_virada"] = k_v
    pe["fortes_flavio"]["votos_fraude_k_virada"] = float(k_v * A["f2"][pe_f].sum())
    pe["fortes_flavio"]["delta_lula_sem_fraude"] = float(dl[pe_f].sum() - k_v * A["f2"][pe_f].sum())
    pe["fortes_flavio"]["k_max_delta_lula_nao_negativo"] = float(dl[pe_f].sum() / A["f2"][pe_f].sum())
    pe["fortes_flavio"]["pct_secoes_lula_perde_obs"] = float(np.mean(dl[pe_f] < 0))
    pe["fortes_flavio"]["pct_secoes_lula_perde_sem_fraude"] = float(np.mean(dl[pe_f] - k_v * A["f2"][pe_f] < 0))
    # o mesmo para todas as seções fortes de Flávio (fatia > 70%), sem filtrar eliminados
    forte = (sf1 > 0.7) & (fin1 >= 50)
    pe["todas_fortes_70"] = {"secoes": int(forte.sum()), "pct_lula_perde_obs": float(np.mean(dl[forte] < 0)),
                             "pct_lula_perde_sem_fraude": float(np.mean(dl[forte] - k_v * A["f2"][forte] < 0)),
                             "pct_flavio_perde_obs": float(np.mean(dfv[forte] < 0))}
    return {"eco_secao_2026": {k: v.round(4).tolist() for k, v in sec.items()},
            "eco_mun_2026": {k: v.round(4).tolist() for k, v in mun26.items()},
            "eco_mun_2022": {k: v.round(4).tolist() for k, v in mun22.items()},
            "ic_mun": ic, "excesso": excesso, "poucos_eliminados": pe}


# ------------------------------------------------------------------ principal
def so_assinaturas():
    """Recalcula só as assinaturas (rápido), sem refazer as réplicas de poder."""
    _, A = carregar()
    ass = assinaturas(A)
    salvar_json("cap05-assinaturas", {"meta": meta("Assinaturas de uma transferência uniforme, nos dados reais",
                                                   "eco_*: taxas de transição estimadas por regressão ecológica não negativa (origens: Lula, Flávio/Bolsonaro, eliminados, brancos+nulos, abstenção do 1º turno → destino). excesso: % de seções em que o ganho do candidato supera eliminados + brancos/nulos + aumento de comparecimento."),
                                      **{k: v for k, v in ass.items() if k != "excesso"}, "dados": ass["excesso"]})
    arq = ACHADOS / "05-poder-detectores.numeros.json"
    r = json.loads(arq.read_text())
    r["assinaturas"] = ass
    arq.write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(ass["poucos_eliminados"], indent=1))


def main():
    t0 = time.time()
    s, A = carregar()
    M = covariaveis_municipais(A)
    m22 = municipios_2022().filter(pl.col("sg_uf") != "ZZ")
    y22 = (m22["bolsonaro_2"] / (m22["bolsonaro_2"] + m22["lula_2"]) - m22["bolsonaro_1"] / (m22["bolsonaro_1"] + m22["lula_1"])).to_numpy()
    sd22 = float(np.std(y22))
    X1eco = np.column_stack([A["l1"], A["f1"], A["o1"], A["i1"], A["a1"] - A["c1"]]).astype(float)
    rng = np.random.default_rng(2026)
    fin = A["l2"] + A["f2"]
    p_f = A["f2"] / np.maximum(fin, 1)

    def replica():
        f2 = rng.binomial(fin, p_f)
        return fin - f2, f2

    # valores reais (sem re-sorteio)
    real = detectores(A, M, A["l2"], A["f2"], sd22, X1eco)
    real.pop("_flag_idx")
    print("real", real, f"{time.time() - t0:.0f}s")

    nulos = []
    for _ in range(N_NULO):
        l2, f2 = replica()
        d = detectores(A, M, l2, f2, sd22, X1eco)
        d.pop("_flag_idx")
        nulos.append(d)
    nul = {k: np.array([d[k] for d in nulos]) for k in DETECTORES}
    lim = {k: (np.quantile(v, 0.025), np.quantile(v, 0.975)) for k, v in nul.items()}
    print("nulo pronto", f"{time.time() - t0:.0f}s")

    linhas, exemplo = [], {}
    total_f = A["f2"].sum()
    for cen in CENARIOS:
        for k in KS_[1:]:
            alarmes = {d: 0 for d in DETECTORES}
            vals = {d: [] for d in DETECTORES}
            loc = []
            for _ in range(N_ALT):
                l2, f2 = replica()
                t = taxas(cen, k, A, l2, f2, rng)
                mv = rng.binomial(f2, t)
                l2m, f2m = l2 + mv, f2 - mv
                d = detectores(A, M, l2m, f2m, sd22, X1eco)
                flag = d.pop("_flag_idx")
                # localização: fração dos municípios sinalizados que de fato foram manipulados (>1% dos votos de F)
                movidos_m = M["soma"](mv) / np.maximum(M["soma"](f2), 1)
                loc.append(float(np.mean(movidos_m[flag] > 0.01)) if len(flag) else np.nan)
                for det in DETECTORES:
                    vals[det].append(d[det])
                    lo, hi = lim[det]
                    alarmes[det] += int(d[det] < lo or d[det] > hi)
            for det in DETECTORES:
                linhas.append({"cenario": cen, "k": k, "detector": det, "poder": alarmes[det] / N_ALT,
                               "media": float(np.mean(vals[det])), "real": real[det],
                               "nulo_lo": float(lim[det][0]), "nulo_hi": float(lim[det][1])})
            linhas.append({"cenario": cen, "k": k, "detector": "localizacao_fdr", "poder": float(np.nanmean(loc)) if not np.all(np.isnan(loc)) else None,
                           "media": None, "real": None, "nulo_lo": None, "nulo_hi": None})
            print(cen, k, {d: alarmes[d] / N_ALT for d in DETECTORES}, f"{time.time() - t0:.0f}s", flush=True)

    poder = pl.DataFrame(linhas)
    # margem: deslocamento na fatia de Lula entre finalistas correspondente a k
    k_virada = float((A["l2"].sum() - A["f2"].sum()) / 2 / total_f)
    salvar_json("cap05-poder", {
        "meta": meta("Curvas de poder dos detectores",
                     "poder = fração de 20 réplicas manipuladas em que o detector sai do intervalo central de 95% de 80 réplicas sem manipulação (detector 'oráculo'). k = fração dos votos nacionais de Flávio transferida a Lula."),
        "cenarios": NOMES_CEN, "detectores": DETECTORES, "k_virada": k_virada,
        "dados": poder.with_columns(pl.col(pl.Float64).round(5)).to_dicts()})

    ass = assinaturas(A)
    # efeito de cada k uniforme sobre a retenção estimada de Flávio (S1): ret' = ret·(1−k)
    salvar_json("cap05-assinaturas", {"meta": meta("Assinaturas de uma transferência uniforme, nos dados reais",
                                                   "eco_*: taxas de transição estimadas por regressão ecológica não negativa (origens: Lula, Flávio/Bolsonaro, eliminados, brancos+nulos, abstenção do 1º turno → destino). excesso: % de seções em que o ganho do candidato supera eliminados + brancos/nulos + aumento de comparecimento."),
                                      **{k: v for k, v in ass.items() if k != "excesso"}, "dados": ass["excesso"]})

    sim = amostra_simulador(s, A, M, rng)
    resumo = {"real": real, "nulo_limites": {k: [float(a), float(b)] for k, (a, b) in lim.items()},
              "k_virada": k_virada, "sd22": sd22, "assinaturas": ass, "simulador": sim}
    (ACHADOS / "05-poder-detectores.numeros.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1, default=str))
    pl.Config.set_tbl_rows(400)
    print(poder.pivot(on="cenario", index=["detector", "k"], values="poder"))
    print(json.dumps(ass, indent=1, default=str))
    print(f"total {time.time() - t0:.0f}s")


def amostra_simulador(s: pl.DataFrame, A, M, rng) -> dict:
    """Dados compactos para o simulador do navegador.
    - municípios (5.570): estoques do 1º turno, votos do 2º, votos de Flávio em urnas UE2020 e em seções tardias,
      covariáveis já prontas (a regressão com covariáveis do 1º turno roda no navegador);
    - amostra estratificada de 30.000 seções (por região), para os detectores de seção."""
    nm = M["nm"]
    soma = M["soma"]
    f2 = A["f2"].astype(float)
    mun = {
        "l1": soma(A["l1"]), "f1": soma(A["f1"]), "o1": soma(A["o1"]), "i1": soma(A["i1"]),
        "c1": soma(A["c1"]), "a1": soma(A["a1"]), "l2": soma(A["l2"]), "f2": soma(A["f2"]),
        "f2_ue2020": soma(f2 * A["ue2020"]), "f2_tardia": soma(f2 * A["tardia"]),
        "f2q": soma(f2 * f2 / np.maximum(A["l2"] + A["f2"], 1)),  # Σ F·sF (para o cenário proporcional)
    }
    X = M["X"]
    m22 = municipios_2022().filter(pl.col("sg_uf") != "ZZ")
    y22 = (m22["bolsonaro_2"] / (m22["bolsonaro_2"] + m22["lula_2"]) - m22["bolsonaro_1"] / (m22["bolsonaro_1"] + m22["lula_1"])).to_numpy()
    salvar_json("cap05-municipios", {
        "meta": meta("Municípios para o simulador 'simule uma alteração'",
                     "Colunas em listas paralelas (formato colunar para reduzir o tamanho). X = covariáveis do 1º turno da regressão. dados = resumo nacional."),
        "colunas": {k: v.astype(int).tolist() for k, v in mun.items()},
        "X": np.round(X, 5).tolist(), "sd22": float(np.std(y22)),
        "hist22": np.histogram(np.clip(y22, -0.12, 0.06), bins=72, range=(-0.12, 0.06))[0].tolist(),
        "dados": [{"municipios": nm, "lula_2": int(mun["l2"].sum()), "flavio_2": int(mun["f2"].sum())}]})
    # amostra estratificada de seções (proporcional por região, 30 mil)
    n = len(A["l1"])
    idx = np.sort(rng.choice(n, 30000, replace=False))
    sec = {k: A[k][idx].astype(int).tolist() for k in ("l1", "f1", "o1", "i1", "c1", "a1", "l2", "f2", "c2", "a2")}
    sec["ue2020"] = A["ue2020"][idx].astype(int).tolist()
    sec["tardia"] = A["tardia"][idx].astype(int).tolist()
    sec["mun"] = A["mun"][idx].astype(int).tolist()
    salvar_json("cap05-secoes", {
        "meta": meta("Amostra aleatória de 30.000 seções para o simulador", "Colunas paralelas. mun = índice do município em cap05-municipios."),
        "colunas": sec, "dados": [{"secoes_amostra": 30000, "secoes_total": int(n)}]})
    return {"municipios": nm, "secoes_amostra": 30000}


def meta(titulo: str, descricao: str) -> dict:
    return {"titulo": titulo, "fonte": FONTE, "descricao": descricao, "gerado_em": HOJE, "script": SCRIPT}


if __name__ == "__main__":
    if "--so-assinaturas" in sys.argv:
        so_assinaturas()
    else:
        main()
