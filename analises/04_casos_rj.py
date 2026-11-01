"""Capítulo 04 — Região dos Lagos e Silva Jardim: os casos do RJ .

O que este script faz (tudo a partir dos boletins de urna oficiais, por seção):
  1. Recalcula Δ Lula / Δ Flávio dos nove municípios citados e confere com as alegações; refaz a identidade
     comparecimento = nominais + brancos + nulos.
  2. Situa os nove casos na distribuição nacional (5.571 municípios), sem e com controles:
       - percentis brutos (nacional e dentro do RJ);
       - comparação com 50 "gêmeos" (vizinhos mais próximos em porte, fatia de Flávio no 1º turno,
         peso e composição dos eliminados, brancos/nulos e comparecimento do 1º turno);
       - regressão com covariáveis do 1º turno (coeficientes ajustados ao 2º), previsão fora da amostra (10 dobras),
         resíduo padronizado com variância dependente do porte e FDR (Benjamini–Hochberg) nos 5.571.
  3. Visão espacial: o conjunto dos nove (e a Região Imediata de Cabo Frio) é anômalo como aglomerado?
     Nulo: todos os aglomerados de 9 vizinhos mais próximos do país, e todas as Regiões Imediatas do IBGE.
  4. Nível de seção: Silva Jardim (61 seções) e os demais — o +1 de Flávio é uniforme ou compensação?
     Cruzamento com o resumo dos logs (modelo de urna, alertas, erros, biometria, encerramento).
  5. Monte Carlo de Silva Jardim: multinomial explícito com os parâmetros das alegações, análise de
     sensibilidade e versão com matriz de transição estimada no restante do RJ.

Rodar: uv run python analises/04_casos_rj.py
"""

from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
from scipy import optimize, stats
from scipy.special import logsumexp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import ACHADOS, ROOT, municipios_2026, salvar_json, secoes_2026  # noqa: E402

SCRIPT = "analises/04_casos_rj.py"
HOJE = date.today().isoformat()
FONTE = "TSE — boletins de urna por seção, 1º e 2º turnos de 2026; cálculo próprio"
EXT = ROOT / "data" / "raw" / "externo"
RNG = np.random.default_rng(20261025)

CASOS = {  # código IBGE -> rótulo
    "3301009": "Campos dos Goytacazes", "3300209": "Araruama", "3300233": "Armação dos Búzios",
    "3300258": "Arraial do Cabo", "3300704": "Cabo Frio", "3301876": "Iguaba Grande",
    "3305208": "São Pedro da Aldeia", "3305505": "Saquarema", "3305604": "Silva Jardim",
}
ALEGACOES = {  # tabela das alegações: (ΔL, ΔF, oscilação de F entre finalistas em p.p.)
    "3301009": (24822, -1389, -5.937), "3300209": (5581, 11, -4.699), "3300233": (1981, 74, -4.782),
    "3300258": (1450, 163, -3.367), "3300704": (9169, 342, -4.586), "3301876": (1443, 184, -3.966),
    "3305208": (3604, 433, -4.404), "3305505": (5396, 269, -5.152), "3305604": (984, 1, -4.569),
}
SJ = "3305604"


def baixar(url: str, nome: str) -> Path:
    EXT.mkdir(parents=True, exist_ok=True)
    p = EXT / nome
    if not p.exists():
        with urllib.request.urlopen(url, timeout=120) as r:
            corpo = r.read()
        if corpo[:2] == b"\x1f\x8b":  # a API do IBGE responde gzip
            corpo = gzip.decompress(corpo)
        p.write_bytes(corpo)
    return p


def geografia() -> pl.DataFrame:
    """Coordenadas (kelvins/municipios-brasileiros) + Região Imediata e Microrregião (API de localidades do IBGE)."""
    ibge = json.loads(baixar("https://servicodados.ibge.gov.br/api/v1/localidades/municipios", "ibge_municipios.json")
                      .read_text())
    reg = pl.DataFrame([{
        "cd_municipio_ibge": str(m["id"]),
        "regiao_imediata": (m.get("regiao-imediata") or {}).get("nome"),
        "id_regiao_imediata": (m.get("regiao-imediata") or {}).get("id"),
        "microrregiao": (m.get("microrregiao") or {}).get("nome"),
        "id_microrregiao": (m.get("microrregiao") or {}).get("id"),
    } for m in ibge])
    coords = pl.read_csv(baixar("https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv",
                                "municipios_coordenadas.csv")).select(
        pl.col("codigo_ibge").cast(pl.Utf8).alias("cd_municipio_ibge"), "latitude", "longitude")
    return reg.join(coords, on="cd_municipio_ibge", how="full", coalesce=True)


# ---------------------------------------------------------------- utilidades estatísticas
def bh(p: np.ndarray) -> np.ndarray:
    """q-valores de Benjamini–Hochberg."""
    n = len(p)
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(q, 1)
    return out


def ols(X: np.ndarray, y: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    if w is None:
        return np.linalg.lstsq(X, y, rcond=None)[0]
    sw = np.sqrt(w)
    return np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]


def previsao_fora_amostra(X: np.ndarray, y: np.ndarray, w: np.ndarray, k: int = 10, semente: int = 7) -> np.ndarray:
    idx = np.random.default_rng(semente).permutation(len(y))
    pred = np.empty(len(y))
    for dobra in np.array_split(idx, k):
        treino = np.setdiff1d(idx, dobra)
        b = ols(X[treino], y[treino], w[treino])
        pred[dobra] = X[dobra] @ b
    return pred


