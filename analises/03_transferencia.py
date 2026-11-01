"""Capítulo 03: para onde foram os eleitores de Cury, Renan, Caiado e Zema.

Inferência ecológica da matriz de transição 1º → 2º turno (2026), com linha de base de 2022,
mapa de viabilidade (que combinações de retenção/transferência reproduzem o resultado oficial)
e insumos do simulador Monte Carlo do site.

Método principal: regressão de Goodman restrita (mínimos quadrados ponderados pelo eleitorado,
com taxas de transição em [0, 1] e cada linha somando 1), ajustada separadamente por UF (ou por
região, no nível municipal) e agregada ao Brasil ponderando pelos votos de origem de cada grupo.
Incerteza: bootstrap por conglomerado (municípios), estratificado pelo grupo de ajuste.
Robustez: ajuste nacional único, por região, por UF e "local" (um ajuste por município grande).

Uso: uv run python analises/03_transferencia.py
"""

from __future__ import annotations

import os
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import ACHADOS, SITE_DATA, municipios_2022, municipios_2026, salvar_json, secoes_2026  # noqa: E402

SCRIPT = "analises/03_transferencia.py"
HOJE = date.today().isoformat()
RNG = np.random.default_rng(2026)
N_BOOT = int(os.environ.get("N_BOOT", 200))
SAIDA_TXT = ACHADOS / "03-transferencia-numeros.txt"

ORIG26 = ["lula_1", "flavio_1", "cury_1", "renan_1", "caiado_1", "zema_1", "menores_1", "bn_1", "abst_1"]
ORIG22 = ["lula_1", "bolsonaro_1", "ciro_1", "tebet_1", "menores_1", "bn_1", "abst_1"]
DEST = ["lula_2", "dir_2", "bn_2", "abst_2"]
NOMES = {
    "lula_1": "Lula", "flavio_1": "Flávio", "bolsonaro_1": "Bolsonaro", "cury_1": "Cury", "renan_1": "Renan",
    "caiado_1": "Caiado", "zema_1": "Zema", "menores_1": "Demais candidatos", "ciro_1": "Ciro", "tebet_1": "Tebet",
    "bn_1": "Branco/nulo", "abst_1": "Abstenção",
}
ELIM26 = ["cury_1", "renan_1", "caiado_1", "zema_1", "menores_1"]
ELIM22 = ["ciro_1", "tebet_1", "menores_1"]

linhas_txt: list[str] = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    linhas_txt.append(s)


# ---------------------------------------------------------------- dados
def preparar(df: pl.DataFrame, origens: list[str], dir_col: str, extra=()) -> pl.DataFrame:
    """Colunas de origem/destino; destinos reescalados para somar o eleitorado do 1º turno."""
    df = df.filter(pl.col("sg_uf") != "ZZ").with_columns(
        bn_1=pl.col("brancos_1") + pl.col("nulos_1"),
        abst_1=pl.col("aptos_1") - pl.col("comp_1"),
        bn_2=pl.col("brancos_2") + pl.col("nulos_2"),
        abst_2=pl.col("aptos_2") - pl.col("comp_2"),
        dir_2=pl.col(dir_col + "_2"),
    )
    if "menores_1" in origens and dir_col == "bolsonaro":
        df = df.with_columns(menores_1=pl.col("menores_1") + pl.col("soraya_1") + pl.col("davila_1"))
    # filtros: eleitorado mínimo e variação pequena do cadastro entre turnos
    df = df.filter(
        (pl.col("aptos_1") >= 20) & (pl.col("aptos_2") > 0)
        & ((pl.col("aptos_1") - pl.col("aptos_2")).abs() <= 0.05 * pl.col("aptos_1"))
    )
    esc = pl.col("aptos_1") / pl.col("aptos_2")
    return df.select(
        "sg_uf", "regiao", "cd_municipio_tse", "nm_municipio", *extra,
        *[pl.col(c).cast(pl.Float64) for c in origens],
        *[(pl.col(c).cast(pl.Float64) * esc).alias(c) for c in DEST],
        pl.col("aptos_1").cast(pl.Float64),
    )


def estatisticas(df: pl.DataFrame, origens: list[str]) -> dict:
    """Estatísticas suficientes por município: A = Σ X X'/n, C = Σ X Y'/n, O = Σ X, D = Σ Y."""
    df = df.sort("cd_municipio_tse")
    X = df.select(origens).to_numpy()
    Y = df.select(DEST).to_numpy()
    n = df["aptos_1"].to_numpy()
    mun = df["cd_municipio_tse"].to_numpy()
    _, ini = np.unique(mun, return_index=True)
    Xs = X / np.sqrt(n)[:, None]
    Ys = Y / np.sqrt(n)[:, None]
    A = np.add.reduceat(np.einsum("ik,il->ikl", Xs, Xs), ini, axis=0)
    C = np.add.reduceat(np.einsum("ik,il->ikl", Xs, Ys), ini, axis=0)
    O = np.add.reduceat(X, ini, axis=0)
    D = np.add.reduceat(Y, ini, axis=0)
    info = df.group_by("cd_municipio_tse", maintain_order=True).agg(
        pl.first("sg_uf"), pl.first("regiao"), pl.first("nm_municipio"), pl.len().alias("n_unid"))
    return {"A": A, "C": C, "O": O, "D": D, "info": info}


def ajustar(A: np.ndarray, C: np.ndarray, b0: np.ndarray | None = None) -> np.ndarray:
    """min Σ_i n_i ||y_i − x_i B||²  s.a.  B ≥ 0, B·1 = 1   (y, x em fração do eleitorado)."""
    K, J = C.shape
    s = np.trace(A) or 1.0
    A, C = A / s, C / s

    def f(b):
        B = b.reshape(K, J)
        AB = A @ B
        return np.sum(B * AB) - 2 * np.sum(B * C), (2 * AB - 2 * C).ravel()

    E = np.kron(np.eye(K), np.ones(J))
    cons = [{"type": "eq", "fun": lambda b: E @ b - 1, "jac": lambda b: E}]
    x0 = np.full(K * J, 1 / J) if b0 is None else b0.ravel()
    r = minimize(f, x0, jac=True, method="SLSQP", bounds=[(0, 1)] * (K * J), constraints=cons,
                 options={"ftol": 1e-15, "maxiter": 2000})
    B = np.clip(r.x.reshape(K, J), 0, 1)
    return B / B.sum(1, keepdims=True)


