"""Cap. 6c: o teste do "serrote" nos nove casos do RJ (capítulo 4).

Pergunta: nos municípios em que Lula cresceu muito e Flávio ficou estagnado (Campos, Região dos Lagos, Silva Jardim),
a variação de votos tem algum padrão ligado ao TEMPO, como quedas de Flávio em intervalos regulares
ao longo da chegada dos boletins? Esse seria o rastro de um "algoritmo que liga e desliga".

Unidade: seção (mesma seção nos dois turnos). Medida por seção:
    y = fatia de Flávio entre os finalistas no 2º turno − a mesma fatia no 1º turno (Flávio/(Flávio+Lula))
    r = y − média ponderada de y no mesmo local de votação (a escola), ponderada pelos votos nos finalistas no 2º turno
Assim, r compara cada seção com as vizinhas da mesma escola; a composição do local sai da conta.

Testes:
    1. Placebo de ordem: fatia acumulada de Flávio na ordem de chegada do 2º turno, votos do 2º × do 1º turno.
    2. Fase do minuto (segundo de chegada), janelas de 8 s, nulo = embaralhar r dentro do local (horários fixos); poder por injeção.
    3. Periodicidade no tempo de chegada: espectro do resíduo em votos, por 10 s, períodos de 30 s a 20 min;
       nulo = embaralhar r dentro do local (mantém os horários, quebra a ligação).
    4. Tendência: r × minuto de chegada (o "algoritmo ligado" no começo ou no fim), nulo idem.
    5. Estagnação de Flávio: ΔF (votos) acumulado ao longo da chegada, por município.
Os mesmos testes no resto do RJ servem de comparação (mesmo dia, mesma pausa de recebimento).

Rode: uv run python analises/06c_serrote_casos_rj.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import salvar_json, secoes_2026  # noqa: E402

CASOS = {
    "3301009": "Campos dos Goytacazes", "3300209": "Araruama", "3300233": "Armação dos Búzios",
    "3300258": "Arraial do Cabo", "3300704": "Cabo Frio", "3301876": "Iguaba Grande",
    "3305208": "São Pedro da Aldeia", "3305505": "Saquarema", "3305604": "Silva Jardim",
}
RNG = np.random.default_rng(4)
GERADO = datetime.now().strftime("%Y-%m-%d")
FONTE = "TSE: boletins de urna por seção, 1º e 2º turnos de 2026 (DT_BU_RECEBIDO do 2º turno); cálculo próprio"


def meta(titulo, descricao):
    return {"titulo": titulo, "fonte": FONTE, "descricao": descricao, "gerado_em": GERADO,
            "script": "analises/06c_serrote_casos_rj.py"}


def carregar() -> pl.DataFrame:
    s = secoes_2026().filter((pl.col("sg_uf") == "RJ") & pl.col("pareada"))
    s = s.filter((pl.col("flavio_2") + pl.col("lula_2") > 0) & (pl.col("flavio_1") + pl.col("lula_1") > 0))
    t0 = s["bu_recebido_2"].min()
    return s.with_columns(
        caso=pl.col("cd_municipio_ibge").cast(pl.Utf8).is_in(list(CASOS)),
        municipio=pl.col("cd_municipio_ibge").cast(pl.Utf8).replace_strict(CASOS, default=None),
        grupo=pl.concat_str(["cd_municipio_tse", "zona", "local"], separator="-"),
        w=(pl.col("flavio_2") + pl.col("lula_2")).cast(pl.Float64),
        y=pl.col("flavio_2") / (pl.col("flavio_2") + pl.col("lula_2")) - pl.col("flavio_1") / (pl.col("flavio_1") + pl.col("lula_1")),
        seg=(pl.col("bu_recebido_2") - t0).dt.total_seconds(),
        fase=pl.col("bu_recebido_2").dt.second(),
    ).sort(["bu_recebido_2", "cd_municipio_tse", "zona", "secao"])


class Bloco:
    """Arrays de um conjunto de seções, com o resíduo dentro do local."""

    def __init__(self, d: pl.DataFrame):
        self.d = d
        self.g = d["grupo"].cast(pl.Categorical).to_physical().to_numpy()
        self.ng = int(self.g.max()) + 1
        self.w = d["w"].to_numpy()
        self.f2 = d["flavio_2"].to_numpy().astype(float)
        self.y0 = d["y"].to_numpy()
        self.fase = d["fase"].to_numpy().astype(int)
        self.seg = d["seg"].to_numpy().astype(int)
        self.sw = np.bincount(self.g, weights=self.w, minlength=self.ng)
        self.ordem_g = np.argsort(self.g, kind="stable")
        self.cortes = np.flatnonzero(np.diff(self.g[self.ordem_g])) + 1
        self.r = self.residuo(self.y0)

    def residuo(self, y):
        return y - (np.bincount(self.g, weights=y * self.w, minlength=self.ng) / self.sw)[self.g]

    def y_com_injecao(self, alvo, phi):
        """Move uma fração phi dos votos de Flávio para Lula nas seções-alvo (muda só o 2º turno)."""
        f2 = np.where(alvo, self.f2 * (1 - phi), self.f2)  # Flávio + Lula não muda, então w também não
        return self.y0 + (f2 - self.f2) / self.w

    def embaralhar_no_local(self, v):
        out = np.empty_like(v)
        out[self.ordem_g] = v[np.lexsort((RNG.random(len(v)), self.g))]
        return out


# ------------------------------------------------------------------ testes
def janelas_fase(b: Bloco, r, fase, k=8):
    """Para cada janela circular de k segundos do minuto: média ponderada do resíduo e escore z (soma / erro-padrão).
    O z trata por igual janelas cheias e quase vazias; a média dá o tamanho do efeito em p.p."""
    soma = np.bincount(fase, weights=r * b.w, minlength=60)
    peso = np.bincount(fase, weights=b.w, minlength=60)
    quad = np.bincount(fase, weights=(r * b.w) ** 2, minlength=60)
    janela = lambda v: np.convolve(np.r_[v, v[:k - 1]], np.ones(k), "valid")  # noqa: E731
    S, W, Q = janela(soma), janela(peso), janela(quad)
    return S / np.maximum(W, 1), S / np.sqrt(np.maximum(Q, 1e-12))


def teste_fase(b: Bloco, n_perm=1000, efeitos=(0.01, 0.02, 0.05, 0.10, 0.20)):
    m, zz = janelas_fase(b, b.r, b.fase)
    obs_uni, obs_bi = -zz.min(), np.abs(zz).max()      # direção alegada: Flávio perde (z negativo)
    j = int(np.argmin(zz))
    # nulo: os horários de chegada ficam exatamente como foram; embaralha-se o resíduo entre as seções da mesma escola
    nulo = []
    for _ in range(n_perm):
        z2 = janelas_fase(b, b.embaralhar_no_local(b.r), b.fase)[1]
        nulo.append((-z2.min(), np.abs(z2).max()))
    nulo = np.array(nulo)
    crit = np.quantile(nulo[:, 0], 0.95)
    poder = []
    for phi in efeitos:
        det, reps = 0, 100
        for _ in range(reps):
            ini = RNG.integers(60)
            alvo = np.isin(b.fase, (ini + np.arange(8)) % 60)
            r = b.residuo(b.y_com_injecao(alvo, phi))
            det += -janelas_fase(b, r, b.fase)[1].min() > crit
        poder.append({"phi": phi, "poder": det / reps})
    return {"z_unilateral": float(obs_uni), "p_unilateral": float((1 + (nulo[:, 0] >= obs_uni).sum()) / (1 + n_perm)),
            "z_bilateral": float(obs_bi), "p_bilateral": float((1 + (nulo[:, 1] >= obs_bi).sum()) / (1 + n_perm)),
            "janela_mais_negativa": {"inicio_s": j, "media_pp": float(m[j] * 100), "z": float(zz[j])},
            "z_critico": float(crit), "poder": poder,
            "perfil": [{"segundo": i, "residuo_pp": float(v * 100)} for i, v in
                       enumerate(np.bincount(b.fase, weights=b.r * b.w, minlength=60) / np.maximum(np.bincount(b.fase, weights=b.w, minlength=60), 1))]}


def espectro_max(b: Bloco, r, passo=10, pmin=30, pmax=1200):
    """Maior potência espectral (relativa à média) do resíduo em votos, por janela de `passo` segundos."""
    t = b.seg // passo
    x = np.bincount(t, weights=r * b.w, minlength=t.max() + 1)
    f = np.fft.rfftfreq(len(x), passo)
    P = np.abs(np.fft.rfft(x - x.mean())) ** 2
    m = (f >= 1 / pmax) & (f <= 1 / pmin)
    i = np.argmax(P[m])
    return float(P[m][i] / P[m].mean()), float(1 / f[m][i]), f[m], P[m] / P[m].mean()


def teste_periodo(b: Bloco, n_perm=1000):
    obs, per, f, P = espectro_max(b, b.r)
    nulo = np.array([espectro_max(b, b.embaralhar_no_local(b.r))[0] for _ in range(n_perm)])
    return {"pico_rel": obs, "periodo_s": per, "p": float((1 + (nulo >= obs).sum()) / (1 + n_perm)),
            "espectro": [{"periodo_s": float(1 / a), "potencia": float(p)} for a, p in zip(f, P)]}


def teste_tendencia(b: Bloco, n_perm=1000):
    t = b.seg / 60.0

    def inc(r):
        tc = t - (np.bincount(b.g, weights=t * b.w, minlength=b.ng) / b.sw)[b.g]
        return float(np.sum(b.w * tc * r) / np.sum(b.w * tc * tc)) if np.sum(b.w * tc * tc) > 0 else 0.0

    obs = inc(b.r)
    nulo = np.array([inc(b.embaralhar_no_local(b.r)) for _ in range(n_perm)])
    return {"pp_por_hora": obs * 60 * 100, "p": float((1 + (np.abs(nulo) >= abs(obs)).sum()) / (1 + n_perm))}


def placebo(d: pl.DataFrame, bloco: int):
    f2, l2, f1, l1 = [d[c].to_numpy().astype(float) for c in ("flavio_2", "lula_2", "flavio_1", "lula_1")]
    n = len(f2) // bloco * bloco
    if n < 3 * bloco:
        return None, None
    s = lambda f, l: f[:n].reshape(-1, bloco).sum(1) / (f + l)[:n].reshape(-1, bloco).sum(1)  # noqa: E731
    c2, c1 = np.cumsum(f2) / np.cumsum(f2 + l2), np.cumsum(f1) / np.cumsum(f1 + l1)
    serie = [{"i": int(i + 1), "t2": float(c2[i]), "t1": float(c1[i])} for i in range(len(f2))]
    return float(np.corrcoef(s(f2, l2), s(f1, l1))[0, 1]), serie


def main():
    d = carregar()
    casos = d.filter(pl.col("caso"))
    resto = d.filter(~pl.col("caso"))
    out = {"secoes_casos": casos.height, "secoes_resto_rj": resto.height,
           "chegada_casos": [str(casos["bu_recebido_2"].min()), str(casos["bu_recebido_2"].max())]}

    for nome, sub in (("casos", casos), ("resto_rj", resto), ("campos", casos.filter(pl.col("municipio") == "Campos dos Goytacazes"))):
        b = Bloco(sub)
        print(nome, sub.height, flush=True)
        out[nome] = {"secoes": sub.height, "locais": b.ng, "fase": teste_fase(b), "periodo": teste_periodo(b),
                     "tendencia": teste_tendencia(b)}

    # placebo de ordem e estagnação, por município
    por_mun, series = [], {}
    for cod, nome in CASOS.items():
        sub = casos.filter(pl.col("municipio") == nome)
        corr, serie = placebo(sub, 10 if sub.height < 200 else 25)
        df = (sub["flavio_2"] - sub["flavio_1"]).to_numpy()
        dl = (sub["lula_2"] - sub["lula_1"]).to_numpy()
        # metade inicial × final da chegada: Flávio estagna em algum trecho?
        h = sub.height // 2
        por_mun.append({"municipio": nome, "secoes": sub.height, "corr_placebo": corr,
                        "delta_f": int(df.sum()), "delta_l": int(dl.sum()),
                        "delta_f_1a_metade": int(df[:h].sum()), "delta_f_2a_metade": int(df[h:].sum()),
                        "secoes_f_caiu": int((df < 0).sum()), "secoes_f_subiu": int((df > 0).sum()),
                        "inicio": str(sub["bu_recebido_2"].min().time()), "fim": str(sub["bu_recebido_2"].max().time())})
        series[nome] = [{"i": int(i + 1), "hora": str(t.time()), "df": int(a), "dl": int(c)}
                        for i, (t, a, c) in enumerate(zip(sub["bu_recebido_2"], np.cumsum(df), np.cumsum(dl)))]
        if nome in ("Campos dos Goytacazes", "Silva Jardim") and serie:
            series[nome + " (placebo)"] = serie
    out["municipios"] = por_mun

    salvar_json("ch06c/municipios", {"meta": meta("Os nove casos na ordem de chegada dos boletins",
                "Correlação 2º × 1º turno por blocos na ordem de chegada; ΔFlávio e ΔLula (votos) por metade da chegada."),
                "dados": por_mun})
    salvar_json("ch06c/series", {"meta": meta("ΔFlávio e ΔLula acumulados na ordem de chegada",
                "Soma acumulada, seção a seção, da variação de votos entre os turnos (mesmas seções)."), "dados": series}, 6)
    rotulos = {"casos": "Os nove casos", "campos": "Campos dos Goytacazes", "resto_rj": "Resto do RJ (comparação)"}
    linhas = []
    for k, rot in rotulos.items():
        t = out[k]
        pw = {x["phi"]: x["poder"] for x in t["fase"]["poder"]}
        linhas += [
            {"grupo": rot, "secoes": t["secoes"], "teste": "Fase do minuto (Flávio penalizado numa janela de 8 s)",
             "efeito": f"{t['fase']['janela_mais_negativa']['media_pp']:+.2f} p.p. (segundos {t['fase']['janela_mais_negativa']['inicio_s']}–{(t['fase']['janela_mais_negativa']['inicio_s'] + 7) % 60})".replace(".", ",", 1),
             "p": t["fase"]["p_unilateral"], "poder_2": pw[0.02], "poder_5": pw[0.05]},
            {"grupo": rot, "secoes": t["secoes"], "teste": "Periodicidade (30 s a 20 min)",
             "efeito": f"pico em {t['periodo']['periodo_s']:.0f} s", "p": t["periodo"]["p"], "poder_2": None, "poder_5": None},
            {"grupo": rot, "secoes": t["secoes"], "teste": "Tendência ao longo da chegada",
             "efeito": f"{t['tendencia']['pp_por_hora']:+.2f} p.p./hora".replace(".", ",", 1), "p": t["tendencia"]["p"], "poder_2": None, "poder_5": None},
        ]
    salvar_json("ch06c/tabela", {"meta": meta("Testes de tempo: resumo",
                "p de permutação (resíduo embaralhado dentro da escola, horários fixos); poder = fração de 100 simulações "
                "em que o teste de fase detecta a injeção de 2% ou 5% dos votos de Flávio numa janela de 8 s."),
                "dados": linhas})
    resumo = {k: v for k, v in out.items()}
    salvar_json("ch06c/testes", {"meta": meta("Testes de tempo nos nove casos e no resto do RJ",
                "Fase do minuto, periodicidade e tendência do resíduo dentro da escola; poder por injeção sintética."),
                "dados": resumo})
    for k, v in out.items():
        if isinstance(v, dict):
            v = {kk: ({a: b for a, b in vv.items() if a not in ("perfil", "espectro")} if isinstance(vv, dict) else vv)
                 for kk, vv in v.items()}
        print(k, v)


if __name__ == "__main__":
    main()
