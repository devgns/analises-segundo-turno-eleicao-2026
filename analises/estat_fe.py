"""OLS com efeitos fixos (transformação within) e erro-padrão agrupado — usado pelos capítulos 07 e 08."""

from __future__ import annotations

import numpy as np
import polars as pl
import statsmodels.api as sm


def ols_fe(df: pl.DataFrame, y: str, xs: list[str], fe: str | None, cluster: str, peso: str | None = None,
           dummies: list[str] = ()) -> dict:
    """Regressão y ~ xs (+ dummies categóricas) com efeito fixo `fe` absorvido por demeaning.

    Retorna {var: {coef, ep, ic_inf, ic_sup, p}} + n, r2_within. EP agrupado por `cluster`.
    """
    cols = [y, *xs]
    d = df.drop_nulls([y, *xs, *dummies, cluster] + ([fe] if fe else []))
    for c in dummies:
        niveis = sorted(d[c].unique().to_list())[1:]
        for nv in niveis:
            nome = f"{c}={nv}"
            d = d.with_columns((pl.col(c) == nv).cast(pl.Float64).alias(nome))
            cols.append(nome)
    if fe:
        d = d.with_columns([(pl.col(c) - pl.col(c).mean().over(fe)).alias(c) for c in cols])
    Y = d[y].to_numpy().astype(float)
    X = d.select(cols[1:]).to_numpy().astype(float)
    if not fe:
        X = sm.add_constant(X)
    grupos = d[cluster].rank("dense").to_numpy()
    w = d[peso].to_numpy().astype(float) if peso else None
    mod = sm.WLS(Y, X, weights=w) if peso else sm.OLS(Y, X)
    res = mod.fit(cov_type="cluster", cov_kwds={"groups": grupos})
    nomes = (cols[1:] if fe else ["const", *cols[1:]])
    ci = res.conf_int()
    out = {"n": int(len(Y)), "r2": float(res.rsquared)}
    for i, nm in enumerate(nomes):
        out[nm] = {"coef": float(res.params[i]), "ep": float(res.bse[i]), "ic_inf": float(ci[i][0]),
                   "ic_sup": float(ci[i][1]), "p": float(res.pvalues[i])}
    return out


def bh(p: np.ndarray) -> np.ndarray:
    """q-valores de Benjamini–Hochberg."""
    p = np.asarray(p, float)
    n = len(p)
    ordem = np.argsort(p)
    q = p[ordem] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[ordem] = np.minimum(q, 1)
    return out