def ajustar_grupos(st: dict, chave: str | None, idx: np.ndarray | None = None, b0=None) -> tuple[np.ndarray, dict]:
    """Ajusta um B por grupo (UF/região) e agrega ponderando pelas origens. Devolve (B_agregado, {grupo: B})."""
    if idx is None:
        idx = np.arange(len(st["A"]))
    grupos = np.array(["BR"] * len(st["A"])) if chave is None else st["info"][chave].to_numpy()
    num = 0.0
    den = 0.0
    por = {}
    for g in np.unique(grupos[idx]):
        sel = idx[grupos[idx] == g]
        B = ajustar(st["A"][sel].sum(0), st["C"][sel].sum(0), None if b0 is None else b0.get(g))
        O = st["O"][sel].sum(0)
        num = num + O[:, None] * B
        den = den + O[:, None]
        por[g] = B
    return num / den, por


def _proj_simplex(V: np.ndarray) -> np.ndarray:
    """Projeção euclidiana de cada linha (último eixo) no simplex."""
    J = V.shape[-1]
    U = -np.sort(-V, axis=-1)
    css = np.cumsum(U, -1) - 1
    cond = U - css / np.arange(1, J + 1) > 0
    rho = J - 1 - np.argmax(cond[..., ::-1], -1)
    theta = np.take_along_axis(css, rho[..., None], -1) / (rho[..., None] + 1)
    return np.maximum(V - theta, 0)


def ajustar_lote(A: np.ndarray, C: np.ndarray, it: int = 6000) -> np.ndarray:
    """Mesmo problema de `ajustar`, para um lote (b, K, K)/(b, K, J), por gradiente projetado acelerado (FISTA).
    Convexo: converge ao mesmo ótimo do SLSQP (diferença máx. ~0,5 p.p. em 6 mil iterações; testado)."""
    s = np.trace(A, axis1=1, axis2=2)[:, None, None]
    s[s == 0] = 1
    A, C = A / s, C / s
    L = 2 * np.linalg.eigvalsh(A)[:, -1][:, None, None] + 1e-12
    B = np.full(C.shape, 1 / C.shape[-1])
    Y = B.copy()
    t = 1.0
    for _ in range(it):
        Bn = _proj_simplex(Y - 2 * (A @ Y - C) / L)
        tn = (1 + np.sqrt(1 + 4 * t * t)) / 2
        Y = Bn + ((t - 1) / tn) * (Bn - B)
        B, t = Bn, tn
    return B


def bootstrap(st: dict, chave: str | None, n_boot: int = N_BOOT) -> dict:
    """Bootstrap por município, estratificado pelo grupo de ajuste.
    Devolve {grupo: (B (n_boot, K, J), O (n_boot, K))}; agregue com `agregar`."""
    grupos = np.array(["BR"] * len(st["A"])) if chave is None else st["info"][chave].to_numpy()
    out = {}
    for g in np.unique(grupos):
        sel = np.flatnonzero(grupos == g)
        W = RNG.multinomial(len(sel), np.full(len(sel), 1 / len(sel)), size=n_boot).astype(float)
        A = np.einsum("bm,mkl->bkl", W, st["A"][sel])
        C = np.einsum("bm,mkl->bkl", W, st["C"][sel])
        out[g] = (ajustar_lote(A, C), W @ st["O"][sel])
    return out


def agregar(draws: dict, grupos=None) -> np.ndarray:
    """Agrega sorteios de vários grupos ponderando pelas origens (sorteadas)."""
    num = 0.0
    den = 0.0
    for g, (B, O) in draws.items():
        if grupos is not None and g not in grupos:
            continue
        num = num + O[:, :, None] * B
        den = den + O[:, :, None]
    return num / den


# ---------------------------------------------------------------- resumos
def resumo(B: np.ndarray, origens: list[str], O: np.ndarray, elim: list[str], dir_nome: str) -> dict:
    """Quantidades-chave de uma matriz B (linhas = origens, colunas = DEST)."""
    i = {o: k for k, o in enumerate(origens)}
    fl = i["flavio_1" if "flavio_1" in i else "bolsonaro_1"]
    li = i["lula_1"]
    e = [i[o] for o in elim]
    Oe = O[e]
    fe = (Oe[:, None] * B[e]).sum(0) / Oe.sum()
    pool = [i["bn_1"], i["abst_1"]]
    Op = O[pool]
    fp = (Op[:, None] * B[pool]).sum(0)  # votos
    return {
        "ret_lula": B[li, 0], "lula_para_dir": B[li, 1], "lula_sai": B[li, 2] + B[li, 3],
        "ret_dir": B[fl, 1], "dir_para_lula": B[fl, 0], "dir_sai": B[fl, 2] + B[fl, 3],
        "elim_lula": fe[0], "elim_dir": fe[1], "elim_bn": fe[2], "elim_abst": fe[3],
        "elim_dir_entre_validos": fe[1] / (fe[0] + fe[1]),
        "novos_validos_mi": (fp[0] + fp[1]) / 1e6,
        "novos_lula_entre_validos": fp[0] / (fp[0] + fp[1]),
        "bn1_lula": B[i["bn_1"], 0], "bn1_dir": B[i["bn_1"], 1],
        "abst1_lula": B[i["abst_1"], 0], "abst1_dir": B[i["abst_1"], 1],
    }


def resumo_ic(Bs: np.ndarray, origens, O, elim, dir_nome) -> dict:
    rs = [resumo(b, origens, O, elim, dir_nome) for b in Bs]
    return {k: (float(np.percentile([r[k] for r in rs], 2.5)), float(np.percentile([r[k] for r in rs], 97.5)))
            for k in rs[0]}


def fmt_res(nome, r, ic=None):
    def f(k, pct=True):
        v = r[k]
        s = f"{100 * v:5.1f}%" if pct else f"{v:5.2f}"
        if ic:
            lo, hi = ic[k]
            s += f" [{100 * lo:.1f}–{100 * hi:.1f}]" if pct else f" [{lo:.2f}–{hi:.2f}]"
        return s
    log(f"  {nome}")
    log(f"    retenção Lula {f('ret_lula')}  Lula→dir {f('lula_para_dir')} | retenção dir {f('ret_dir')}  dir→Lula {f('dir_para_lula')}")
    log(f"    eliminados → Lula {f('elim_lula')}  → dir {f('elim_dir')}  → BN {f('elim_bn')}  → abst {f('elim_abst')}"
        f"  | dir entre válidos {f('elim_dir_entre_validos')}")
    log(f"    BN1→Lula {f('bn1_lula')} BN1→dir {f('bn1_dir')} | abst1→Lula {f('abst1_lula')} abst1→dir {f('abst1_dir')}"
        f" | novos válidos {f('novos_validos_mi', False)} mi, Lula entre eles {f('novos_lula_entre_validos')}")