def residuo_padronizado(r: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Variância do resíduo modelada como a + b/n (parte municipal + parte amostral), ajustada por MQ robusto."""
    def perda(par):
        a, b = np.exp(par)
        v = a + b / n
        return np.sum(np.log(v) + r ** 2 / v)  # verossimilhança normal

    res = optimize.minimize(perda, x0=np.log([np.var(r) / 2, np.var(r) * np.median(n) / 2]), method="Nelder-Mead")
    a, b = np.exp(res.x)
    return r / np.sqrt(a + b / n)


def percentil(v: np.ndarray, x: float) -> float:
    """Percentil (0–100) de x em v (proporção de v ≤ x)."""
    return float(np.mean(v <= x) * 100)


# ---------------------------------------------------------------- 1. recálculo
def recalculo(m: pl.DataFrame) -> pl.DataFrame:
    r = (m.filter(pl.col("cd_municipio_ibge").is_in(list(CASOS)))
         .with_columns(
             (pl.col("lula_2") - pl.col("lula_1")).alias("dl"),
             (pl.col("flavio_2") - pl.col("flavio_1")).alias("df"),
             (pl.col("comp_2") - pl.col("validos_2") - pl.col("brancos_2") - pl.col("nulos_2")).alias("residuo_r2"),
             (pl.col("comp_1") - pl.col("validos_1") - pl.col("brancos_1") - pl.col("nulos_1")).alias("residuo_r1"),
         ))
    linhas = []
    for d in r.iter_rows(named=True):
        dl, dfl, osc = ALEGACOES[d["cd_municipio_ibge"]]
        sf1 = d["flavio_1"] / (d["flavio_1"] + d["lula_1"])
        sf2 = d["flavio_2"] / (d["flavio_2"] + d["lula_2"])
        linhas.append({
            "codigo_ibge": d["cd_municipio_ibge"], "municipio": CASOS[d["cd_municipio_ibge"]],
            "secoes": d["n_secoes"], "lula_1": d["lula_1"], "flavio_1": d["flavio_1"], "eliminados_1": d["outros_1"],
            "lula_2": d["lula_2"], "flavio_2": d["flavio_2"], "delta_lula": d["dl"], "delta_flavio": d["df"],
            "delta_lula_alegacao": dl, "delta_flavio_alegacao": dfl, "confere": d["dl"] == dl and d["df"] == dfl,
            "osc_flavio_finalistas": sf2 - sf1, "osc_alegacao": osc / 100,
            "delta_comp": d["comp_2"] - d["comp_1"],
            "delta_invalidos": (d["brancos_2"] + d["nulos_2"]) - (d["brancos_1"] + d["nulos_1"]),
            "residuo_r_2t": d["residuo_r2"], "residuo_r_1t": d["residuo_r1"],
        })
    return pl.DataFrame(linhas).sort("delta_lula", descending=True)


# ---------------------------------------------------------------- 2. contexto nacional
def base_municipal(m: pl.DataFrame, geo: pl.DataFrame) -> pl.DataFrame:
    d = (m.filter(pl.col("sg_uf") != "ZZ")
         .with_columns(
             (pl.col("flavio_1") / (pl.col("flavio_1") + pl.col("lula_1"))).alias("sf1"),
             (pl.col("flavio_2") / (pl.col("flavio_2") + pl.col("lula_2"))).alias("sf2"),
             (pl.col("outros_1") / pl.col("validos_1")).alias("o1"),
             ((pl.col("brancos_1") + pl.col("nulos_1")) / pl.col("comp_1")).alias("inv1"),
             (pl.col("comp_1") / pl.col("aptos_1")).alias("turn1"),
             (pl.col("biom_sh_1") / pl.col("comp_1")).alias("biom1"),
             *[(pl.col(f"{c}_1") / pl.col("outros_1").clip(1)).alias(f"c_{c}") for c in ("cury", "renan", "caiado", "zema")],
             pl.col("aptos_1").log().alias("log_aptos"),
             (pl.col("lula_2") - pl.col("lula_1")).alias("dl"),
             (pl.col("flavio_2") - pl.col("flavio_1")).alias("df"),
         )
         .with_columns(
             (pl.col("sf2") - pl.col("sf1")).alias("y"),
             (pl.col("df") / pl.col("comp_1")).alias("df_rel"),
             (pl.col("dl") / pl.col("comp_1")).alias("dl_rel"),
             (pl.col("df") / pl.col("outros_1").clip(1)).alias("df_pool"),
             pl.col("cd_municipio_ibge").is_in(list(CASOS)).alias("caso"),
         )
         .join(geo, on="cd_municipio_ibge", how="left"))
    return d


def desenho(d: pl.DataFrame, fe_uf: bool) -> np.ndarray:
    sf1 = d["sf1"].to_numpy()
    o1 = d["o1"].to_numpy()
    cols = [np.ones(d.height), sf1, sf1 ** 2, sf1 ** 3, o1, o1 ** 2, sf1 * o1,
            d["inv1"].to_numpy(), d["turn1"].to_numpy(), d["biom1"].to_numpy(), d["log_aptos"].to_numpy(),
            d["log_aptos"].to_numpy() ** 2, d["capital"].cast(pl.Float64).to_numpy()]
    cols += [d[f"c_{c}"].to_numpy() * o1 for c in ("cury", "renan", "caiado", "zema")]
    grupos = d["sg_uf"] if fe_uf else d["regiao"]
    for g in sorted(grupos.unique().to_list())[1:]:
        cols.append((grupos == g).cast(pl.Float64).to_numpy())
    return np.column_stack(cols)


def contexto_nacional(d: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    y = d["y"].to_numpy()
    n = (d["lula_2"] + d["flavio_2"]).to_numpy().astype(float)
    out = {}
    for nome, fe in (("reg", False), ("uf", True)):
        X = desenho(d, fe)
        pred = previsao_fora_amostra(X, y, w=np.sqrt(n))
        r = y - pred
        z = residuo_padronizado(r, n)
        p2 = 2 * stats.norm.sf(np.abs(z))
        p1 = stats.norm.cdf(z)  # unilateral: Flávio pior que o previsto (direção "a favor de Lula")
        b = ols(X, y, np.sqrt(n))
        r2 = 1 - np.sum((y - X @ b) ** 2 * np.sqrt(n)) / np.sum((y - np.average(y, weights=np.sqrt(n))) ** 2 * np.sqrt(n))
        out[nome] = dict(pred=pred, z=z, q2=bh(p2), q1=bh(p1), r2=r2, sd_res=float(np.std(r)))
    d = d.with_columns(
        pl.Series("pred_reg", out["reg"]["pred"]), pl.Series("z_reg", out["reg"]["z"]),
        pl.Series("q_reg", out["reg"]["q2"]), pl.Series("q1_reg", out["reg"]["q1"]),
        pl.Series("pred_uf", out["uf"]["pred"]), pl.Series("z_uf", out["uf"]["z"]),
        pl.Series("q_uf", out["uf"]["q2"]), pl.Series("q1_uf", out["uf"]["q1"]),
    )
    meta = {k: {"r2": round(v["r2"], 4), "sd_res_pp": round(v["sd_res"] * 100, 3),
                "n_fdr05": int((v["q2"] < 0.05).sum()),
                "n_fdr05_pro_lula": int(((v["q2"] < 0.05) & (v["z"] < 0)).sum()),
                "n_fdr05_pro_flavio": int(((v["q2"] < 0.05) & (v["z"] > 0)).sum())} for k, v in out.items()}
    return d, meta


def gemeos(d: pl.DataFrame, k: int = 50) -> dict[str, dict]:
    """Percentil de cada caso entre os k municípios mais parecidos no 1º turno (Mahalanobis)."""
    vars_ = ["log_aptos", "sf1", "o1", "inv1", "turn1", "c_cury", "c_renan", "c_caiado", "c_zema"]
    M = d.select(vars_).to_numpy()
    Vi = np.linalg.pinv(np.cov(M.T))
    y = d["y"].to_numpy()
    out = {}
    for i in np.where(d["caso"].to_numpy())[0]:
        dif = M - M[i]
        dist = np.einsum("ij,jk,ik->i", dif, Vi, dif)
        dist[d["caso"].to_numpy()] = np.inf  # gêmeos não incluem os próprios casos
        viz = np.argsort(dist)[:k]
        out[d["cd_municipio_ibge"][int(i)]] = {
            "pct_gemeos": percentil(y[viz], y[i]), "y_gemeos_med": float(np.median(y[viz])),
            "y_gemeos_p05": float(np.quantile(y[viz], 0.05)),
        }
    return out


# ---------------------------------------------------------------- 3. espacial
def aglomerados(d: pl.DataFrame, coluna: str, k: int = 9) -> dict:
    """Para cada município, aglomerado = ele + 8 vizinhos mais próximos. Compara a média de `coluna`
    do conjunto dos 9 casos (e dos aglomerados centrados em cada caso) com todos os aglomerados do país."""
    ok = d["latitude"].is_not_null().to_numpy()
    dd = d.filter(pl.Series(ok))
    lat, lon = np.radians(dd["latitude"].to_numpy()), np.radians(dd["longitude"].to_numpy())
    xyz = np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    v = dd[coluna].to_numpy()
    medias = np.empty(dd.height)
    for i0 in range(0, dd.height, 500):
        bloco = xyz[i0:i0 + 500]
        dist = 2 - 2 * bloco @ xyz.T
        viz = np.argpartition(dist, k, axis=1)[:, :k]
        medias[i0:i0 + 500] = v[viz].mean(axis=1)
    casos = dd["caso"].to_numpy()
    media_casos = float(v[casos].mean())
    centros = {dd["cd_municipio_ibge"][int(i)]: float(medias[i]) for i in np.where(casos)[0]}
    return {
        "media_9_casos": media_casos,
        "percentil_9_casos": percentil(medias, media_casos),
        "n_aglomerados": int(dd.height),
        "n_aglomerados_mais_extremos": int((medias <= media_casos).sum()),
        "centros": {c: {"media": m_, "percentil": percentil(medias, m_)} for c, m_ in centros.items()},
        "distribuicao": medias,
    }


def regioes_imediatas(d: pl.DataFrame, coluna: str, nperm: int = 20000) -> pl.DataFrame:
    """Média de `coluna` por Região Imediata; p de permutação = sorteio de grupos do mesmo tamanho no país."""
    v = d[coluna].to_numpy()
    g = d.group_by("id_regiao_imediata", "regiao_imediata", "sg_uf", maintain_order=True).agg(
        pl.col(coluna).mean().alias("media"), pl.len().alias("n"),
        pl.col("caso").sum().alias("n_casos")).drop_nulls("id_regiao_imediata")
    ps = []
    cache: dict[int, np.ndarray] = {}
    for row in g.iter_rows(named=True):
        n = row["n"]
        if n not in cache:
            amostras = np.array([v[RNG.choice(len(v), n, replace=False)].mean() for _ in range(2000)])
            cache[n] = amostras
        ps.append(float((np.sum(cache[n] <= row["media"]) + 1) / (len(cache[n]) + 1)))
    g = g.with_columns(pl.Series("p_perm", ps))
    return g.with_columns(pl.Series("q_perm", bh(g["p_perm"].to_numpy()))).sort("media")


# ---------------------------------------------------------------- 4. seções
def secoes_rj(s: pl.DataFrame) -> pl.DataFrame:
    return (s.filter((pl.col("sg_uf") == "RJ") & pl.col("pareada"))
            .with_columns(
                (pl.col("lula_2") - pl.col("lula_1")).alias("dl"),
                (pl.col("flavio_2") - pl.col("flavio_1")).alias("df"),
                (pl.col("flavio_1") / (pl.col("flavio_1") + pl.col("lula_1"))).alias("sf1"),
                (pl.col("flavio_2") / (pl.col("flavio_2") + pl.col("lula_2"))).alias("sf2"),
                pl.col("cd_municipio_ibge").is_in(list(CASOS)).alias("caso"),
                (pl.col("encerramento_2").dt.hour().cast(pl.Int32) * 60
                 + pl.col("encerramento_2").dt.minute().cast(pl.Int32)).alias("enc_min"),
                (pl.col("biom_sh_2") / pl.col("comp_2")).alias("biom2"),
                (pl.col("biom_sh_1") / pl.col("comp_1")).alias("biom1"),
            ).with_columns((pl.col("sf2") - pl.col("sf1")).alias("y")))


def analise_secoes(rj: pl.DataFrame) -> dict:
    """Dispersão de ΔF por seção: Silva Jardim e os casos vs. seções do RJ de porte parecido."""
    # dispersão esperada de ΔF dado o porte: desvio-padrão de ΔF em faixas de eleitores (resto do RJ)
    resto = rj.filter(~pl.col("caso"))
    faixas = np.quantile(resto["comp_1"].to_numpy(), np.linspace(0, 1, 11))
    out = {}
    for cod, nome in CASOS.items():
        c = rj.filter(pl.col("cd_municipio_ibge") == cod)
        dfv = c["df"].to_numpy()
        # nulo: sorteio de conjuntos de seções do resto do RJ com mesma distribuição de porte
        bins = np.clip(np.searchsorted(faixas, c["comp_1"].to_numpy()) - 1, 0, 9)
        rb = np.clip(np.searchsorted(faixas, resto["comp_1"].to_numpy()) - 1, 0, 9)
        pool = [resto["df"].to_numpy()[rb == b] for b in range(10)]
        sds, somas = [], []
        for _ in range(2000):
            amostra = np.concatenate([RNG.choice(pool[b], (bins == b).sum()) for b in range(10) if (bins == b).sum()])
            sds.append(amostra.std())
        out[cod] = {
            "municipio": nome, "secoes": c.height, "df_total": int(dfv.sum()), "dl_total": int(c["dl"].sum()),
            "secoes_df_pos": int((dfv > 0).sum()), "secoes_df_neg": int((dfv < 0).sum()), "secoes_df_zero": int((dfv == 0).sum()),
            "soma_df_pos": int(dfv[dfv > 0].sum()), "soma_df_neg": int(dfv[dfv < 0].sum()),
            "sd_df": float(dfv.std()), "sd_df_nulo_med": float(np.median(sds)),
            "pct_sd_nulo": percentil(np.array(sds), dfv.std()),
            "secoes_dl_neg": int((c["dl"].to_numpy() < 0).sum()),
            "pct_secoes_dl_neg_resto_rj": float((resto["dl"].to_numpy() < 0).mean()),
            # ΔF acompanha a variação de comparecimento da seção? (rotatividade de eleitores)
            "corr_df_dcomp": float(np.corrcoef(dfv, (c["comp_2"] - c["comp_1"]).to_numpy())[0, 1]),
            "corr_df_dcomp_resto_rj": float(np.corrcoef(resto["df"].to_numpy(), (resto["comp_2"] - resto["comp_1"]).to_numpy())[0, 1]),
            "sd_df_sem_comp": float(np.std(dfv - np.polyval(np.polyfit((c["comp_2"] - c["comp_1"]).to_numpy(), dfv, 1),
                                                            (c["comp_2"] - c["comp_1"]).to_numpy()))),
            "pct_secoes_df_neg_resto_rj": float((resto["df"].to_numpy() < 0).mean()),
        }
    return out


def logs_comparacao(s: pl.DataFrame, rj: pl.DataFrame) -> pl.DataFrame:
    def resumo(df: pl.DataFrame, grupo: str) -> dict:
        return {
            "grupo": grupo, "secoes": df.height,
            "pct_ue2020_2022": float(df["modelo_urna"].is_in(["UE2020", "UE2022"]).mean()),
            "pct_ue2013_2015": float(df["modelo_urna"].is_in(["UE2013", "UE2015"]).mean()),
            "alertas_med": float(df["n_alertas"].mean()), "erros_med": float(df["n_erros"].mean()),
            "pct_secoes_com_erro": float((df["n_erros"] > 0).mean()),
            "biom_sh_1": float(df["biom_sh_1"].sum() / df["comp_1"].sum()),
            "biom_sh_2": float(df["biom_sh_2"].sum() / df["comp_2"].sum()),
            "pct_enc_pos_1705": float((df["enc_min"] >= 17 * 60 + 5).mean()),
            "votos_log_menos_comp": int((df["n_votos_log"] - df["comp_2"]).sum()),
        }
    nac = s.filter(pl.col("pareada")).with_columns(
        (pl.col("encerramento_2").dt.hour().cast(pl.Int32) * 60 + pl.col("encerramento_2").dt.minute().cast(pl.Int32)).alias("enc_min"))
    linhas = [resumo(rj.filter(pl.col("cd_municipio_ibge") == SJ), "Silva Jardim"),
              resumo(rj.filter(pl.col("caso")), "9 casos (todos)"),
              resumo(rj.filter(~pl.col("caso")), "Resto do RJ"),
              resumo(nac, "Brasil")]
    return pl.DataFrame(linhas)


def logs_regressao(rj: pl.DataFrame) -> list[dict]:
    """Dentro do RJ: as características da urna/log explicam y (oscilação de F) da seção, além do município?"""
    d = rj.drop_nulls(["modelo_urna", "n_alertas", "enc_min", "y"]).filter(pl.col("comp_2") >= 30)
    y = d["y"].to_numpy()
    # remove média por município (efeito fixo) e controla sf1
    mun = d["cd_municipio_ibge"].to_numpy()
    _, inv = np.unique(mun, return_inverse=True)

    def demean(x):
        m = np.bincount(inv, weights=x) / np.bincount(inv)
        return x - m[inv]

    feats = {
        "UE2020/2022 (vs 2013/2015)": d["modelo_urna"].is_in(["UE2020", "UE2022"]).cast(pl.Float64).to_numpy(),
        "alertas no log (por 10)": d["n_alertas"].to_numpy() / 10,
        "erros no log (algum)": (d["n_erros"].to_numpy() > 0).astype(float),
        "sem biometria, 2º turno (p.p.)": d["biom2"].to_numpy() * 100,
        "encerrou após 17h05": (d["enc_min"].to_numpy() >= 17 * 60 + 5).astype(float),
    }
    X = np.column_stack([demean(d["sf1"].to_numpy())] + [demean(v) for v in feats.values()])
    yd = demean(y)
    b = np.linalg.lstsq(X, yd, rcond=None)[0]
    r = yd - X @ b
    # erro-padrão agrupado por município
    XtX_inv = np.linalg.inv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(inv):
        sc = X[inv == g].T @ r[inv == g]
        meat += np.outer(sc, sc)
    se = np.sqrt(np.diag(XtX_inv @ meat @ XtX_inv))
    return [{"variavel": k, "coef_pp": float(b[i + 1] * 100), "ep_pp": float(se[i + 1] * 100),
             "p": float(2 * stats.norm.sf(abs(b[i + 1] / se[i + 1])))} for i, k in enumerate(feats)]


# ---------------------------------------------------------------- 5. Monte Carlo
ORIGENS = ["lula", "flavio", "eliminados", "invalidos", "ausentes"]
DESTINOS = ["lula", "flavio", "invalidos", "ausentes"]


def estoques_sj(m: pl.DataFrame) -> dict:
    r = m.filter(pl.col("cd_municipio_ibge") == SJ).row(0, named=True)
    return {
        "n1": np.array([r["lula_1"], r["flavio_1"], r["outros_1"], r["brancos_1"] + r["nulos_1"], r["aptos_1"] - r["comp_1"]]),
        "aptos_2": r["aptos_2"], "lula_2": r["lula_2"], "flavio_2": r["flavio_2"], "validos_2": r["validos_2"],
    }


def matriz_alegacao(ret_f=0.94, ret_l=0.95, elim_f=0.43, elim_l=0.37, ativ_inv=0.55, ativ_aus=0.18, troca=0.5):
    """Matriz de transição no espírito do cenário-base das alegações (Quaest). `troca` = fração das perdas de cada
    finalista que vai direto ao adversário (resto: metade inválido, metade abstenção)."""
    def linha_finalista(ret, para_adv_idx):
        perda = 1 - ret
        lin = np.zeros(4)
        lin[para_adv_idx] = perda * troca
        lin[2] = perda * (1 - troca) / 2
        lin[3] = perda * (1 - troca) / 2
        return lin
    L = linha_finalista(ret_l, 1); L[0] = ret_l
    F = linha_finalista(ret_f, 0); F[1] = ret_f
    resto_e = 1 - elim_f - elim_l
    E = np.array([elim_l, elim_f, resto_e * 0.6, resto_e * 0.4])
    # reativados: dividem-se 40% L / 36% F entre os que escolhem (Quaest, ausentes/inválidos)
    sl, sf = 0.40 / 0.76, 0.36 / 0.76
    INV = np.array([ativ_inv * sl, ativ_inv * sf, (1 - ativ_inv) * 0.85, (1 - ativ_inv) * 0.15])
    AUS = np.array([ativ_aus * sl, ativ_aus * sf, 0.01, 1 - ativ_aus - 0.01])
    return np.vstack([L, F, E, INV, AUS])


def simular(n1: np.ndarray, P: np.ndarray, conc: np.ndarray | None, nsim: int, rng) -> np.ndarray:
    """Sorteio multinomial explícito eleitor-a-eleitor (por grupo de origem). Com `conc`, cada linha da matriz é
    sorteada de uma Dirichlet(conc·P) — variação municipal dos fluxos (incerteza de parâmetro)."""
    tot = np.zeros((nsim, 4))
    for g in range(5):
        if conc is None:
            pv = np.broadcast_to(P[g], (nsim, 4))
        else:
            pv = rng.dirichlet(np.maximum(P[g] * conc[g], 1e-3), size=nsim)
        tot += rng.multinomial(int(n1[g]), pv)
    return tot


def _inclinar(pl_: float, pf_: float, theta: float, phi: float) -> tuple[float, float]:
    """(P(válido), P(Flávio | válido)) depois da inclinação exponencial e^{θV + φF} sobre um eleitor com
    probabilidades pL, pF e 1 − pL − pF de não votar validamente nos finalistas."""
    a, b = pl_ * np.exp(theta), pf_ * np.exp(theta + phi)
    z = a + b + (1 - pl_ - pf_)
    return (a + b) / z, (b / (a + b) if a + b > 0 else 0.0)


def conjunta_vf(n1: np.ndarray, P: np.ndarray, theta: float = 0.0, phi: float = 0.0) -> tuple[np.ndarray, int, int]:
    """Distribuição conjunta exata de (V, F) = (válidos nos finalistas, votos de Flávio) sob a matriz fixa P:
    por grupo, V_g ~ Bin(n_g, pL+pF) e F_g | V_g ~ Bin(V_g, pF/(pL+pF)); os grupos são convoluídos.
    Cada grupo é truncado em ±12 desvios (massa desprezada < 1e-30). Devolve (pmf[v, f], v0, f0).
    Com `theta`/`phi`, devolve a distribuição inclinada por e^{θV + φF}, que desloca a massa para perto do ponto
    de interesse, onde a FFT não perde precisão (a lei original se recupera multiplicando por e^{−θv − φf})."""
    from scipy import signal
    pmf, v0, f0 = np.ones((1, 1)), 0, 0
    for g in range(5):
        n = int(n1[g])
        pv, pf = _inclinar(P[g, 0], P[g, 1], theta, phi)
        mv, sv = n * pv, np.sqrt(n * pv * (1 - pv))
        vs = np.arange(max(0, int(mv - 12 * sv - 30)), min(n, int(mv + 12 * sv + 30)) + 1)
        mf, sf = mv * pf, np.sqrt(n * pv * pf * (1 - pv * pf))
        fs = np.arange(max(0, int(mf - 12 * sf - 30)), min(n, int(mf + 12 * sf + 30)) + 1)
        bloco = stats.binom.pmf(vs, n, pv)[:, None] * stats.binom.pmf(fs[None, :], vs[:, None], pf)
        pmf = np.clip(signal.fftconvolve(pmf, bloco), 0, None)
        v0, f0 = v0 + vs[0], f0 + fs[0]
    return pmf / pmf.sum(), v0, f0


def condicional_exato(n1: np.ndarray, P: np.ndarray, v_obs: int, f_obs: int, tau: float | None = None) -> dict:
    """P(Flávio ≤ f_obs | válidos nos finalistas = v_obs), exata sob a matriz fixa. Com `tau`, aplica o mesmo
    deslocamento N(0, tau) na fatia usado na simulação: P = Σ_f p(f | v_obs) · Φ((f_obs + 0,5 − f) / (v_obs·tau)).
    Também devolve o ajuste do total de válidos: média e desvio previstos pelo modelo e o z do observado.

    v_obs pode estar muitos desvios longe da média (10,8 no cenário-base). Ali a massa real (~1e-27) fica abaixo do
    ruído de arredondamento da FFT (~1e-16), e a conta direta devolve lixo (17% numa versão anterior). Por isso cada
    probabilidade é calculada sob a inclinação exponencial e^{θV + φF} que centra a massa no evento medido e depois
    desfeita em escala log. Conferido contra amostragem por importância (800 mil amostras): 5,5e-16 no cenário-base."""
    pmf, v0, f0 = conjunta_vf(n1, P)
    pv = pmf.sum(axis=1)
    vs = v0 + np.arange(len(pv))
    media = float((vs * pv).sum()); dp = float(np.sqrt(((vs - media) ** 2 * pv).sum()))

    def medias(t):  # médias de V e F sob a inclinação e^{θV + φF}
        ev = ef = 0.0
        for g in range(5):
            pv_g, pf_g = _inclinar(P[g, 0], P[g, 1], t[0], t[1])
            ev += n1[g] * pv_g; ef += n1[g] * pv_g * pf_g
        return ev, ef

    def log_m(t):  # log da função geradora: Σ n_g · log(pO + pL·e^θ + pF·e^{θ+φ})
        return float(sum(n1[g] * np.log(1 - P[g, 0] - P[g, 1] + P[g, 0] * np.exp(t[0]) + P[g, 1] * np.exp(t[0] + t[1]))
                         for g in range(5)))

    def log_pontos(t, vmask, fmask):
        """log de Σ P(V = v, F = f) na região pedida, a partir da lei inclinada por t: P = M(t)·e^{−θv−φf}·p_t."""
        pmf_t, v0_t, f0_t = conjunta_vf(n1, P, *t)
        vs_t, fs_t = v0_t + np.arange(pmf_t.shape[0]), f0_t + np.arange(pmf_t.shape[1])
        sel = vmask(vs_t)[:, None] & fmask(fs_t)[None, :] & (pmf_t > 0)
        vv, ff = np.meshgrid(vs_t, fs_t, indexing="ij")
        return log_m(t) + logsumexp(np.log(pmf_t[sel]) - t[0] * vv[sel] - t[1] * ff[sel])

    # Cada probabilidade usa a inclinação que centra a massa no evento que ela mede:
    # P(V = v_obs) e P(V ≤ v_obs) com θ (V em v_obs); P(V = v_obs, F ≤ f_obs) com (θ, φ) (V em v_obs e F em f_obs).
    t_v = (optimize.brentq(lambda t: medias((t, 0.0))[0] - v_obs, -50, 50), 0.0)
    log_den = log_pontos(t_v, lambda v: v == v_obs, lambda f: np.ones_like(f, bool))
    p_v = float(np.exp(log_pontos(t_v, lambda v: v <= v_obs, lambda f: np.ones_like(f, bool))))
    if tau is None:
        t_vf = tuple(optimize.fsolve(lambda t: np.subtract(medias(t), (v_obs, f_obs)), t_v, xtol=1e-12))
        # φ < 0 empurra F para baixo; se F observado está acima da média condicional, a cauda pedida é o corpo
        t_vf = t_vf if t_vf[1] < 0 else t_v
        p = float(min(np.exp(log_pontos(t_vf, lambda v: v == v_obs, lambda f: f <= f_obs) - log_den), 1.0))
    else:
        # com a dispersão N(0, tau) na fatia, a soma pondera a linha inteira e não depende de uma cauda extrema
        pmf_t, v0_t, f0_t = conjunta_vf(n1, P, *t_v)
        linha = pmf_t[v_obs - v0_t]
        fs = f0_t + np.arange(len(linha))
        p = float((linha / linha.sum() * stats.norm.cdf((f_obs + 0.5 - fs) / (v_obs * tau))).sum())
    return {"p_flavio_le_obs_validos_exato": p, "validos_previstos": media, "validos_dp": dp,
            "validos_z": (v_obs - media) / dp, "p_validos_le_obs": min(p_v, 1.0)}


def monte_carlo(m: pl.DataFrame, rj: pl.DataFrame) -> dict:
    e = estoques_sj(m)
    n1 = e["n1"].copy()
    n1[4] += e["aptos_2"] - n1.sum()  # 3 eleitores novos entram como ausentes (como as alegações)
    sf_obs = e["flavio_2"] / (e["flavio_2"] + e["lula_2"])
    rng = np.random.default_rng(11)

    def resumir(sims, rotulo, **extra):
        F, L, V = sims[:, 1], sims[:, 0], sims[:, 0] + sims[:, 1]
        sf = F / V
        perto = np.abs(V - e["validos_2"]) <= 100  # condicionamento aproximado ao total de válidos (±100)
        return {
            "cenario": rotulo, **extra,
            "p_flavio_le_obs": float(np.mean(F <= e["flavio_2"])),
            "p_flavio_le_obs_cond_validos": float(np.mean(F[perto] <= e["flavio_2"])) if perto.sum() > 200 else None,
            "p_fatia_le_obs": float(np.mean(sf <= sf_obs)),
            "mediana_flavio": float(np.median(F)), "p025_flavio": float(np.quantile(F, 0.025)),
            "p975_flavio": float(np.quantile(F, 0.975)),
            "mediana_fatia_f": float(np.median(sf)),
        }

    cen = []
    conc_base = np.array([130, 80, 50, 50, 50])
    P0 = matriz_alegacao()
    v_obs, f_obs = int(e["validos_2"]), int(e["flavio_2"])
    cen.append(resumir(simular(n1, P0, None, 200000, rng), "Base das alegações, só sorteio multinomial (sem incerteza de parâmetro)",
                       grupo="base", **condicional_exato(n1, P0, v_obs, f_obs)))
    # regressão numérica: valores estáveis do cenário-base (o método antigo, por FFT direta, dava 17%)
    assert 5.3e-16 < cen[-1]["p_flavio_le_obs_validos_exato"] < 5.7e-16, cen[-1]["p_flavio_le_obs_validos_exato"]
    assert 3.1e-27 < cen[-1]["p_validos_le_obs"] < 3.3e-27, cen[-1]["p_validos_le_obs"]
    cen.append(resumir(simular(n1, P0, conc_base, 200000, rng), "Base das alegações + variação municipal (Dirichlet 130/80/50)",
                       grupo="base"))
    for ef in (0.2, 0.3, 0.5, 0.644, 0.7):  # entre os eliminados que escolhem um finalista (80% no cenário-base)
        cen.append(resumir(simular(n1, matriz_alegacao(elim_f=0.8 * ef, elim_l=0.8 * (1 - ef)), conc_base, 100000, rng),
                           f"Eliminados: {ef * 100:.1f}% para Flávio entre os que escolhem".replace(".0%", "%").replace(".", ","),
                           grupo="eliminados", elim_f=ef))
    for rf in (0.90, 0.92, 0.94, 0.96, 0.98):
        cen.append(resumir(simular(n1, matriz_alegacao(ret_f=rf), conc_base, 100000, rng),
                           f"Retenção de Flávio {round(rf * 100)}% (resto igual)", grupo="retencao", ret_f=rf))
    for k in (20, 50, 80, 200, 1000):
        cen.append(resumir(simular(n1, P0, np.full(5, k), 100000, rng),
                           f"Concentração Dirichlet {k} (todas as linhas)", grupo="dispersao", conc=k))

    # ---- versão orientada por dados: matriz estimada no restante do RJ (regressão ecológica por seção, NNLS)
    resto = rj.filter(~pl.col("caso"))
    X = np.column_stack([resto["lula_1"], resto["flavio_1"], resto["outros_1"],
                         resto["brancos_1"] + resto["nulos_1"], resto["aptos_1"] - resto["comp_1"]]).astype(float)
    Y = np.column_stack([resto["lula_2"], resto["flavio_2"], resto["brancos_2"] + resto["nulos_2"],
                         resto["aptos_2"] - resto["comp_2"]]).astype(float)
    B = np.column_stack([optimize.nnls(X, Y[:, j])[0] for j in range(4)])
    Pd = B / B.sum(axis=1, keepdims=True)
    # sobredispersão municipal empírica: aplica a matriz a cada município do RJ (fora os casos) e mede o
    # desvio da fatia de F entre finalistas além do sorteio multinomial
    mr = m.filter((pl.col("sg_uf") == "RJ"))
    Xm = np.column_stack([mr["lula_1"], mr["flavio_1"], mr["outros_1"], mr["brancos_1"] + mr["nulos_1"],
                          mr["aptos_1"] - mr["comp_1"]]).astype(float)
    prev = Xm @ Pd
    sf_prev = prev[:, 1] / (prev[:, 0] + prev[:, 1])
    sf_obs_m = (mr["flavio_2"] / (mr["flavio_2"] + mr["lula_2"])).to_numpy()
    nfin = (mr["flavio_2"] + mr["lula_2"]).to_numpy()
    res = sf_obs_m - sf_prev
    caso_m = mr["cd_municipio_ibge"].is_in(list(CASOS)).to_numpy()
    var_binom = sf_prev * (1 - sf_prev) / nfin
    tau2 = max(np.mean(res[~caso_m] ** 2 - var_binom[~caso_m]), 0)
    zm = res / np.sqrt(tau2 + var_binom)
    p_m = stats.norm.cdf(zm)
    i_sj = int(np.where(mr["cd_municipio_ibge"].to_numpy() == SJ)[0][0])
    rj_rank = pl.DataFrame({"municipio": mr["nm_municipio"], "codigo_ibge": mr["cd_municipio_ibge"],
                            "fatia_f_prev": sf_prev, "fatia_f_obs": sf_obs_m, "residuo": res, "z": zm,
                            "p_unilateral": p_m, "caso": caso_m}).sort("z")
    # simulação explícita com a matriz dos dados: só multinomial e com a sobredispersão municipal
    tau = np.sqrt(tau2)
    sims_d = simular(n1, Pd, None, 200000, rng)
    cen.append(resumir(sims_d, "Matriz estimada no resto do RJ, só sorteio multinomial", grupo="dados",
                       **condicional_exato(n1, Pd, v_obs, f_obs)))
    # sobredispersão: desloca a fatia de F por N(0, tau) em cada sorteio (variação municipal observada no RJ)
    V = sims_d[:, 0] + sims_d[:, 1]
    sf_d = sims_d[:, 1] / V + rng.normal(0, tau, len(V))
    Fd = np.round(sf_d * V)
    sims_d2 = sims_d.copy(); sims_d2[:, 1] = Fd; sims_d2[:, 0] = V - Fd
    cen.append(resumir(sims_d2, "Matriz estimada no resto do RJ + variação municipal observada no RJ", grupo="dados",
                       **condicional_exato(n1, Pd, v_obs, f_obs, tau)))

    return {
        "cenarios": cen, "sf_obs": sf_obs, "n1": n1.tolist(),
        "matriz_alegacao": P0.round(4).tolist(), "matriz_dados": Pd.round(4).tolist(),
        "tau_pp": tau * 100, "rj_rank": rj_rank,
        "sj_z_dados": float(zm[i_sj]), "sj_p_dados": float(p_m[i_sj]),
        "sj_rank_rj": int((zm <= zm[i_sj]).sum()), "n_rj": len(zm),
        "q_bh_rj_sj": float(bh(p_m)[i_sj]),
    }


# ---------------------------------------------------------------- main
def main():
    s = secoes_2026()
    m = municipios_2026()
    geo = geografia()

    # 1
    rec = recalculo(m)
    salvar_json("cap04-casos", {"meta": meta("Os nove casos do RJ recalculados", "Δ entre turnos dos nove municípios citados nas alegações, comparado com os números citados em alegações; R = comparecimento − (válidos + brancos + nulos)."), "dados": rec.to_dicts()})

    # 2
    d = base_municipal(m, geo)
    d, meta_reg = contexto_nacional(d)
    gem = gemeos(d)
    nac = {
        "n_municipios": d.height,
        "y_nacional_agregado": float(d["flavio_2"].sum() / (d["flavio_2"].sum() + d["lula_2"].sum())
                                     - d["flavio_1"].sum() / (d["flavio_1"].sum() + d["lula_1"].sum())),
        "y_mediana": float(d["y"].median()),
    }
    rj_mask = (d["sg_uf"] == "RJ").to_numpy()
    yv = d["y"].to_numpy()
    tab = []
    for row in d.filter(pl.col("caso")).iter_rows(named=True):
        c = row["cd_municipio_ibge"]
        tab.append({
            "codigo_ibge": c, "municipio": CASOS[c], "osc_f": row["y"],
            "pct_nacional": percentil(yv, row["y"]), "pct_rj": percentil(yv[rj_mask], row["y"]),
            "df_pool": row["df_pool"], "pct_nac_df_pool": percentil(d["df_pool"].to_numpy(), row["df_pool"]),
            "pct_gemeos": gem[c]["pct_gemeos"], "osc_gemeos_med": gem[c]["y_gemeos_med"],
            "prev_reg": row["pred_reg"], "z_reg": row["z_reg"], "q_reg": row["q_reg"], "q1_reg": row["q1_reg"],
            "prev_uf": row["pred_uf"], "z_uf": row["z_uf"], "q_uf": row["q_uf"], "q1_uf": row["q1_uf"],
            "rank_z_reg": int((d["z_reg"].to_numpy() <= row["z_reg"]).sum()),
        })
    tab = pl.DataFrame(tab).sort("z_reg")
    salvar_json("cap04-contexto", {"meta": meta("Os nove casos na distribuição nacional",
                                                 "osc_f = variação da fatia de Flávio entre os finalistas (fração). Percentis: proporção de municípios com valor ≤ ao do caso (baixo = mais pró-Lula). z = resíduo padronizado fora da amostra; q = FDR (BH) bilateral sobre 5.571 municípios; reg = efeitos de região, uf = efeitos de UF."),
                                    "regressao": meta_reg, "nacional": nac, "dados": tab.to_dicts()})

    # distribuição nacional para o gráfico: histograma de y e z_reg; pontos dos casos
    def hist(v, lo, hi, nb):
        h, e = np.histogram(np.clip(v, lo, hi), bins=nb, range=(lo, hi))
        return [{"x": round(float((e[i] + e[i + 1]) / 2), 5), "n": int(h[i])} for i in range(nb)]
    # efeito de UF: média ponderada do resíduo (modelo sem UF) por estado — o RJ como um todo é atípico?
    uf = (d.with_columns((pl.col("y") - pl.col("pred_reg")).alias("res"), (pl.col("lula_2") + pl.col("flavio_2")).alias("nfin"))
          .group_by("sg_uf").agg(((pl.col("res") * pl.col("nfin")).sum() / pl.col("nfin").sum()).alias("residuo_medio"),
                                 pl.col("z_reg").mean().alias("z_medio"), pl.len().alias("municipios"),
                                 (pl.col("flavio_2").sum() / (pl.col("flavio_2").sum() + pl.col("lula_2").sum())
                                  - pl.col("flavio_1").sum() / (pl.col("flavio_1").sum() + pl.col("lula_1").sum())).alias("osc_f_uf"))
          .sort("residuo_medio"))
    salvar_json("cap04-uf", {"meta": meta("Resíduo médio por UF (modelo sem efeito de UF)", "residuo_medio = observado − previsto da oscilação de Flávio, ponderado por votos nos finalistas; negativo = Flávio caiu mais que o previsto."),
                             "dados": uf.to_dicts()})
    print(uf)
    salvar_json("cap04-distribuicao", {"meta": meta("Distribuição nacional da oscilação de Flávio e do resíduo padronizado",
                                                    "hist_y: oscilação da fatia de Flávio entre finalistas por município (fração); hist_z: resíduo padronizado do modelo com efeitos de região; casos: posição dos nove."),
                                       "hist_y": hist(yv, -0.10, 0.04, 70), "hist_z": hist(d["z_reg"].to_numpy(), -5, 5, 50),
                                       "hist_z_uf": hist(d["z_uf"].to_numpy(), -5, 5, 50),
                                       "dados": [{"municipio": CASOS[r["codigo_ibge"]], "osc_f": r["osc_f"], "z_reg": r["z_reg"], "z_uf": r["z_uf"]} for r in tab.to_dicts()]})

    # dispersão nacional (amostra) sf1 x y
    amostra = d.select("nm_municipio", "sg_uf", "sf1", "y", "aptos_1", "caso", "z_reg")
    amostra = pl.concat([amostra.filter(~pl.col("caso")).sample(3000, seed=3), amostra.filter(pl.col("caso"))])
    salvar_json("cap04-dispersao", {"meta": meta("Fatia de Flávio no 1º turno × oscilação no 2º (municípios)",
                                                 "Amostra de 3.000 municípios + os nove casos. sf1 = fatia de Flávio entre finalistas no 1º turno."),
                                    "dados": amostra.with_columns(pl.col("sf1", "y", "z_reg").round(5)).to_dicts()})

    # top anomalias nacionais (a favor de Lula e de Flávio)
    top = (d.sort("z_reg").head(15).vstack(d.sort("z_reg", descending=True).head(5))
           .select(pl.col("nm_municipio").alias("municipio"), pl.col("sg_uf").alias("uf"), pl.col("aptos_1").alias("aptos"),
                   pl.col("sf1").alias("fatia_f_1t"), pl.col("y").alias("osc_f"), pl.col("pred_reg").alias("prev"),
                   "z_reg", "q_reg", "z_uf", "q_uf", "caso"))
    salvar_json("cap04-top-nacional", {"meta": meta("Municípios mais anômalos do país (regressoras do 1º turno, ajuste fora da amostra)", "15 com maior desvio a favor de Lula e 5 a favor de Flávio."), "dados": top.to_dicts()})

    # 3 espacial
    esp = {}
    for col in ("y", "z_reg", "z_uf"):
        a = aglomerados(d, col)
        dist = a.pop("distribuicao")
        esp[col] = a
        if col == "z_reg":
            esp["hist_aglomerados_z_reg"] = hist(dist, -3, 3, 60)
        if col == "y":
            esp["hist_aglomerados_y"] = hist(dist, -0.08, 0.03, 55)
    ri = regioes_imediatas(d, "z_reg")
    ri_y = regioes_imediatas(d, "y")
    alvo_ri = d.filter(pl.col("cd_municipio_ibge") == "3300704")["id_regiao_imediata"][0]
    esp["regiao_imediata_cabo_frio"] = {
        "z_reg": ri.with_row_index("rank", offset=1).filter(pl.col("id_regiao_imediata") == alvo_ri).to_dicts()[0],
        "y": ri_y.with_row_index("rank", offset=1).filter(pl.col("id_regiao_imediata") == alvo_ri).to_dicts()[0],
        "n_regioes": ri.height, "n_q05_z": int((ri["q_perm"] < 0.05).sum()), "n_q05_y": int((ri_y["q_perm"] < 0.05).sum()),
    }
    for nome_ri in ("Campos dos Goytacazes", "Rio Bonito"):
        x = ri.with_row_index("rank", offset=1).filter((pl.col("regiao_imediata") == nome_ri) & (pl.col("sg_uf") == "RJ"))
        if x.height:
            esp[f"ri_{nome_ri}"] = x.to_dicts()[0]
    salvar_json("cap04-espacial", {"meta": meta("Os casos como aglomerado espacial",
                                                "Para cada município, média de 9 (ele + 8 vizinhos mais próximos). Percentil do conjunto dos nove casos e das Regiões Imediatas."),
                                   **{k: v for k, v in esp.items()},
                                   "dados": ri.head(25).with_columns(pl.col("media", "p_perm", "q_perm").round(5)).to_dicts()})

    # 4 seções
    rj = secoes_rj(s)
    sec = analise_secoes(rj)
    sj = (rj.filter(pl.col("cd_municipio_ibge") == SJ)
          .select("zona", "secao", "local", "comp_1", "comp_2", "lula_1", "lula_2", "flavio_1", "flavio_2", "outros_1",
                  "dl", "df", "modelo_urna", "n_alertas", "n_erros", "biom_sh_2", "enc_min")
          .with_columns(((pl.col("enc_min") // 60).cast(pl.Utf8) + "h" + (pl.col("enc_min") % 60).cast(pl.Utf8).str.zfill(2)).alias("encerramento"))
          .drop("enc_min").sort("df"))
    salvar_json("cap04-silva-jardim-secoes", {"meta": meta("Silva Jardim: as 61 seções", "Δ por seção entre turnos (mesma seção nos dois turnos)."), "dados": sj.to_dicts()})
    loc = (rj.filter(pl.col("cd_municipio_ibge") == SJ).group_by("local")
           .agg(pl.len().alias("secoes"), pl.col("comp_1").sum(), pl.col("dl").sum(), pl.col("df").sum(), pl.col("outros_1").sum(),
                pl.col("flavio_1").sum(), pl.col("lula_1").sum())
           .sort("df"))
    salvar_json("cap04-silva-jardim-locais", {"meta": meta("Silva Jardim por local de votação", "Soma das seções de cada local."), "dados": loc.to_dicts()})
    # strip das seções dos nove casos (df e dl) — para o gráfico
    strip = (rj.filter(pl.col("caso")).select(pl.col("cd_municipio_ibge").replace_strict(CASOS).alias("municipio"),
                                               "dl", "df", "comp_1"))
    salvar_json("cap04-secoes-casos", {"meta": meta("ΔL e ΔF por seção nos nove casos", "Cada ponto é uma seção."), "dados": strip.to_dicts()})
    salvar_json("cap04-secoes-resumo", {"meta": meta("Dispersão de ΔF por seção vs. seções do RJ de mesmo porte", "pct_sd_nulo = percentil do desvio-padrão observado entre 2.000 sorteios de seções do resto do RJ com o mesmo perfil de porte."),
                                        "dados": list(sec.values())})
    lg = logs_comparacao(s, rj)
    lreg = logs_regressao(rj)
    salvar_json("cap04-logs", {"meta": meta("Logs e características das urnas: casos vs. resto", "Seções pareadas, 2º turno."), "regressao_rj": lreg, "dados": lg.to_dicts()})

    # 5 Monte Carlo
    mc = monte_carlo(m, rj)
    rank = mc.pop("rj_rank")
    salvar_json("cap04-monte-carlo", {"meta": meta("Monte Carlo de Silva Jardim: sensibilidade",
                                                    "Três eventos diferentes: p_flavio_le_obs = P(Flávio ≤ 8.933) sem fixar os válidos; p_flavio_le_obs_validos_exato = P(Flávio ≤ 8.933 | válidos = 14.367), exata por convolução (só nos cenários de matriz fixa); p_fatia_le_obs = P(fatia de Flávio entre finalistas ≤ observada), com o total de válidos variando. _cond_validos = aproximação por válidos ±100 do observado. validos_previstos/validos_dp/validos_z = ajuste do modelo ao total de válidos (o observado é 14.367)."),
                                       **{k: v for k, v in mc.items() if k != "cenarios"}, "dados": mc["cenarios"]})
    salvar_json("cap04-rj-matriz", {"meta": meta("Municípios do RJ contra a matriz de transição estimada no próprio RJ", "z negativo = Flávio abaixo do previsto."),
                                    "dados": rank.with_columns(pl.col(pl.Float64).round(5)).to_dicts()})

    resumo = {"recalculo": rec.to_dicts(), "regressao": meta_reg, "nacional": nac, "contexto": tab.to_dicts(),
              "espacial": {k: v for k, v in esp.items() if not k.startswith("hist")}, "secoes": sec,
              "logs": lg.to_dicts(), "logs_reg": lreg, "mc": mc, "top": top.to_dicts()}
    (ACHADOS / "04-casos-rj.numeros.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({k: resumo[k] for k in ("regressao", "nacional")}, indent=1, default=str))
    print(tab)
    print(json.dumps(resumo["espacial"], indent=1, default=str))
    print(json.dumps(sec, indent=1, default=str))
    print(lg)
    print(lreg)
    print(pl.DataFrame(mc["cenarios"]))
    print({k: v for k, v in mc.items() if k != "cenarios"})
    print(rank.head(10))
    print(top)


def meta(titulo: str, descricao: str) -> dict:
    return {"titulo": titulo, "fonte": FONTE, "descricao": descricao, "gerado_em": HOJE, "script": SCRIPT}


if __name__ == "__main__":
    pl.Config.set_tbl_cols(30)
    pl.Config.set_tbl_width_chars(250)
    pl.Config.set_tbl_rows(40)
    main()
