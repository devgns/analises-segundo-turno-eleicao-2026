"""Capítulo 2 — O mapa da virada: deslocamento uniforme entre turnos? (2026 vs 2022)

Alegações: "Lula subiu em 5.378 cidades, Flávio em 184", o Sul, o efeito comum absorvido pelo
intercepto e a tese central de deslocamento nacional quase uniforme.

Testes (definidos antes de olhar os resultados; linha de base = 2022, mesma estrutura de 2 turnos):
  A. Contagens de municípios com 4 métricas, 2026 e 2022.
  B. Distribuição de Δfatia de Lula entre finalistas (municípios e seções): média, DP, IQR, fração com o
     mesmo sinal do país, por região/UF. Pergunta: 2026 é MAIS uniforme que 2022?
  C. Modelo: Δfatia ~ eliminados + Δcomparecimento + Δ(brancos+nulos), cada um interagido com a fatia de
     Lula no 1º turno, + região. O intercepto = deslocamento comum "não explicado" = troca líquida direta
     entre finalistas por eleitor de finalista (ver derivação no achados). Comparado com 2022.
     Também: regressão de Goodman (matriz de transição ecológica) por município e por seção.
  D. Sul por UF.
  E. Mapa coroplético (GeoJSON IBGE simplificado) + explorador de municípios + dispersão.

Rodar: uv run python analises/02_mapa_virada.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import ACHADOS, CAND_2022_T1, CAND_2022_T2, CHAVE, REGIAO, ROOT, SITE_DATA, _nomes_municipios, _padronizar, municipios_2022, municipios_2026, salvar_json, secoes_2026  # noqa: E402,E501

SCRIPT = "analises/02_mapa_virada.py"
HOJE = str(date.today())
FONTE = "TSE — boletins de urna por seção, 1º e 2º turnos de 2026 e 2022"
NUM: dict = {}
(ACHADOS / "dados").mkdir(parents=True, exist_ok=True)
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]


def salvar(nome, titulo, descricao, dados, decimais=5, **extra):
    if isinstance(dados, pl.DataFrame):
        dados = dados.with_columns(pl.col(pl.Float64, pl.Float32).round(decimais)).to_dicts()
    m = {"titulo": titulo, "fonte": FONTE, "descricao": descricao, "gerado_em": HOJE, "script": SCRIPT}
    return salvar_json(f"ch02/{nome}", {"meta": m, "dados": dados, **extra}, decimais=None)


def preparar(m: pl.DataFrame, adv: str) -> pl.DataFrame:
    """Variáveis por unidade (município ou seção). adv = flavio | bolsonaro."""
    L1, L2, A1, A2 = pl.col("lula_1"), pl.col("lula_2"), pl.col(f"{adv}_1"), pl.col(f"{adv}_2")
    fin1 = L1 + A1
    bn1 = pl.col("brancos_1") + pl.col("nulos_1")
    bn2 = pl.col("brancos_2") + pl.col("nulos_2")
    return m.with_columns(
        (L1 / fin1).alias("sh1"), (L2 / (L2 + A2)).alias("sh2"),
        (L2 - L1).alias("dL"), (A2 - A1).alias("dA"),
        (pl.col("outros_1") / fin1).alias("o"),
        ((pl.col("comp_2") - pl.col("comp_1")) / fin1).alias("dc"),
        ((bn1 - bn2) / fin1).alias("dbn"),
        ((L2 - A2) / pl.col("validos_2") - (L1 - A1) / pl.col("validos_1")).alias("dmargem"),
        (pl.col("comp_2") / pl.col("aptos_2") - pl.col("comp_1") / pl.col("aptos_1")).alias("dturnout"),
    ).with_columns((pl.col("sh2") - pl.col("sh1")).alias("dsh"))


def wquant(x, w, qs):
    i = np.argsort(x)
    x, w = x[i], w[i]
    c = np.cumsum(w) / w.sum()
    return [float(np.interp(q, c, x)) for q in qs]


def estat(x: np.ndarray, w: np.ndarray | None = None, sinal: float = 1.0) -> dict:
    if w is None:
        w = np.ones_like(x)
    mu = np.average(x, weights=w)
    sd = np.sqrt(np.average((x - mu) ** 2, weights=w))
    q = wquant(x, w, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {"n": int(len(x)), "media": float(mu), "dp": float(sd), "p05": q[0], "p25": q[1], "mediana": q[2],
            "p75": q[3], "p95": q[4], "iqr": q[3] - q[1],
            "frac_mesmo_sinal": float(np.average(np.sign(x) == np.sign(sinal), weights=w)),
            "dp_sobre_media": float(sd / abs(mu))}


def secoes_2022() -> pl.DataFrame:
    t1 = _padronizar(2022, 1, CAND_2022_T1).drop("local")
    t2 = _padronizar(2022, 2, CAND_2022_T2).drop("local")
    return (t1.join(t2, on=CHAVE, how="inner")
            .join(_nomes_municipios(), on=["sg_uf", "cd_municipio_tse"], how="left")
            .with_columns(pl.col("sg_uf").replace_strict(REGIAO, default=None).alias("regiao")))


# ----------------------------------------------------------------------------------------------
def contagens_p04(m26: pl.DataFrame, m22: pl.DataFrame) -> None:
    linhas = []
    for m, ano in ((m26, 2026), (m22, 2022)):
        adv = "Flávio" if ano == 2026 else "Bolsonaro"
        n = m.height
        r = {
            "Lula ganhou votos nominais": int((m["dL"] > 0).sum()),
            f"{adv} ganhou votos nominais": int((m["dA"] > 0).sum()),
            "Lula perdeu votos nominais": int((m["dL"] < 0).sum()),
            f"{adv} perdeu votos nominais": int((m["dA"] < 0).sum()),
            "Ganho absoluto de Lula > do adversário": int((m["dL"] > m["dA"]).sum()),
            "Ganho absoluto do adversário > de Lula": int((m["dA"] > m["dL"]).sum()),
            "Fatia de Lula entre finalistas subiu": int((m["dsh"] > 0).sum()),
            "Fatia de Lula entre finalistas caiu": int((m["dsh"] < 0).sum()),
            "Margem Lula − adversário sobre válidos melhorou": int((m["dmargem"] > 0).sum()),
            "Margem Lula − adversário sobre válidos piorou": int((m["dmargem"] < 0).sum()),
        }
        for k, v in r.items():
            linhas.append({"ano": ano, "metrica": k, "municipios": v, "fracao": v / n, "total": n})
    salvar("p04-contagens", "Em quantos municípios cada um 'subiu'? Quatro métricas, 2026 e 2022",
           "Municípios brasileiros (sem exterior). O número 5.378 × 184 do relatório que circulou nas redes não é reproduzido "
           "por nenhuma métrica isolada; ver achados.", linhas)
    NUM["p04"] = linhas
    for l in linhas:
        print(l["ano"], l["metrica"], l["municipios"])


def dispersao(m26, m22, s26, s22) -> None:
    out = []
    for nivel, a, b in (("municipio", m26, m22), ("secao", s26, s22)):
        for d, ano, sinal in ((a, 2026, 1.0), (b, 2022, -1.0)):
            x = d["dsh"].to_numpy(); w = (d["lula_1"] + d[[c for c in d.columns if c.endswith("_1") and c[:4] in ("flav", "bols")][0]]).to_numpy().astype(float)
            for pond, ww in (("nao", None), ("sim", w)):
                e = estat(x, ww, sinal)
                out.append({"nivel": nivel, "ano": ano, "ponderado": pond, "grupo": "Brasil", **e})
            for reg in REGIOES:
                f = (d["regiao"] == reg).to_numpy()
                out.append({"nivel": nivel, "ano": ano, "ponderado": "nao", "grupo": reg, **estat(x[f], None, sinal)})
    t = pl.DataFrame(out)
    salvar("dispersao", "Quão uniforme foi o deslocamento? Δfatia de Lula entre finalistas, 2026 vs 2022",
           "Estatísticas da distribuição da variação da fatia de Lula entre os dois finalistas (fração). "
           "frac_mesmo_sinal = fração de unidades que andaram na mesma direção do país "
           "(para Lula em 2026, para Bolsonaro em 2022). Seções com ≥ 50 votos em finalistas.", t)
    NUM["dispersao"] = out
    print(t.filter(pl.col("grupo") == "Brasil"))

    # por UF (municípios), 2026 e 2022
    uf = []
    for d, ano, sinal in ((m26, 2026, 1.0), (m22, 2022, -1.0)):
        for (u,), g in d.group_by(["sg_uf"]):
            e = estat(g["dsh"].to_numpy(), None, sinal)
            uf.append({"ano": ano, "uf": u, "regiao": REGIAO[u], "municipios": e["n"], "media": e["media"],
                       "dp": e["dp"], "iqr": e["iqr"], "frac_mesmo_sinal": e["frac_mesmo_sinal"]})
    uf = pl.DataFrame(uf).sort("ano", "uf", descending=[True, False])
    salvar("dispersao-uf", "Deslocamento por UF (municípios), 2026 e 2022",
           "Média simples, DP e IQR da Δfatia de Lula entre finalistas nos municípios de cada UF.", uf)
    NUM["dispersao_uf"] = uf.to_dicts()

    # histograma comparável: Δ "a favor de quem estava atrás no 1º turno" (2026: +Δ; 2022: −Δ)
    bins = np.round(np.arange(-0.06, 0.1201, 0.0025), 4)
    hist = []
    for d, ano, sinal in ((m26, 2026, 1.0), (m22, 2022, -1.0)):
        x = np.clip(sinal * d["dsh"].to_numpy(), bins[0], bins[-1] - 1e-9)
        h, _ = np.histogram(x, bins=bins)
        for b0, c in zip(bins[:-1], h):
            hist.append({"ano": ano, "faixa": round(float(b0 + 0.00125), 5), "municipios": int(c)})
    salvar("hist-municipios", "Distribuição do deslocamento a favor de quem estava atrás no 1º turno",
           "2026: Δfatia de Lula; 2022: Δfatia de Bolsonaro (= −Δfatia de Lula). Municípios; pontas acumuladas.", hist)


def modelo(d: pl.DataFrame, rotulo: str, regiao_fe: bool = True, peso: str = "fin1") -> dict:
    """WLS do Δfatia de Lula. Erros agrupados: por UF no nível municipal, por município no nível de seção (com
    menos de 20 grupos, como num modelo de uma só região, caímos para HC1 e registramos)."""
    d = d.with_columns((pl.col("sh1") - 0.5).alias("s"))
    X = d.select(
        "o", "dc", "dbn", "s",
        (pl.col("o") * pl.col("s")).alias("o_s"), (pl.col("dc") * pl.col("s")).alias("dc_s"),
        (pl.col("dbn") * pl.col("s")).alias("dbn_s"),
    ).to_pandas()
    w = d[peso].to_numpy().astype(float)
    if regiao_fe:
        # indicadoras de região centralizadas pela participação ponderada (mesmo peso da regressão): o intercepto
        # passa a ser a média dos interceptos regionais ponderada pelos votos dos finalistas no 1º turno.
        regs = d["regiao"].to_numpy()
        for r in REGIOES[1:]:
            ind = (regs == r).astype(float)
            X[f"r_{r}"] = ind - np.average(ind, weights=w)
    X = sm.add_constant(X)
    y = d["dsh"].to_numpy()
    grupos = d["sg_uf"] if "secao" not in d.columns else d["sg_uf"] + "-" + d["cd_municipio_tse"].cast(pl.Utf8)
    codigos = grupos.cast(pl.Categorical).to_physical().to_numpy()
    if len(np.unique(codigos)) >= 20:
        fit = sm.WLS(y, X, weights=w).fit(cov_type="cluster", cov_kwds={"groups": codigos})
        erro = "agrupado por " + ("UF" if "secao" not in d.columns else "município")
    else:
        fit = sm.WLS(y, X, weights=w).fit(cov_type="HC1")
        erro = "HC1 (poucos grupos)"
    resid = y - fit.fittedvalues
    sdw = float(np.sqrt(np.average(resid ** 2, weights=w)))
    ci = fit.conf_int().loc["const"].tolist()
    r = {"modelo": rotulo, "n": int(len(y)), "erro_padrao": erro, "intercepto": float(fit.params["const"]), "ic95_inf": ci[0],
         "ic95_sup": ci[1], "r2": float(fit.rsquared), "dp_residual_pond": sdw,
         "coef": {k: float(v) for k, v in fit.params.items()}}
    return r, resid


def modelos(m26, m22, s26, s22) -> tuple:
    res = []
    resid26 = None
    for nivel, a, b in (("municipio", m26, m22), ("secao", s26, s22)):
        for d, ano in ((a, 2026), (b, 2022)):
            r, resid = modelo(d, f"{nivel} {ano}")
            r["nivel"], r["ano"] = nivel, ano
            res.append(r)
            if nivel == "municipio" and ano == 2026:
                resid26 = resid
            if nivel == "municipio":
                # caudas dos resíduos: casos "atípicos" em 2026 vs 2022 (o deslocamento comum já removido)
                rr = np.asarray(resid)
                sd = float(np.std(rr))
                NUM.setdefault("caudas_residuo", []).append({
                    "ano": ano, "dp": sd,
                    "acima_3dp": int((rr > 3 * sd).sum()), "abaixo_3dp": int((rr < -3 * sd).sum()),
                    "abs_maior_3pp": int((np.abs(rr) > 0.03).sum()),
                    "a_favor_de_lula_maior_3pp": int((rr > 0.03).sum()), "contra_lula_maior_3pp": int((rr < -0.03).sum()),
                })
            r2, _ = modelo(d, f"{nivel} {ano} sem região", regiao_fe=False)
            r2["nivel"], r2["ano"] = nivel, ano
            res.append(r2)
    # interceptos por região (modelo separado por região, municípios)
    for d, ano in ((m26, 2026), (m22, 2022)):
        for reg in REGIOES:
            r, _ = modelo(d.filter(pl.col("regiao") == reg), f"municipio {ano} {reg}", regiao_fe=False)
            r["nivel"], r["ano"], r["regiao"] = "municipio-regiao", ano, reg
            res.append(r)
    for r in res:
        print(f"{r['modelo']:<35} n={r['n']:>7} intercepto={r['intercepto'] * 100:+.3f} p.p. "
              f"[{r['ic95_inf'] * 100:+.3f}, {r['ic95_sup'] * 100:+.3f}] R2={r['r2']:.3f} dp_res={r['dp_residual_pond'] * 100:.3f}")
    NUM["modelos"] = res
    tab = [r | {"regiao": r.get("regiao", "Brasil")} for r in res]
    salvar("modelo-intercepto", "Deslocamento comum não explicado (intercepto), 2026 vs 2022",
           "WLS (peso = votos dos finalistas no 1º turno); erros agrupados por UF (municípios) ou por município (seções), "
           "HC1 nos modelos de uma só região. Variável: Δfatia de Lula entre finalistas. "
           "Controles: eliminados, Δcomparecimento e queda de brancos+nulos (por voto de finalista), cada um "
           "interagido com a fatia de Lula no 1º turno; indicadoras de região centralizadas pelo mesmo peso, de modo que o "
           "intercepto é a média ponderada dos interceptos regionais. O intercepto é o deslocamento previsto num ponto "
           "contrafactual (o=dc=dbn=0, fatia 50%): uma construção do modelo, não um fluxo observado nem um volume de votos.", tab)
    print("caudas", NUM["caudas_residuo"])
    return res, resid26


def goodman(d: pl.DataFrame, adv: str, rotulo: str) -> dict:
    """Regressão de Goodman: votos do 2º turno / aptos ~ grupos do 1º turno / aptos, sem intercepto."""
    E = d["aptos_1"].cast(pl.Float64)
    g = d.select(
        (pl.col("lula_1") / E).alias("L1"), (pl.col(f"{adv}_1") / E).alias("A1"),
        (pl.col("outros_1") / E).alias("O1"), ((pl.col("brancos_1") + pl.col("nulos_1")) / E).alias("BN1"),
        ((pl.col("aptos_1") - pl.col("comp_1")) / E).alias("AB1"),
    ).to_pandas()
    w = E.to_numpy()
    out = {"modelo": rotulo}
    for dest, col in (("lula", "lula_2"), ("adv", f"{adv}_2")):
        y = (d[col] / E).to_numpy()
        f = sm.WLS(y, g, weights=w).fit(cov_type="HC1")
        for k, v in f.params.items():
            out[f"{k}_para_{dest}"] = float(v)
    return out


# ----------------------------------------------------------------------------------------------
def geojson() -> None:
    raw = ROOT / "data" / "raw" / "geo" / "ibge-malha-municipios" / "br_municipios_qualidade_minima.geojson"
    g = json.loads(raw.read_text())
    nomes = {r["cd_municipio_ibge"]: r["nm_municipio"] for r in _nomes_municipios().iter_rows(named=True)}

    def rdp(pts: np.ndarray, eps: float) -> np.ndarray:
        """Douglas-Peucker iterativo (tolerância em graus)."""
        n = len(pts)
        if n < 5:
            return pts
        manter = np.zeros(n, bool)
        manter[0] = manter[-1] = True
        pilha = [(0, n - 1)]
        while pilha:
            i, j = pilha.pop()
            if j <= i + 1:
                continue
            a, b = pts[i], pts[j]
            seg = pts[i + 1:j]
            ab = b - a
            nab = np.hypot(*ab)
            if nab == 0:
                dist = np.hypot(*(seg - a).T)
            else:
                dist = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / nab
            k = int(np.argmax(dist))
            if dist[k] > eps:
                m = i + 1 + k
                manter[m] = True
                pilha += [(i, m), (m, j)]
        return pts[manter]

    def q(ring):
        pts = rdp(np.asarray(ring, float), 0.012)
        out = []
        for x, y in pts:
            p = [round(float(x), 3), round(float(y), 3)]
            if not out or out[-1] != p:
                out.append(p)
        if len(out) >= 3 and out[0] != out[-1]:
            out.append(out[0])
        return out

    feats = []
    for f in g["features"]:
        geom = f["geometry"]
        if geom["type"] == "Polygon":
            coords = [r for r in (q(r) for r in geom["coordinates"]) if len(r) >= 4]
        else:
            coords = [[r for r in (q(r) for r in poly) if len(r) >= 4] for poly in geom["coordinates"]]
            coords = [p for p in coords if p]
        cod = str(f["properties"].get("codarea"))
        feats.append({"type": "Feature", "properties": {"codigo_ibge": cod, "nome": nomes.get(cod, "")},
                      "geometry": {"type": geom["type"], "coordinates": coords}})
    out = SITE_DATA / "geo" / "br-municipios.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":"), ensure_ascii=False))
    NUM["geo"] = {"features": len(feats), "bytes": out.stat().st_size}
    print("geo", NUM["geo"])


def main() -> None:
    m26 = preparar(municipios_2026().filter(pl.col("sg_uf") != "ZZ"), "flavio")
    m22 = preparar(municipios_2022().filter(pl.col("sg_uf") != "ZZ"), "bolsonaro")
    for m in (m26, m22):
        assert m["regiao"].null_count() == 0
    m26 = m26.with_columns((pl.col("lula_1") + pl.col("flavio_1")).alias("fin1"))
    m22 = m22.with_columns((pl.col("lula_1") + pl.col("bolsonaro_1")).alias("fin1"))
    NUM["n_municipios"] = {"2026": m26.height, "2022": m22.height}

    s26 = preparar(secoes_2026().filter(pl.col("pareada") & (pl.col("sg_uf") != "ZZ")), "flavio") \
        .with_columns((pl.col("lula_1") + pl.col("flavio_1")).alias("fin1")) \
        .filter((pl.col("fin1") >= 50) & (pl.col("lula_2") + pl.col("flavio_2") >= 50))
    s22 = preparar(secoes_2022().filter(pl.col("sg_uf") != "ZZ"), "bolsonaro") \
        .with_columns((pl.col("lula_1") + pl.col("bolsonaro_1")).alias("fin1")) \
        .filter((pl.col("fin1") >= 50) & (pl.col("lula_2") + pl.col("bolsonaro_2") >= 50))
    NUM["n_secoes"] = {"2026": s26.height, "2022": s22.height}

    contagens_p04(m26, m22)
    dispersao(m26, m22, s26, s22)
    res, resid26 = modelos(m26, m22, s26, s22)

    gm = [goodman(m26, "flavio", "municipio 2026"), goodman(m22, "bolsonaro", "municipio 2022"),
          goodman(s26, "flavio", "secao 2026"), goodman(s22, "bolsonaro", "secao 2022")]
    for r in gm:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    NUM["goodman"] = gm
    gl = []
    for r in gm:
        nivel, ano = r["modelo"].split()
        for org, rot in (("L1", "Lula 1º t."), ("A1", "Adversário 1º t."), ("O1", "Eliminados"),
                         ("BN1", "Brancos/nulos"), ("AB1", "Abstenção")):
            gl.append({"nivel": nivel, "ano": int(ano), "origem": rot, "para_lula": r[f"{org}_para_lula"],
                       "para_adversario": r[f"{org}_para_adv"]})
    salvar("goodman", "Matriz de transição ecológica (regressão de Goodman)",
           "Fração estimada de cada grupo do 1º turno que votou em Lula / no adversário no 2º. Estimativa "
           "ecológica: supõe taxas constantes no território; pode sair de [0,1]. Não observa indivíduos.", gl, 4)

    # ---------------- Sul
    sul = []
    for m, ano in ((m26, 2026), (m22, 2022)):
        for u in ("PR", "SC", "RS", "Sul"):
            g = m.filter(pl.col("regiao") == "Sul") if u == "Sul" else m.filter(pl.col("sg_uf") == u)
            sul.append({"ano": ano, "uf": u, "municipios": g.height,
                        "lula_ganhou": int((g["dL"] > 0).sum()), "adv_ganhou": int((g["dA"] > 0).sum()),
                        "fatia_lula_subiu": int((g["dsh"] > 0).sum()),
                        "d_lula": int(g["dL"].sum()), "d_adv": int(g["dA"].sum()),
                        "eliminados_1": int(g["outros_1"].sum()),
                        "d_comp": int((g["comp_2"] - g["comp_1"]).sum()),
                        "sh1": float(g["lula_1"].sum() / (g["lula_1"].sum() + g["fin1"].sum() - g["lula_1"].sum())),
                        "sh2": float(g["lula_2"].sum() / (g["lula_2"].sum() + g[[c for c in g.columns if c in ("flavio_2", "bolsonaro_2")][0]].sum())),
                        })
    sul = pl.DataFrame(sul).with_columns((pl.col("sh2") - pl.col("sh1")).alias("dsh"))
    print(sul)
    salvar("sul", "Região Sul por UF: quem ganhou votos entre turnos (2026 e 2022)",
           "Contagens de municípios e somas de votos. Adversário = Flávio (2026) ou Bolsonaro (2022).", sul)
    NUM["sul"] = sul.to_dicts()

    # ---------------- Tabela/explorador + mapa + dispersão
    base22 = m22.select("cd_municipio_ibge", pl.col("dsh").alias("dsh22"))
    exp = (m26.with_columns(pl.Series("resid", resid26))
           .join(base22, on="cd_municipio_ibge", how="left")
           .with_columns(
               (pl.col("dsh").rank("average") / pl.len()).alias("pctl"),
               (pl.col("resid").rank("average") / pl.len()).alias("pctl_resid"),
           ))
    explorador = exp.select(
        pl.col("sg_uf").alias("uf"), pl.col("nm_municipio").alias("municipio"),
        pl.col("cd_municipio_ibge").alias("codigo_ibge"), pl.col("aptos_2").alias("eleitores"),
        pl.col("lula_1").alias("l1"), pl.col("flavio_1").alias("f1"), pl.col("outros_1").alias("o1"),
        pl.col("lula_2").alias("l2"), pl.col("flavio_2").alias("f2"),
        pl.col("dL").alias("d_lula"), pl.col("dA").alias("d_flavio"),
        pl.col("sh1").alias("s1"), pl.col("dsh").alias("d_fatia"), "pctl", pl.col("resid").alias("residuo"),
        pl.col("dsh22").alias("d_fatia_2022"),
    ).sort("uf", "municipio")
    salvar("municipios", "Explorador de municípios: 1º e 2º turnos de 2026",
           "Δfatia = variação da fatia de Lula entre os dois finalistas. pctl = percentil nacional de Δfatia. "
           "residuo = Δfatia não explicada pelo modelo (eliminados, comparecimento, brancos/nulos, região). "
           "d_fatia_2022 = mesma medida em 2022 (Lula × Bolsonaro).", explorador, 4)
    NUM["extremos_resid"] = {
        "maiores": explorador.sort("residuo", descending=True).head(15).to_dicts(),
        "menores": explorador.sort("residuo").head(15).to_dicts(),
    }
    # correlação entre Δ 2026 e Δ 2022 (geografia do deslocamento se repete?)
    j = explorador.drop_nulls("d_fatia_2022")
    NUM["corr_d26_d22"] = float(np.corrcoef(j["d_fatia"], j["d_fatia_2022"])[0, 1])
    NUM["corr_resid_d22"] = float(np.corrcoef(j["residuo"], j["d_fatia_2022"])[0, 1])
    print("corr Δ26×Δ22", NUM["corr_d26_d22"], "corr resid×Δ22", NUM["corr_resid_d22"])
    # RJ / casos das alegações no explorador
    rj = ["CAMPOS DOS GOYTACAZES", "ARARUAMA", "ARMAÇÃO DOS BÚZIOS", "ARRAIAL DO CABO", "CABO FRIO",
          "IGUABA GRANDE", "SÃO PEDRO DA ALDEIA", "SAQUAREMA", "SILVA JARDIM"]
    NUM["rj_casos"] = explorador.join(exp.select(pl.col("cd_municipio_ibge").alias("codigo_ibge"), "pctl_resid"), on="codigo_ibge").filter((pl.col("uf") == "RJ") & pl.col("municipio").is_in(rj)).to_dicts()

    salvar("mapa", "Δfatia de Lula entre finalistas por município, 2026 e 2022",
           "codigo_ibge casa com data/geo/br-municipios.json.",
           exp.select(pl.col("cd_municipio_ibge").alias("codigo_ibge"), pl.col("nm_municipio").alias("municipio"),
                      pl.col("sg_uf").alias("uf"), pl.col("dsh").alias("d26"), pl.col("dsh22").alias("d22")), 4)

    mod = {r["modelo"]: r for r in res}
    disp = {(r["nivel"], r["ano"], r["ponderado"], r["grupo"]): r for r in NUM["dispersao"]}
    kpis = [
        {"rotulo": "Deslocamento comum não explicado, 2026", "valor": mod["municipio 2026"]["intercepto"], "formato": "pp",
         "cor": "lula", "detalhe": "intercepto do modelo municipal (a favor de Lula)"},
        {"rotulo": "O mesmo intercepto em 2022", "valor": mod["municipio 2022"]["intercepto"], "formato": "pp",
         "cor": "flavio", "detalhe": "a favor de Bolsonaro, que estava atrás no 1º turno"},
        {"rotulo": "Desvio-padrão entre municípios, 2026", "valor": disp[("municipio", 2026, "nao", "Brasil")]["dp"],
         "formato": "pp", "detalhe": f"2022: {disp[('municipio', 2022, 'nao', 'Brasil')]['dp'] * 100:.2f} p.p.".replace(".", ",")},
        {"rotulo": "Municípios na direção nacional, 2026", "valor": disp[("municipio", 2026, "nao", "Brasil")]["frac_mesmo_sinal"],
         "formato": "pct1", "detalhe": f"2022: {disp[('municipio', 2022, 'nao', 'Brasil')]['frac_mesmo_sinal'] * 100:.1f}%".replace(".", ",")},
    ]
    for k in kpis:
        if k["formato"] == "pp":
            k["detalhe"] = k["detalhe"].replace("+", "")
    salvar_json("ch02/kpis", {"meta": {"titulo": "KPIs do capítulo 2", "fonte": FONTE, "descricao": "", "gerado_em": HOJE,
                                       "script": SCRIPT}, "dados": kpis})
    geojson()
    (ACHADOS / "dados" / "02-mapa-da-virada.json").write_text(json.dumps(NUM, ensure_ascii=False, indent=1, default=str))
    print("ok")


if __name__ == "__main__":
    main()