def meta(titulo, descricao, fonte="TSE — boletins de urna (bweb), 1º e 2º turnos de 2026 e 2022; cálculo próprio"):
    return {"titulo": titulo, "fonte": fonte, "descricao": descricao, "gerado_em": HOJE, "script": SCRIPT}


def r4(x):
    if isinstance(x, float):
        return round(x, 5)
    if isinstance(x, dict):
        return {k: r4(v) for k, v in x.items()}
    if isinstance(x, list):
        return [r4(v) for v in x]
    return x


def gravar(nome, titulo, descricao, dados, **extra):
    salvar_json(nome, r4({"meta": meta(titulo, descricao), "dados": dados, **extra}))


# ---------------------------------------------------------------- principal
def main():
    t0 = time.time()
    s = secoes_2026().filter(pl.col("pareada"))
    # totais oficiais (com exterior) para contabilidade e simulador
    tot = s.select(
        *[pl.col(c).sum() for c in ["lula_1", "flavio_1", "cury_1", "renan_1", "caiado_1", "zema_1", "menores_1",
                                    "brancos_1", "nulos_1", "comp_1", "aptos_1", "lula_2", "flavio_2", "brancos_2",
                                    "nulos_2", "comp_2", "aptos_2", "validos_1", "validos_2"]]
    ).to_dicts()[0]
    log("== Totais (seções pareadas, com exterior) ==")
    for k, v in tot.items():
        log(f"  {k:10s} {v:>13,}")
    d_lula = tot["lula_2"] - tot["lula_1"]
    d_fl = tot["flavio_2"] - tot["flavio_1"]
    elim_tot = sum(tot[c] for c in ["cury_1", "renan_1", "caiado_1", "zema_1", "menores_1"])
    bn1 = tot["brancos_1"] + tot["nulos_1"]
    bn2 = tot["brancos_2"] + tot["nulos_2"]
    log(f"  ΔLula {d_lula:,}  ΔFlávio {d_fl:,}  eliminados {elim_tot:,}  ΔBN {bn2 - bn1:,}  Δcomp {tot['comp_2'] - tot['comp_1']:,}")

    # ---------- 2026, seções
    sec = preparar(s, ORIG26, "flavio", extra=["zona", "secao"])
    log(f"\nSeções usadas no ajuste: {sec.height:,} (de {s.height:,} pareadas; exclui exterior, <20 aptos, Δcadastro>5%)")
    st = estatisticas(sec, ORIG26)
    O26 = st["O"].sum(0)
    # eleitorado oficial de cada origem (todas as seções, com exterior): as taxas são estimadas na amostra
    # do ajuste (O26) e aplicadas a estes totais para exibir votos
    tot_orig = secoes_2026().filter(pl.col("lula_1").is_not_null()).select(
        *[pl.col(c).sum() for c in ORIG26 if c not in ("bn_1", "abst_1")],
        bn_1=(pl.col("brancos_1") + pl.col("nulos_1")).sum(),
        abst_1=(pl.col("aptos_1") - pl.col("comp_1")).sum(),
    ).to_dicts()[0]
    O26_oficial = np.array([float(tot_orig[o]) for o in ORIG26])

    modelos = {}
    Bnac, _ = ajustar_grupos(st, None)
    Breg, _ = ajustar_grupos(st, "regiao")
    Buf, por_uf = ajustar_grupos(st, "sg_uf")
    modelos["2026 seções — Brasil (um ajuste)"] = Bnac
    modelos["2026 seções — por região"] = Breg
    modelos["2026 seções — por UF (principal)"] = Buf

    # modelo local: um ajuste por município com ≥ 60 seções; o resto agrupado por UF
    grande = st["info"]["n_unid"].to_numpy() >= 60
    gk = np.flatnonzero(grande)
    Bmun = ajustar_lote(st["A"][gk], st["C"][gk], it=20000)
    num = (st["O"][gk][:, :, None] * Bmun).sum(0)
    den = st["O"][gk].sum(0)[:, None]
    resto = np.flatnonzero(~grande)
    Bres, _ = ajustar_grupos(st, "sg_uf", resto)
    Ores = st["O"][resto].sum(0)
    Bloc = (num + Ores[:, None] * Bres) / (den + Ores[:, None])
    modelos["2026 seções — local (município grande / UF)"] = Bloc
    log(f"Modelo local: {grande.sum()} municípios com ≥60 seções ajustados um a um ({100 * st['O'][grande].sum() / O26.sum():.1f}% do eleitorado)")

    log("\nBootstrap 2026 seções por UF…")
    draws_uf = bootstrap(st, "sg_uf")
    Bs_uf = agregar(draws_uf)
    ic_uf = resumo_ic(Bs_uf, ORIG26, O26, ELIM26, "Flávio")
    lo_B, hi_B = np.percentile(Bs_uf, 2.5, axis=0), np.percentile(Bs_uf, 97.5, axis=0)

    # ---------- 2026 e 2022, municípios
    m26 = preparar(municipios_2026(), ORIG26, "flavio")
    st_m26 = estatisticas(m26, ORIG26)
    m22 = preparar(municipios_2022(), ORIG22, "bolsonaro")
    st_m22 = estatisticas(m22, ORIG22)
    O_m26, O_m22 = st_m26["O"].sum(0), st_m22["O"].sum(0)
    Bm26_nac, _ = ajustar_grupos(st_m26, None)
    Bm26, por_m26 = ajustar_grupos(st_m26, "regiao")
    Bm22_nac, _ = ajustar_grupos(st_m22, None)
    Bm22, por_m22 = ajustar_grupos(st_m22, "regiao")
    modelos["2026 municípios — Brasil (um ajuste)"] = Bm26_nac
    modelos["2026 municípios — por região"] = Bm26
    log("Bootstrap municípios…")
    Bs_m26 = agregar(bootstrap(st_m26, "regiao"))
    Bs_m22 = agregar(bootstrap(st_m22, "regiao"))
    ic_m26 = resumo_ic(Bs_m26, ORIG26, O_m26, ELIM26, "Flávio")
    ic_m22 = resumo_ic(Bs_m22, ORIG22, O_m22, ELIM22, "Bolsonaro")

    log("\n== Resumos (2026: dir = Flávio; 2022: dir = Bolsonaro). IC 95% bootstrap por município ==")
    tab_modelos = []
    for nome, B in modelos.items():
        O = O26 if "seções" in nome else O_m26
        r = resumo(B, ORIG26, O, ELIM26, "Flávio")
        ic = ic_uf if nome.endswith("(principal)") else ic_m26 if nome == "2026 municípios — por região" else None
        fmt_res(nome, r, ic)
        tab_modelos.append({"modelo": nome, "ano": 2026, **r,
                            **({f"{k}_lo": v[0] for k, v in ic.items()} if ic else {}),
                            **({f"{k}_hi": v[1] for k, v in ic.items()} if ic else {})})
    for nome, B, ic in [("2022 municípios — Brasil (um ajuste)", Bm22_nac, None),
                        ("2022 municípios — por região", Bm22, ic_m22)]:
        r = resumo(B, ORIG22, O_m22, ELIM22, "Bolsonaro")
        fmt_res(nome, r, ic)
        tab_modelos.append({"modelo": nome, "ano": 2022, **r,
                            **({f"{k}_lo": v[0] for k, v in ic.items()} if ic else {}),
                            **({f"{k}_hi": v[1] for k, v in ic.items()} if ic else {})})

    # matriz principal com IC (sankey + tabela)
    log("\n== Matriz principal (2026, seções, por UF agregada) — % do eleitorado de cada origem ==")
    matriz = []
    for k, o in enumerate(ORIG26):
        lin = {"origem": NOMES[o], "chave": o, "votos_origem": O26_oficial[k], "votos_amostra": float(O26[k])}
        for j, dnome in enumerate(["lula", "flavio", "bn", "abst"]):
            lin[f"para_{dnome}"] = float(Buf[k, j])
            lin[f"para_{dnome}_lo"] = float(lo_B[k, j])
            lin[f"para_{dnome}_hi"] = float(hi_B[k, j])
            lin[f"votos_{dnome}"] = O26_oficial[k] * float(Buf[k, j])
        matriz.append(lin)
        log(f"  {NOMES[o]:18s} " + "  ".join(f"{100 * Buf[k, j]:5.1f} [{100 * lo_B[k, j]:4.1f}–{100 * hi_B[k, j]:4.1f}]"
                                             for j in range(4)))
    pred = O26 @ Buf
    real = st["D"].sum(0)
    log("  previsto vs real (Lula, Flávio, BN, abst): " + ", ".join(f"{p / 1e6:.3f}/{r_ / 1e6:.3f}" for p, r_ in zip(pred, real)))
    gravar("cap03-matriz", "Matriz de transição estimada, 1º → 2º turno de 2026",
           "Fração do eleitorado de cada origem (1º turno) que foi para cada destino (2º turno). Regressão de Goodman "
           "restrita, ajustada por UF sobre ~490 mil seções pareadas e agregada ao Brasil; IC 95% por bootstrap de municípios.",
           matriz)

    # matriz 2022 (baseline) também para tabela
    matriz22 = []
    lo22, hi22 = np.percentile(Bs_m22, 2.5, axis=0), np.percentile(Bs_m22, 97.5, axis=0)
    for k, o in enumerate(ORIG22):
        lin = {"origem": NOMES[o], "chave": o, "votos_origem": float(O_m22[k])}
        for j, dnome in enumerate(["lula", "bolsonaro", "bn", "abst"]):
            lin[f"para_{dnome}"] = float(Bm22[k, j])
            lin[f"para_{dnome}_lo"] = float(lo22[k, j])
            lin[f"para_{dnome}_hi"] = float(hi22[k, j])
        matriz22.append(lin)
    gravar("cap03-matriz-2022", "Matriz de transição estimada, 1º → 2º turno de 2022 (linha de base)",
           "Mesmo método, nível municipal, ajuste por região agregado ao Brasil.", matriz22)
    gravar("cap03-modelos", "Quantidades-chave por modelo de inferência ecológica",
           "Retenções, transferências dos eliminados e dos que não votaram válido no 1º turno, por especificação.",
           tab_modelos)

    # ---------- por região (a partir dos ajustes por UF)
    log("\n== Por região (ajustes por UF, agregados na região) ==")
    reg_rows = []
    info = st["info"]
    ufs = info["sg_uf"].to_numpy()
    regs = info["regiao"].to_numpy()
    for reg in ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]:
        sel = np.flatnonzero(regs == reg)
        Br, _ = ajustar_grupos(st, "sg_uf", sel)
        Or = st["O"][sel].sum(0)
        bs = agregar(draws_uf, set(ufs[sel]))
        r = resumo(Br, ORIG26, Or, ELIM26, "Flávio")
        ic = resumo_ic(bs, ORIG26, Or, ELIM26, "Flávio")
        fmt_res(reg, r, ic)
        reg_rows.append({"regiao": reg, **r, **{f"{k}_lo": v[0] for k, v in ic.items()},
                         **{f"{k}_hi": v[1] for k, v in ic.items()}})
    gravar("cap03-regioes", "Transferência estimada por região (2026)",
           "Ajuste por UF agregado em cada região; IC 95% por bootstrap de municípios.", reg_rows)

    # ---------- por UF: cada eliminado (experimentos naturais)
    log("\n== Linha de cada eliminado, por UF (destaque onde o candidato foi forte) ==")
    uf_rows = []
    for uf, B in sorted(por_uf.items()):
        sel = ufs == uf
        O = st["O"][sel].sum(0)
        val1 = O[:7].sum()
        lin = {"uf": uf, "regiao": regs[sel][0]}
        for c in ["cury_1", "renan_1", "caiado_1", "zema_1"]:
            k = ORIG26.index(c)
            nm = c[:-2]
            lin[f"{nm}_share"] = float(O[k] / val1)
            lin[f"{nm}_lula"] = float(B[k, 0])
            lin[f"{nm}_flavio"] = float(B[k, 1])
            lin[f"{nm}_fora"] = float(B[k, 2] + B[k, 3])
        r = resumo(B, ORIG26, O, ELIM26, "Flávio")
        lin.update({k: float(r[k]) for k in ["ret_lula", "ret_dir", "dir_para_lula", "lula_para_dir",
                                             "elim_lula", "elim_dir", "elim_dir_entre_validos", "novos_lula_entre_validos"]})
        uf_rows.append(lin)
    # bootstrap para UFs-vitrine
    vitrines = {"caiado_1": "GO", "zema_1": "MG", "cury_1": None, "renan_1": None}
    shares = pl.DataFrame(uf_rows)
    grandes = {u for u in np.unique(ufs) if st["O"][ufs == u].sum() >= 3e6}
    for c in ["cury_1", "renan_1"]:
        vitrines[c] = shares.filter(pl.col("uf").is_in(list(grandes))).sort(f"{c[:-2]}_share", descending=True)["uf"][0]
    cand_rows = []
    rN = resumo(Buf, ORIG26, O26, ELIM26, "Flávio")
    for c, uf in vitrines.items():
        k = ORIG26.index(c)
        nm = NOMES[c]
        cand_rows.append({"candidato": nm, "recorte": "Brasil", "votos": O26_oficial[k],
                          "lula": float(Buf[k, 0]), "flavio": float(Buf[k, 1]), "fora": float(Buf[k, 2] + Buf[k, 3]),
                          "lula_lo": float(lo_B[k, 0]), "lula_hi": float(hi_B[k, 0]),
                          "flavio_lo": float(lo_B[k, 1]), "flavio_hi": float(hi_B[k, 1])})
        sel = np.flatnonzero(ufs == uf)
        bs = draws_uf[uf][0]
        B = por_uf[uf]
        Ou = st["O"][sel].sum(0)
        cand_rows.append({"candidato": nm, "recorte": uf, "votos": float(Ou[k]),
                          "share_validos": float(Ou[k] / Ou[:7].sum()),
                          "lula": float(B[k, 0]), "flavio": float(B[k, 1]), "fora": float(B[k, 2] + B[k, 3]),
                          "lula_lo": float(np.percentile(bs[:, k, 0], 2.5)), "lula_hi": float(np.percentile(bs[:, k, 0], 97.5)),
                          "flavio_lo": float(np.percentile(bs[:, k, 1], 2.5)), "flavio_hi": float(np.percentile(bs[:, k, 1], 97.5))})
        log(f"  {nm:8s} Brasil: Lula {100 * Buf[k, 0]:.1f}% Flávio {100 * Buf[k, 1]:.1f}% | {uf} ({100 * Ou[k] / Ou[:7].sum():.1f}% dos válidos): "
            f"Lula {100 * B[k, 0]:.1f}% [{100 * cand_rows[-1]['lula_lo']:.1f}–{100 * cand_rows[-1]['lula_hi']:.1f}] "
            f"Flávio {100 * B[k, 1]:.1f}% [{100 * cand_rows[-1]['flavio_lo']:.1f}–{100 * cand_rows[-1]['flavio_hi']:.1f}]")
    gravar("cap03-ufs", "Transferência estimada por UF (2026)", "Um ajuste por UF; seções pareadas.", uf_rows)
    gravar("cap03-candidatos", "Destino estimado dos eleitores de cada eliminado",
           "Brasil (agregado dos ajustes por UF) e a UF onde o candidato teve maior fatia. IC 95% bootstrap.", cand_rows)

    # ---------- experimento natural: Goiás (Caiado governador), municípios
    go = (municipios_2026().filter(pl.col("sg_uf") == "GO")
          .with_columns(caiado=pl.col("caiado_1") / pl.col("aptos_1"),
                        d_lula=(pl.col("lula_2") - pl.col("lula_1")) / pl.col("aptos_1"),
                        d_flavio=(pl.col("flavio_2") - pl.col("flavio_1")) / pl.col("aptos_1"))
          .select("nm_municipio", "cd_municipio_ibge", "aptos_1", "caiado", "d_lula", "d_flavio"))
    w = go["aptos_1"].to_numpy()
    xg = go["caiado"].to_numpy()
    coefs = {}
    for c in ["d_lula", "d_flavio"]:
        yv = go[c].to_numpy()
        Xd = np.column_stack([np.ones_like(xg), xg])
        beta = np.linalg.lstsq(Xd * np.sqrt(w)[:, None], yv * np.sqrt(w), rcond=None)[0]
        coefs[c] = beta.tolist()
    log(f"\nGoiás, municípios (n={go.height}): inclinação ΔLula/aptos vs Caiado/aptos = {coefs['d_lula'][1]:.3f}; "
        f"ΔFlávio = {coefs['d_flavio'][1]:.3f}")
    gravar("cap03-goias", "Goiás: crescimento de Lula e de Flávio × votação de Caiado, por município",
           "Eixo x: votos de Caiado no 1º turno / eleitorado. Eixo y: variação de votos entre turnos / eleitorado.",
           go.rename({"nm_municipio": "municipio", "cd_municipio_ibge": "codigo_ibge", "aptos_1": "eleitores"}).to_dicts(),
           regressao=coefs)

    # ---------- descritivo sem modelo: o que mudou por faixa de votação de Lula no 1º turno
    fx = (s.filter(pl.col("sg_uf") != "ZZ")
          .with_columns(sh=pl.col("lula_1") / (pl.col("lula_1") + pl.col("flavio_1")))
          .with_columns(faixa=(pl.col("sh") * 10).floor().clip(0, 9).cast(pl.Int32))
          .group_by("faixa").agg(
              pl.len().alias("secoes"), pl.col("aptos_1").sum().alias("eleitores"),
              ((pl.col("lula_2") - pl.col("lula_1")).sum() / pl.col("aptos_1").sum()).alias("d_lula"),
              ((pl.col("flavio_2") - pl.col("flavio_1")).sum() / pl.col("aptos_1").sum()).alias("d_flavio"),
              (pl.col("outros_1").sum() / pl.col("aptos_1").sum()).alias("eliminados"),
              ((pl.col("brancos_1") + pl.col("nulos_1") - pl.col("brancos_2") - pl.col("nulos_2")).sum()
               / pl.col("aptos_1").sum()).alias("queda_bn"),
              ((pl.col("comp_2") - pl.col("comp_1")).sum() / pl.col("aptos_1").sum()).alias("d_comparecimento"))
          .sort("faixa")
          .with_columns(rotulo=pl.format("{}–{}%", pl.col("faixa") * 10, pl.col("faixa") * 10 + 10)))
    log("\n== Sem modelo: variações por faixa de Lula/(Lula+Flávio) no 1º turno, em % do eleitorado ==")
    for r_ in fx.iter_rows(named=True):
        log(f"  {r_['rotulo']:>8s} seções {r_['secoes']:>6,}  ΔLula {100 * r_['d_lula']:5.2f}  ΔFlávio {100 * r_['d_flavio']:5.2f}"
            f"  eliminados {100 * r_['eliminados']:5.2f}  queda BN {100 * r_['queda_bn']:5.2f}  Δcomp {100 * r_['d_comparecimento']:5.2f}")
    # mesma conta por município, 2026 × 2022 (linha de base comparável)
    fx_mun = []
    for ano, mdf, dcol in [(2026, municipios_2026(), "flavio"), (2022, municipios_2022(), "bolsonaro")]:
        f = (mdf.filter(pl.col("sg_uf") != "ZZ")
             .with_columns(sh=pl.col("lula_1") / (pl.col("lula_1") + pl.col(dcol + "_1")))
             .with_columns(faixa=(pl.col("sh") * 10).floor().clip(1, 8).cast(pl.Int32))
             .group_by("faixa").agg(
                 pl.len().alias("municipios"), pl.col("aptos_1").sum().alias("eleitores"),
                 ((pl.col("lula_2") - pl.col("lula_1")).sum() / pl.col("aptos_1").sum()).alias("d_lula"),
                 ((pl.col(dcol + "_2") - pl.col(dcol + "_1")).sum() / pl.col("aptos_1").sum()).alias("d_direita"),
                 (pl.col("outros_1").sum() / pl.col("aptos_1").sum()).alias("eliminados"),
                 ((pl.col("brancos_1") + pl.col("nulos_1") - pl.col("brancos_2") - pl.col("nulos_2")).sum()
                  / pl.col("aptos_1").sum()).alias("queda_bn"),
                 ((pl.col("comp_2") - pl.col("comp_1")).sum() / pl.col("aptos_1").sum()).alias("d_comparecimento"))
             .sort("faixa")
             .with_columns(ano=pl.lit(ano),
                           rotulo=pl.when(pl.col("faixa") == 1).then(pl.lit("<20%"))
                           .when(pl.col("faixa") == 8).then(pl.lit("≥80%"))
                           .otherwise(pl.format("{}–{}%", pl.col("faixa") * 10, pl.col("faixa") * 10 + 10)),
                           fatia_direita_do_ganho=pl.col("d_direita") / (pl.col("d_lula") + pl.col("d_direita"))))
        fx_mun.append(f)
        log(f"\n  Municípios {ano} (direita = {dcol}):")
        for r_ in f.iter_rows(named=True):
            log(f"    {r_['rotulo']:>7s} n={r_['municipios']:>4}  ΔLula {100 * r_['d_lula']:5.2f}  Δdir {100 * r_['d_direita']:5.2f}"
                f"  elim {100 * r_['eliminados']:5.2f}  queda BN {100 * r_['queda_bn']:5.2f}  Δcomp {100 * r_['d_comparecimento']:5.2f}"
                f"  fatia da direita no ganho {100 * r_['fatia_direita_do_ganho']:5.1f}%")
    gravar("cap03-faixas", "O que mudou entre turnos, por faixa de votação de Lula no 1º turno — 2026 × 2022",
           "Municípios agrupados pela fatia de Lula entre os dois finalistas no 1º turno; variações em fração do eleitorado "
           "do 1º turno. Direita = Flávio (2026) ou Bolsonaro (2022).",
           pl.concat(fx_mun).to_dicts())

    # ---------- teste de poder: o método enxergaria uma alteração sintética?
    log("\n== Teste de poder: alteração sintética injetada nas seções, reestimada por UF ==")
    rB = resumo(Buf, ORIG26, O26, ELIM26, "Flávio")
    poder = [{"cenario": "Dados oficiais (sem injeção)", "votos_movidos": 0.0, **rB}]
    cenarios_f = [
        ("Virada uniforme: 4,8% dos votos de Flávio viram de Lula", "dir_2", 0.048),
        ("Enchimento: 20% dos abstencionistas viram votos de Lula", "abst_2", 0.20),
        ("Enchimento proporcional a Lula: +9% sobre os votos de Lula, tirados da abstenção", "lula_2", 0.09),
    ]
    for nome, base_col, tam in cenarios_f:
        mov = pl.col(base_col) * tam
        if base_col == "lula_2":
            mov = pl.min_horizontal(pl.col("lula_2") * tam, pl.col("abst_2"))
            fonte = "abst_2"
        else:
            fonte = base_col
        sec_f = sec.with_columns(_m=mov).with_columns(
            lula_2=pl.col("lula_2") + pl.col("_m"), **{fonte: pl.col(fonte) - pl.col("_m")})
        movidos = float(sec_f["_m"].sum())
        st_f = estatisticas(sec_f.drop("_m"), ORIG26)
        Bf, _ = ajustar_grupos(st_f, "sg_uf")
        rf = resumo(Bf, ORIG26, st_f["O"].sum(0), ELIM26, "Flávio")
        D = st_f["D"].sum(0)
        log(f"  {nome}: {movidos / 1e6:.2f} mi de votos movidos; Lula passa a {100 * D[0] / (D[0] + D[1]):.2f}% dos válidos")
        fmt_res("    reestimado", rf)
        poder.append({"cenario": nome, "votos_movidos": movidos, "lula_share": float(D[0] / (D[0] + D[1])), **rf})
    gravar("cap03-poder", "Teste de poder: alterações sintéticas e o que a inferência ecológica enxerga",
           "Cada linha injeta uma alteração uniforme nas seções e reestima a matriz por UF.", poder)

    # ---------- contabilidade, viabilidade e pesquisas (só números verificados)
    L1, F1 = tot["lula_1"], tot["flavio_1"]
    V2 = tot["lula_2"] + tot["flavio_2"]
    share_oficial = tot["lula_2"] / V2
    ELIM_IDS = ["cury", "renan", "caiado", "zema", "menores"]
    votos_e = {c: tot[f"{c}_1"] for c in ELIM_IDS}

    def contas(rL, cL, rF, cF, elim):
        """elim = {cand: (fração→Lula, fração→Flávio)} do eleitorado de cada eliminado."""
        lula = L1 * rL + F1 * cF + sum(votos_e[c] * elim[c][0] for c in ELIM_IDS)
        dirv = F1 * rF + L1 * cL + sum(votos_e[c] * elim[c][1] for c in ELIM_IDS)
        return lula, dirv, V2 - lula - dirv

    def prever(rL, cL, rF, cF, elim, sP):
        """Lula% dos válidos, condicionado ao total oficial de válidos; os 'novos' votantes válidos se dividem em sP."""
        lula, dirv, vp = contas(rL, cL, rF, cF, elim)
        lula += vp * sP
        dirv += vp * (1 - sP)
        return lula / (lula + dirv), vp

    def sP_necessario(rL, cL, rF, cF, elim):
        lula, _, vp = contas(rL, cL, rF, cF, elim)
        return (tot["lula_2"] - lula) / vp, vp

    def x_agregado(elim):
        L = sum(votos_e[c] * elim[c][0] for c in ELIM_IDS)
        F = sum(votos_e[c] * elim[c][1] for c in ELIM_IDS)
        return F / (L + F), (L + F) / sum(votos_e.values())

    # Pesquisas verificadas. Quaest 17–20/10 (BR-08535/2026, divulgada 21/10): só por candidato; Zema não publicado
    # (usamos o de Caiado); "demais" recebem o agregado ponderado. Datafolha 06–07/10 (divulgado 08/10): agregado 46/32/15.
    Q = {"cury": (0.48, 0.33), "renan": (0.25, 0.51), "caiado": (0.21, 0.57)}
    pesos = {c: votos_e[c] for c in Q}
    qL = sum(pesos[c] * Q[c][0] for c in Q) / sum(pesos.values())
    qF = sum(pesos[c] * Q[c][1] for c in Q) / sum(pesos.values())
    Q_ELIM = {**Q, "zema": Q["caiado"], "menores": (qL, qF)}
    D_ELIM = {c: (0.32, 0.46) for c in ELIM_IDS}
    # Quaest divulgada em 22/10 (quaest.com.br/segundo-turno-2026-votos-brancos-nulos): eliminados 37% Lula × 43% Flávio
    # (agregado), retenção declarada 95% Lula / 94% Flávio, ausentes/branco/nulo do 1º turno 40% Lula × 36% Flávio.
    # Sem subamostras publicadas: não são parâmetros exatos.
    Q22_ELIM = {c: (0.37, 0.43) for c in ELIM_IDS}
    log(f"\nQuaest 17–20/10 ponderada pelos votos do 1º turno: Lula {100 * qL:.1f}% × Flávio {100 * qF:.1f}% "
        f"({100 * qF / (qL + qF):.1f}% Flávio entre quem escolhe)")
    # retenção: nos cenários principais usamos a estimada pelos dados (favorável a reproduzir o oficial); a Quaest de
    # 22/10 publicou retenção declarada, usada num cenário à parte (metade das perdas vai ao adversário, como no mapa)
    rE = resumo(Buf, ORIG26, O26, ELIM26, "Flávio")
    RET = dict(rL=rE["ret_lula"], cL=rE["lula_para_dir"], rF=rE["ret_dir"], cF=rE["dir_para_lula"])
    ei_elim = {c: (float(Buf[ORIG26.index(c + "_1"), 0]), float(Buf[ORIG26.index(c + "_1"), 1])) for c in ELIM_IDS}
    cen = {
        "Quaest 17–20/10": dict(**RET, elim=Q_ELIM, sP=0.494),
        "Datafolha 06–07/10": dict(**RET, elim=D_ELIM, sP=0.48),
        "Quaest 22/10": dict(**RET, elim=Q22_ELIM, sP=0.40 / 0.76),
        "Quaest 22/10, retenção declarada (95%/94%)": dict(rL=0.95, cL=0.025, rF=0.94, cF=0.03, elim=Q22_ELIM, sP=0.40 / 0.76),
        "Inferência ecológica (este capítulo)": dict(**RET, elim=ei_elim, sP=rE["novos_lula_entre_validos"]),
    }
    log(f"\n== Cenários (resultado oficial: Lula {100 * share_oficial:.3f}% dos válidos). Retenção dos finalistas = estimada "
        f"pelos dados (Lula {100 * RET['rL']:.1f}%, Flávio {100 * RET['rF']:.1f}%); novos votantes divididos como o "
        f"cabeçalho da própria pesquisa ==")
    pontos = []
    for nome, c in cen.items():
        sh, vp = prever(**c)
        sh50, _ = prever(**{**c, "sP": 0.5})
        sp_n, _ = sP_necessario(**{k: v for k, v in c.items() if k != "sP"})
        c100 = {**c, "rL": 1.0, "cL": 0.0, "rF": 1.0, "cF": 0.0}
        sp_100, vp100 = sP_necessario(**{k: v for k, v in c100.items() if k != "sP"})
        x, pE = x_agregado(c["elim"])
        log(f"  {nome}: eliminados → Flávio {100 * x:.1f}% entre válidos (votam válido {100 * pE:.0f}%). Lula previsto "
            f"{100 * sh:.2f}% (oficial − previsto {100 * (share_oficial - sh):+.2f} p.p.; com novos 50/50: {100 * sh50:.2f}%); "
            f"novos válidos {vp / 1e6:.2f} mi; Lula precisaria de {100 * sp_n:.1f}% deles (cabeçalho da pesquisa: "
            f"{100 * c['sP']:.1f}%); com retenção 100%: {100 * sp_100:.1f}% de {vp100 / 1e6:.2f} mi")
        pontos.append({"cenario": nome, "x": x, "y": c["rF"], "votam_validos": pE, "lula_previsto": sh,
                       "lula_previsto_50": sh50, "erro_pp": share_oficial - sh, "novos_validos": vp,
                       "sP_pesquisa": c["sP"], "sP_necessario": sp_n, "sP_necessario_ret100": sp_100})

    # mapa: x = % eliminados→Flávio entre válidos (igual para todos), y = retenção de Flávio.
    # Fixos: retenção de Lula estimada, 78,6% dos eliminados votam válido (Quaest ponderada), novos 49,4% Lula (Quaest).
    pE0 = x_agregado(Q_ELIM)[1]
    base = dict(rL=RET["rL"], cL=RET["cL"], pE=pE0, sP=0.494)
    xs = np.round(np.arange(0.30, 0.801, 0.01), 3)
    ys = np.round(np.arange(0.88, 1.0001, 0.0025), 4)
    grade = []
    for y in ys:
        for x in xs:
            cF = (1 - y) / 2  # metade de quem deixa Flávio vai para Lula, metade sai (branco/nulo/abstenção)
            el = {c: (base["pE"] * (1 - x), base["pE"] * x) for c in ELIM_IDS}
            sh, vp = prever(base["rL"], base["cL"], y, cF, el, base["sP"])
            spn, _ = sP_necessario(base["rL"], base["cL"], y, cF, el)
            grade.append({"x": float(x), "y": float(y), "lula": sh, "dif": sh - share_oficial, "sP_necessario": spn})
    curva = []
    for x in xs:
        difs = np.array([g["dif"] for g in grade if g["x"] == x])
        if difs.min() <= 0 <= difs.max():
            yy = np.interp(0, difs[::-1], ys[::-1]) if difs[0] > difs[-1] else np.interp(0, difs, ys)
            curva.append({"x": float(x), "y": float(yy)})
    log("  Mapa: curva de reprodução do oficial: " + ", ".join(f"x={c['x']:.2f}→y={c['y']:.3f}" for c in curva[::5]))
    gravar("cap03-viabilidade", "Mapa de viabilidade: o que reproduz o resultado oficial?",
           "Lula previsto (% dos válidos) menos o oficial, variando a parcela dos eliminados que vai para Flávio (entre os "
           "que votam válido) e a retenção de Flávio. Fixos: retenção de Lula estimada pelos dados, 78,6% dos eliminados "
           "votando válido e novos votantes 49,4% Lula (Quaest 17–20/10); metade de quem deixa Flávio vai para Lula; "
           "total de válidos igual ao oficial.",
           grade, pontos=pontos, curva=curva, oficial=share_oficial, fixos=base)

    # comparação pesquisa × dados, por candidato (fração para Flávio entre quem escolheu um finalista)
    def frac_f(Bm, ks):
        Ok = O26[ks]
        L = (Ok * Bm[..., ks, 0]).sum(-1)
        F = (Ok * Bm[..., ks, 1]).sum(-1)
        return F / (L + F)
    comp = []
    idx_all = [ORIG26.index(c + "_1") for c in ELIM_IDS]
    for nome, ks, pesq in [
        ("Eliminados (todos)", idx_all, [("Quaest 17–20/10 (ponderada)", qF / (qL + qF)), ("Datafolha 06–07/10", 46 / 78),
                                         ("Quaest 22/10", 43 / 80)]),
        ("Cury", [ORIG26.index("cury_1")], [("Quaest 17–20/10", 33 / 81)]),
        ("Renan", [ORIG26.index("renan_1")], [("Quaest 17–20/10", 51 / 76)]),
        ("Caiado", [ORIG26.index("caiado_1")], [("Quaest 17–20/10", 57 / 78)]),
        ("Zema", [ORIG26.index("zema_1")], []),
    ]:
        d = frac_f(Buf, ks)
        bs = frac_f(Bs_uf, ks)
        comp.append({"indicador": nome, "dados": float(d), "lo": float(np.percentile(bs, 2.5)),
                     "hi": float(np.percentile(bs, 97.5)), "pesquisas": [{"nome": n, "valor": v} for n, v in pesq]})
        log(f"  {nome:20s} dados {100 * d:.1f}% [{100 * np.percentile(bs, 2.5):.1f}–{100 * np.percentile(bs, 97.5):.1f}]  "
            + "  ".join(f"{n}: {100 * v:.1f}%" for n, v in pesq))
    gravar("cap03-pesquisas", "Fração que foi para Flávio, entre os eleitores de cada eliminado que escolheram um finalista",
           "Inferência ecológica (IC 95% bootstrap) × pesquisas verificadas (Quaest 17–20/10 por candidato; Datafolha 06–07/10; Quaest 22/10, agregado).",
           comp)

    # ---------- simulador: bases nacionais e presets
    abst1 = tot["aptos_1"] - tot["comp_1"]
    sim = {
        "aptos_1": tot["aptos_1"], "aptos_2": tot["aptos_2"],
        "grupos": {"lula": L1, "flavio": F1, "cury": tot["cury_1"], "renan": tot["renan_1"], "caiado": tot["caiado_1"],
                   "zema": tot["zema_1"], "menores": tot["menores_1"], "bn": bn1, "abst": abst1},
        "oficial": {"lula": tot["lula_2"], "flavio": tot["flavio_2"], "bn": bn2, "abst": tot["aptos_2"] - tot["comp_2"],
                    "share_lula": share_oficial},
    }
    # preset ecológico: por grupo, válidos e divisão
    def preset_ei(B):
        g = {}
        for c in ["cury_1", "renan_1", "caiado_1", "zema_1", "menores_1"]:
            k = ORIG26.index(c)
            g[c[:-2]] = {"valido": float(B[k, 0] + B[k, 1]), "flavio": float(B[k, 1] / max(B[k, 0] + B[k, 1], 1e-9))}
        kL, kF, kb, ka = (ORIG26.index(c) for c in ["lula_1", "flavio_1", "bn_1", "abst_1"])
        return {"retL": float(B[kL, 0]), "retF": float(B[kF, 1]),
                "trocaL": float(B[kL, 1] / max(1 - B[kL, 0], 1e-9)), "trocaF": float(B[kF, 0] / max(1 - B[kF, 1], 1e-9)),
                "elim": g, "bnValido": float(B[kb, 0] + B[kb, 1]), "bnLula": float(B[kb, 0] / max(B[kb, 0] + B[kb, 1], 1e-9)),
                "abstValido": float(B[ka, 0] + B[ka, 1]), "abstLula": float(B[ka, 0] / max(B[ka, 0] + B[ka, 1], 1e-9))}
    sim["preset_ei"] = preset_ei(Buf)
    sim["preset_ei_lo_hi"] = {"retF": [float(lo_B[1, 1]), float(hi_B[1, 1])], "retL": [float(lo_B[0, 0]), float(hi_B[0, 0])]}
    salvar_json("cap03-sim", r4({"meta": meta("Bases do simulador de transferência", "Totais nacionais (com exterior) e cenários."),
                                 "dados": [], **sim}))

    # ---------- KPIs
    rU = rE
    kpis = [
        {"rotulo": "Retenção estimada de Flávio", "valor": rU["ret_dir"], "formato": "pct1",
         "detalhe": f"IC 95% {100 * ic_uf['ret_dir'][0]:.1f}–{100 * ic_uf['ret_dir'][1]:.1f}%; Flávio → Lula: {100 * rU['dir_para_lula']:.1f}%".replace(".", ","),
         "cor": "flavio"},
        {"rotulo": "Eliminados que foram para Flávio, entre os que escolheram um finalista", "valor": rU["elim_dir_entre_validos"],
         "formato": "pct1", "detalhe": f"Quaest 17–20/10: {100 * qF / (qL + qF):.0f}%; Datafolha 06–07/10: 59%", "cor": "flavio"},
        {"rotulo": "Lula entre quem não votou válido no 1º turno e votou no 2º", "valor": rU["novos_lula_entre_validos"],
         "formato": "pct1", "detalhe": f"{rU['novos_validos_mi']:.1f} mi de novos votos válidos (estimativa instável)".replace(".", ","),
         "cor": "lula"},
        {"rotulo": "Oficial menos o previsto pelos cruzamentos da Quaest", "valor": pontos[0]["erro_pp"], "formato": "pp",
         "detalhe": f"Lula previsto: {100 * pontos[0]['lula_previsto']:.2f}%; Datafolha: {100 * pontos[1]['lula_previsto']:.2f}%".replace(".", ",")},
    ]
    salvar_json("cap03-kpis", r4({"meta": meta("KPIs do capítulo 3", ""), "dados": kpis}))

    log(f"\nTempo total: {time.time() - t0:.0f} s")
    SAIDA_TXT.write_text("\n".join(linhas_txt) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
