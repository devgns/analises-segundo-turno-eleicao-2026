"""Capítulo 6 — A prorrogação e as seções tardias.

Separa os relógios (voto do eleitor, encerramento da seção, emissão do BU, recebimento do BU pelo TSE),
reproduz as alegações do relatório que circulou nas redes, conta os votos depois das 17h a partir dos logs, faz o teste de
diferenças em diferenças entre turnos nas MESMAS seções, desenha as curvas de apuração de 2026 (1º e 2º
turnos) e de 2022 (2º turno), procura pausas no recebimento dos BUs e estima a distribuição horária dos votos.

Uso: uv run python analises/06_horarios.py
Saídas: site/public/data/ch06/*.json, data/processed/agregados/cap06_*.parquet (cache), resumo no stdout.

Convenções de relógio (verificadas no próprio script):
  * bweb `dt_abertura/dt_encerramento/dt_emissao_bu` e bu_secao `ts_*`: relógio LOCAL da urna;
  * bweb `dt_bu_recebido`: horário de BRASÍLIA (nunca é anterior à emissão convertida para Brasília);
  * logs: `ts_*` local e `ts_*_brasilia` = local − fuso_brasilia_h.
  O exterior (ZZ, fuso nulo) fica fora das análises de horário.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import CHAVE, PROC, REGIAO, ROOT, bweb, salvar_json, secoes_2026  # noqa: E402

AGG = PROC / "agregados"
LOGS = PROC / "logs_urna" / "eleitores"
SCRIPT = "analises/06_horarios.py"
FONTE_BU = "TSE — boletins de urna (bweb) e logs das urnas, 1º e 2º turnos de 2026"
HOJE = date.today().isoformat()
D2 = date(2026, 10, 25)
D1 = date(2026, 10, 4)
D22 = date(2022, 10, 30)
ORDEM_REG = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]


def dt(d: date, h: int, m: int = 0, s: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m, s)


def gravar(nome: str, dados, titulo: str, descricao: str, fonte: str = FONTE_BU, **extra) -> None:
    if isinstance(dados, pl.DataFrame):
        dados = dados.with_columns(pl.col(pl.Float64, pl.Float32).round(5)).to_dicts()
    obj = {"meta": {"titulo": titulo, "fonte": fonte, "descricao": descricao, "gerado_em": HOJE,
                    "script": SCRIPT, "demo": False}, "dados": dados, **extra}
    p = salvar_json(f"ch06/{nome}", obj, decimais=None)
    print(f"  -> {p.relative_to(ROOT)} ({p.stat().st_size / 1024:.0f} KB)")


def hhmm(col: str | pl.Expr) -> pl.Expr:
    c = pl.col(col) if isinstance(col, str) else col
    return c.dt.strftime("%H:%M")


# ---------------------------------------------------------------------------------------------
# 1. Agregação dos logs por seção (streaming, UF a UF) — fica em cache
# ---------------------------------------------------------------------------------------------

def logs_por_secao(recalcular: bool = False) -> tuple[pl.DataFrame, pl.DataFrame]:
    cache_s = AGG / "cap06_logs_secao.parquet"
    cache_m = AGG / "cap06_logs_minuto_uf.parquet"
    if recalcular or not cache_s.exists() or not cache_m.exists():
        AGG.mkdir(parents=True, exist_ok=True)
        partes_s, partes_m = [], []
        for d in sorted(LOGS.glob("sg_uf=*")):
            uf = d.name.split("=")[1]
            lf = pl.scan_parquet(d / "*.parquet").with_columns(pl.lit(uf).alias("sg_uf"))
            # ZZ não tem fuso: usa o relógio local (horário de cada país)
            t = pl.col("ts_computado") if uf == "ZZ" else pl.col("ts_computado_brasilia")
            lim = lambda h, m=0: t >= dt(D2, h, m)  # noqa: E731
            partes_s.append(
                lf.group_by(CHAVE).agg(
                    pl.len().alias("n_log"),
                    lim(17).sum().alias("n_pos17"),
                    lim(17, 1).sum().alias("n_pos1701"),
                    lim(17, 5).sum().alias("n_pos1705"),
                    lim(17, 10).sum().alias("n_pos1710"),
                    lim(18).sum().alias("n_pos18"),
                    lim(19).sum().alias("n_pos19"),
                    (pl.col("ts_computado") >= dt(D2, 17)).sum().alias("n_pos17_local"),
                    (pl.col("ts_identificador_brasilia") >= dt(D2, 17)).sum().alias("n_ident_pos17")
                    if uf != "ZZ" else pl.lit(0, pl.UInt32).alias("n_ident_pos17"),
                    t.max().alias("ult_voto_b"),
                ).collect(engine="streaming")
            )
            if uf != "ZZ":
                partes_m.append(
                    lf.filter(t >= dt(D2, 15)).group_by(pl.lit(uf).alias("sg_uf"), t.dt.truncate("1m").alias("minuto"))
                    .agg(pl.len().alias("n")).collect(engine="streaming")
                )
            print(f"  logs {uf}: ok")
        pl.concat(partes_s, how="vertical_relaxed").write_parquet(cache_s)
        pl.concat(partes_m).write_parquet(cache_m)
    return pl.read_parquet(cache_s), pl.read_parquet(cache_m)


def logs_minuto_secao(recalcular: bool = False) -> pl.DataFrame:
    """Votos por seção e minuto, só a partir de 16h30 de Brasília (base do estudo de evento)."""
    cache = AGG / "cap06_logs_secao_minuto_pos1630.parquet"
    if recalcular or not cache.exists():
        (
            pl.scan_parquet(LOGS / "*" / "*.parquet", hive_partitioning=True)
            .filter((pl.col("sg_uf") != "ZZ") & (pl.col("ts_computado_brasilia") >= dt(D2, 16, 30)))
            .group_by(*CHAVE, pl.col("ts_computado_brasilia").dt.truncate("1m").alias("minuto"))
            .agg(pl.len().alias("n"))
            .sink_parquet(cache)
        )
    return pl.read_parquet(cache)


# ---------------------------------------------------------------------------------------------
# 2. Tabela base de seções com todos os relógios em Brasília
# ---------------------------------------------------------------------------------------------

def base_secoes(logs: pl.DataFrame) -> pl.DataFrame:
    s = secoes_2026()
    f = pl.duration(hours=pl.col("fuso_brasilia_h").cast(pl.Int64))
    s = s.join(logs.drop("ult_voto_b"), on=CHAVE, how="left").join(
        logs.select(*CHAVE, "ult_voto_b"), on=CHAVE, how="left")
    return s.with_columns(
        (pl.col("encerramento_2") - f).alias("enc2_b"),
        (pl.col("encerramento_1") - f).alias("enc1_b"),
        (pl.col("emissao_bu_2") - f).alias("emis2_b"),
        (pl.col("emissao_bu_1") - f).alias("emis1_b"),
        (pl.col("abertura_2") - f).alias("abert2_b"),
        pl.col("bu_recebido_2").alias("rec2"),
        pl.col("bu_recebido_1").alias("rec1"),
        (pl.col("lula_1") / (pl.col("lula_1") + pl.col("flavio_1"))).alias("s1"),
        (pl.col("lula_2") / (pl.col("lula_2") + pl.col("flavio_2"))).alias("s2"),
        (pl.col("lula_1") + pl.col("flavio_1")).alias("dois_1"),
        (pl.col("lula_2") + pl.col("flavio_2")).alias("dois_2"),
        pl.col("capital").fill_null(False),
    ).with_columns((pl.col("s2") - pl.col("s1")).alias("delta"))


def fatia_flavio(df: pl.DataFrame, t: str = "2") -> float:
    fl, lu = df[f"flavio_{t}"].sum(), df[f"lula_{t}"].sum()
    return fl / (fl + lu) if fl + lu else float("nan")


# ---------------------------------------------------------------------------------------------
# 3. As alegações da conta que circulou
# ---------------------------------------------------------------------------------------------

def reproduzir_alegacoes(s: pl.DataFrame) -> list[dict]:
    """Reproduz cada número do relatório que circulou nas redes testando definições de relógio e de corte."""
    todas = s  # inclui ZZ (a conta que circulou provavelmente usou o bweb inteiro)
    hl = pl.col("encerramento_2").dt.time()
    hb = pl.when(pl.col("sg_uf") == "ZZ").then(pl.col("encerramento_2")).otherwise(pl.col("enc2_b")).dt.time()
    from datetime import time as T
    linhas = []

    def bloco(rotulo, relogio, cond):
        a = todas.filter(cond)
        b = todas.filter(~cond | cond.is_null())
        linhas.append({
            "definicao": rotulo, "relogio": relogio, "secoes": a.height, "comparecimento": int(a["comp_2"].sum()),
            "flavio_2t_ate": fatia_flavio(a), "flavio_1t_mesmas": fatia_flavio(a, "1"),
            "vantagem_lula_demais": int(b["lula_2"].sum() - b["flavio_2"].sum()),
        })

    bloco("Encerradas até 17h00min59s (relógio local, como na conta que circulou)", "local", hl <= T(17, 0, 59))
    bloco("Encerradas até 17h00min00s (relógio local)", "local", hl <= T(17, 0, 0))
    bloco("Encerradas até 17h00min59s (Brasília)", "brasilia", hb <= T(17, 0, 59))
    bloco("Encerradas até 17h05 (Brasília)", "brasilia", hb < T(17, 5))
    faixa = []
    for rot, rel, h in (("local", "local", hl), ("Brasília", "brasilia", hb)):
        m = todas.filter((h >= T(17, 1)) & (h < T(17, 16)))
        faixa.append({"definicao": f"Encerradas entre 17h01 e 17h15 ({rot})", "relogio": rel, "secoes": m.height,
                      "comparecimento": int(m["comp_2"].sum()), "aptos": int(m["aptos_2"].sum())})
        m = todas.filter(h >= T(19, 0))
        faixa.append({"definicao": f"Encerradas a partir de 19h00 ({rot})", "relogio": rel, "secoes": m.height,
                      "comparecimento": int(m["comp_2"].sum()), "aptos": int(m["aptos_2"].sum())})
    return linhas, faixa


def tabela_corte(s: pl.DataFrame) -> pl.DataFrame:
    """Para o interativo: fatia de Flávio (2T e 1T, mesmas seções) nas seções com relógio <= corte."""
    s = s.filter(pl.col("sg_uf") != "ZZ")
    relogios = {
        "enc2_local": ("Encerramento 2º turno, relógio local (conta que circulou)", pl.col("encerramento_2"), D2),
        "enc2_b": ("Encerramento 2º turno, Brasília", pl.col("enc2_b"), D2),
        "ultvoto2_b": ("Último voto do log, Brasília", pl.col("ult_voto_b"), D2),
        "emis2_b": ("Emissão do BU 2º turno, Brasília", pl.col("emis2_b"), D2),
        "rec2": ("Recebimento do BU pelo TSE, 2º turno", pl.col("rec2"), D2),
        "enc1_b": ("Encerramento 1º turno, Brasília", pl.col("enc1_b"), D1),
        "rec1": ("Recebimento do BU pelo TSE, 1º turno", pl.col("rec1"), D1),
    }
    tot = s.select(pl.col("lula_2", "flavio_2", "lula_1", "flavio_1", "comp_2").sum()).row(0, named=True)
    saidas = []
    for chave, (rot, expr, d) in relogios.items():
        g = (
            s.filter(expr.is_not_null())
            .with_columns(((expr - pl.lit(dt(d, 0))).dt.total_minutes()).clip(15 * 60, 24 * 60).alias("m"))
            .group_by("m").agg(pl.len().alias("n"), pl.col("lula_2", "flavio_2", "lula_1", "flavio_1", "comp_2").sum())
            .sort("m")
        )
        grade = pl.DataFrame({"m": np.arange(15 * 60, 24 * 60 + 1, 1, dtype=np.int64)})
        g = grade.join(g, on="m", how="left").fill_null(0).with_columns(
            pl.col("n", "lula_2", "flavio_2", "lula_1", "flavio_1", "comp_2").cum_sum())
        g = g.filter((pl.col("m") % 5 == 0) | (pl.col("m") < 17 * 60 + 30))
        saidas.append(g.select(
            pl.lit(chave).alias("relogio"), pl.lit(rot).alias("rotulo"),
            ((pl.col("m") // 60).cast(pl.Utf8).str.zfill(2) + ":" + (pl.col("m") % 60).cast(pl.Utf8).str.zfill(2)).alias("corte"),
            pl.col("m").alias("minuto_dia"),
            pl.col("n").alias("secoes"),
            pl.col("comp_2").alias("comparecimento"),
            (pl.col("flavio_2") / (pl.col("flavio_2") + pl.col("lula_2"))).alias("flavio_2t"),
            (pl.col("flavio_1") / (pl.col("flavio_1") + pl.col("lula_1"))).alias("flavio_1t"),
            ((tot["lula_2"] - pl.col("lula_2")) - (tot["flavio_2"] - pl.col("flavio_2"))).alias("vantagem_lula_demais"),
        ))
    return pl.concat(saidas)


# ---------------------------------------------------------------------------------------------
# 4. Composição e diferenças em diferenças
# ---------------------------------------------------------------------------------------------

FAIXAS = [(0, 1, "17h00"), (1, 2, "17h01"), (2, 5, "17h02–04"), (5, 10, "17h05–09"), (10, 30, "17h10–29"),
          (30, 60, "17h30–59"), (60, 120, "18h00–59"), (120, 10_000, "19h ou depois")]


def faixa_expr(col: str, d: date) -> pl.Expr:
    m = (pl.col(col) - pl.lit(dt(d, 17))).dt.total_seconds() / 60
    e = pl.lit(None, pl.Utf8)
    for lo, hi, rot in reversed(FAIXAS):
        e = pl.when((m >= lo) & (m < hi)).then(pl.lit(rot)).otherwise(e)
    return pl.when(m < 0).then(pl.lit("antes das 17h")).otherwise(e)


def composicao(s: pl.DataFrame, col: str, d: date) -> pl.DataFrame:
    tot_comp = s["comp_2"].sum()
    g = s.with_columns(faixa_expr(col, d).alias("faixa")).filter(pl.col("faixa").is_not_null()).group_by("faixa").agg(
        pl.len().alias("secoes"),
        pl.col("comp_2").sum().alias("comparecimento"),
        pl.col("aptos_2").mean().alias("aptos_medio"),
        pl.col("capital").mean().alias("frac_capital"),
        *[(pl.col("regiao") == r).mean().alias(f"frac_{r.lower().replace('-', '_')}") for r in ORDEM_REG],
        (pl.col("lula_1").sum() / pl.col("dois_1").sum()).alias("lula_1t"),
        (pl.col("lula_2").sum() / pl.col("dois_2").sum()).alias("lula_2t"),
        (pl.col("comp_2").sum() / pl.col("aptos_2").sum()).alias("comparec_2t"),
        (pl.col("comp_1").sum() / pl.col("aptos_1").sum()).alias("comparec_1t"),
        pl.col("n_pos17").sum().alias("votos_pos17"),
    ).with_columns(
        (pl.col("lula_2t") - pl.col("lula_1t")).alias("delta"),
        (pl.col("comparecimento") / tot_comp).alias("frac_comparecimento"),
    )
    ordem = ["antes das 17h"] + [r for *_, r in FAIXAS]
    return g.with_columns(pl.col("faixa").replace_strict({k: i for i, k in enumerate(ordem)}).alias("_o")).sort("_o").drop("_o")


def did(s: pl.DataFrame, col: str, d: date, rotulo: str, decis: bool = False) -> list[dict]:
    """Δ (Lula 2T − Lula 1T, entre os dois finalistas) por faixa de encerramento, bruto e ajustado.

    Ajuste: efeitos fixos de UF, decis de tamanho (aptos), decis da fatia de Lula no 1º turno, capital.
    Erros-padrão agrupados por município. Peso = votos nos dois finalistas no 2º turno.
    Referência: faixa 17h00 (seções que fecharam no primeiro minuto).
    """
    x = s.filter((pl.col("dois_1") > 0) & (pl.col("dois_2") > 0) & (pl.col("sg_uf") != "ZZ") & pl.col(col).is_not_null())
    if decis:  # décimos da ordem de chegada (rec) em vez de faixas de horário
        x = x.with_columns(("d" + (pl.col(col).rank("ordinal") * 10 // (pl.len() + 1)).cast(pl.Utf8)).alias("faixa"))
    else:
        x = x.with_columns(faixa_expr(col, d).alias("faixa")).filter(
            pl.col("faixa").is_not_null() & (pl.col("faixa") != "antes das 17h"))
    x = x.with_columns(
        pl.col("aptos_2").qcut(10, labels=[f"t{i}" for i in range(10)], allow_duplicates=True).alias("dec_tam"),
        pl.col("s1").qcut(10, labels=[f"s{i}" for i in range(10)], allow_duplicates=True).alias("dec_s1"),
    )
    rotulos = [f"d{i}" for i in range(10)] if decis else [r for *_, r in FAIXAS]
    faixas = [r for r in rotulos if r in x["faixa"].unique().to_list()]
    ref = faixas[0]
    y = x["delta"].to_numpy()
    w = x["dois_2"].to_numpy().astype(float)
    grupos = x.select(pl.concat_str("sg_uf", "cd_municipio_tse")).to_series().cast(pl.Categorical).to_physical().to_numpy()

    def dummies(col, drop):
        v = x[col].cast(pl.Utf8).to_numpy()
        cats = [c for c in sorted(set(v)) if c != drop]
        return np.column_stack([(v == c).astype(float) for c in cats]), cats

    Fb, cats_f = dummies("faixa", ref)
    res = []
    for ajuste in ("bruto", "ajustado"):
        X = [np.ones(len(y)), Fb]
        if ajuste == "ajustado":
            for c, ref_c in (("sg_uf", "SP"), ("dec_tam", "t0"), ("dec_s1", "s0")):
                X.append(dummies(c, ref_c)[0])
            X.append(x["capital"].cast(float).to_numpy()[:, None])
        X = np.column_stack(X)
        m = sm.WLS(y, X, weights=w).fit(cov_type="cluster", cov_kwds={"groups": grupos})
        for i, c in enumerate(cats_f, start=1):
            res.append({"relogio": rotulo, "ajuste": ajuste, "faixa": c, "referencia": ref,
                        "coef": float(m.params[i]), "ep": float(m.bse[i]),
                        "ic_inf": float(m.params[i] - 1.96 * m.bse[i]), "ic_sup": float(m.params[i] + 1.96 * m.bse[i]),
                        "p": float(m.pvalues[i]), "secoes": int((x["faixa"] == c).sum())})
    # Holm dentro de cada (relógio, ajuste)
    for aj in ("bruto", "ajustado"):
        sub = sorted([r for r in res if r["ajuste"] == aj], key=lambda r: r["p"])
        k = len(sub)
        acum = 0.0
        for i, r in enumerate(sub):
            acum = max(acum, min(1.0, (k - i) * r["p"]))
            r["p_holm"] = acum
    return res


def did_dose(s: pl.DataFrame) -> dict:
    """Δ ~ fração dos votos da seção dados após 17h (log) + controles. Dose-resposta da prorrogação."""
    x = s.filter((pl.col("dois_1") > 0) & (pl.col("dois_2") > 0) & (pl.col("sg_uf") != "ZZ")
                 & pl.col("n_log").is_not_null() & (pl.col("n_log") > 0))
    x = x.with_columns(
        (pl.col("n_pos17") / pl.col("n_log")).alias("frac17"),
        (pl.col("n_pos1710") / pl.col("n_log")).alias("frac1710"),
        pl.col("aptos_2").qcut(10, labels=[f"t{i}" for i in range(10)], allow_duplicates=True).alias("dec_tam"),
        pl.col("s1").qcut(10, labels=[f"s{i}" for i in range(10)], allow_duplicates=True).alias("dec_s1"),
    )
    y = x["delta"].to_numpy()
    w = x["dois_2"].to_numpy().astype(float)
    grupos = x.select(pl.concat_str("sg_uf", "cd_municipio_tse")).to_series().cast(pl.Categorical).to_physical().to_numpy()
    out = {}
    for var in ("frac17", "frac1710"):
        cols = [np.ones(len(y)), x[var].to_numpy()]
        for c, ref_c in (("sg_uf", "SP"), ("dec_tam", "t0"), ("dec_s1", "s0")):
            v = x[c].cast(pl.Utf8).to_numpy()
            cols += [(v == k).astype(float) for k in sorted(set(v)) if k != ref_c]
        cols.append(x["capital"].cast(float).to_numpy())
        m = sm.WLS(y, np.column_stack(cols), weights=w).fit(cov_type="cluster", cov_kwds={"groups": grupos})
        out[var] = {"coef": float(m.params[1]), "ep": float(m.bse[1]), "p": float(m.pvalues[1]),
                    "media_var": float(np.average(x[var].to_numpy(), weights=w))}
    return out


def persistencia(s: pl.DataFrame) -> pl.DataFrame:
    """Tabela cruzada: faixa de encerramento no 1º turno × no 2º turno (as seções lentas são as mesmas?)."""
    x = s.filter(pl.col("sg_uf") != "ZZ").with_columns(
        faixa_expr("enc1_b", D1).alias("f1"), faixa_expr("enc2_b", D2).alias("f2"))
    return x.group_by("f1", "f2").agg(pl.len().alias("secoes"), pl.col("delta").mean().alias("delta_medio"))


# ---------------------------------------------------------------------------------------------
# 5. Estudo de evento: minuto do voto (log) × composição das seções
# ---------------------------------------------------------------------------------------------

def estudo_evento(s: pl.DataFrame, lm: pl.DataFrame) -> pl.DataFrame:
    """Por minuto (16h30–19h10, Brasília): votos computados e a fatia de Lula estimada pela seção.

    Δ por minuto = média (ponderada pelos votos do minuto) de s2 − s1 das seções que estavam votando.
    Não é o voto de quem votou naquele minuto (sigilo), é a composição das seções ativas.
    """
    p = s.select(*CHAVE, "s1", "s2", "delta").filter(pl.col("s1").is_not_null() & pl.col("s2").is_not_null())
    g = (
        lm.join(p, on=CHAVE, how="inner")
        .filter(pl.col("minuto") < dt(D2, 19, 10))
        .group_by("minuto").agg(
            pl.col("n").sum().alias("votos"),
            ((pl.col("n") * pl.col("s2")).sum() / pl.col("n").sum()).alias("lula_2t_est"),
            ((pl.col("n") * pl.col("s1")).sum() / pl.col("n").sum()).alias("lula_1t_mesmas"),
            pl.col("secao").n_unique().alias("secoes_ativas_aprox"),
        ).sort("minuto")
    )
    return g.with_columns((pl.col("lula_2t_est") - pl.col("lula_1t_mesmas")).alias("delta"), hhmm("minuto").alias("hora")).drop("minuto")


# ---------------------------------------------------------------------------------------------
# 6. Curvas de apuração e pausas
# ---------------------------------------------------------------------------------------------

def curva(df: pl.DataFrame, tcol: str, a: str, b: str, d: date, rotulo: str) -> tuple[pl.DataFrame, dict]:
    x = df.filter(pl.col(tcol).is_not_null()).sort(tcol)
    tot_sec = x.height
    g = x.group_by(pl.col(tcol).dt.truncate("1m").alias("t")).agg(
        pl.len().alias("bus"), pl.col(a).sum().alias("a"), pl.col(b).sum().alias("b")).sort("t")
    g = g.with_columns(pl.col("bus").cum_sum().alias("bus_acum"), pl.col("a").cum_sum().alias("a_acum"),
                       pl.col("b").cum_sum().alias("b_acum"))
    g = g.with_columns((pl.col("a_acum") - pl.col("b_acum")).alias("dif"),
                       (pl.col("bus_acum") / tot_sec).alias("frac_secoes"),
                       (pl.col("a_acum") / (pl.col("a_acum") + pl.col("b_acum"))).alias("lula_acum"),
                       ((pl.col("t") - pl.lit(dt(d, 0))).dt.total_minutes()).alias("minuto_dia"))
    # virada definitiva = último minuto em que o sinal da diferença muda
    sinal = g["dif"].sign().to_list()
    virada = None
    for i in range(1, len(sinal)):
        if sinal[i] != sinal[i - 1] and sinal[i] != 0:
            virada = i
    info = {"eleicao": rotulo, "bus": tot_sec, "bus_antes_17h": int(x.filter(pl.col(tcol) < dt(d, 17)).height),
            "primeiro": str(g["t"][0].time()), "ultimo": str(x[tcol][-1].time()),
            "virada_hora": str(g["t"][virada].time())[:5] if virada is not None else None,
            "virada_frac_secoes": float(g["frac_secoes"][virada]) if virada is not None else None,
            "dif_max_contra_lula": int(g["dif"].min())}
    # pausas: minutos sem nenhum BU entre o primeiro e o último recebimento
    # só a partir das 17h00 do dia (há poucos BUs com horário espúrio de madrugada, ex. 2022 01h20)
    ini = max(g["t"][0], dt(d, 17))
    full = pl.DataFrame({"t": pl.datetime_range(ini, g["t"][-1], "1m", eager=True)})
    z = full.join(g.select("t", "bus"), on="t", how="left").with_columns(pl.col("bus").fill_null(0))
    z = z.with_columns((pl.col("bus") > 0).cum_sum().alias("grp"))
    pausas = z.filter(pl.col("bus") == 0).group_by("grp").agg(pl.col("t").min().alias("inicio"), pl.len().alias("minutos"))
    pausas = pausas.sort("minutos", descending=True)
    info["pausas"] = [{"inicio": str(r["inicio"].time())[:5], "minutos": int(r["minutos"])} for r in pausas.head(5).iter_rows(named=True)]
    # composição por decil da ordem de chegada
    x = x.with_columns((pl.int_range(pl.len()) * 10 // pl.len()).alias("decil"))
    return g.with_columns(pl.lit(rotulo).alias("eleicao")), info, x


def curvas_apuracao(s: pl.DataFrame) -> tuple[pl.DataFrame, list[dict], pl.DataFrame, pl.DataFrame]:
    s_all = secoes_2026()
    c2, i2, x2 = curva(s_all.filter(pl.col("lula_2").is_not_null()), "bu_recebido_2", "lula_2", "flavio_2", D2, "2026 · 2º turno")
    c1, i1, x1 = curva(s_all.filter(pl.col("lula_1").is_not_null()), "bu_recebido_1", "lula_1", "flavio_1", D1, "2026 · 1º turno")
    # 2022: o cache compartilhado tem as datas nulas (formato dd/mm/aaaa); usa o extrato do 06b_bweb2022_recebido.py
    p22 = AGG / "cap06_bweb2022_t2.parquet"
    if not p22.exists():
        raise SystemExit("Rode antes: uv run python analises/06b_bweb2022_recebido.py --turno 2")
    b22 = pl.read_parquet(p22).select("dt_bu_recebido", pl.col("votos_13").fill_null(0).alias("lula"),
                                       pl.col("votos_22").fill_null(0).alias("bolsonaro"))
    c22, i22, x22 = curva(b22, "dt_bu_recebido", "lula", "bolsonaro", D22, "2022 · 2º turno")
    curvas = pl.concat([c.select("eleicao", "minuto_dia", "bus", "bus_acum", "frac_secoes", "dif", "lula_acum")
                        for c in (c2, c1, c22)])
    # chegadas por minuto (detectar pausa)
    chegadas = curvas.select("eleicao", "minuto_dia", "bus")

    # decis de chegada: fatia de Lula entre os finalistas em cada décimo dos BUs, por ordem de chegada
    dec = []
    for x, a, b, rot in ((x2, "lula_2", "flavio_2", "2026 · 2º turno"), (x1, "lula_1", "flavio_1", "2026 · 1º turno"),
                         (x22, "lula", "bolsonaro", "2022 · 2º turno")):
        dd = x.group_by("decil").agg((pl.col(a).sum() / (pl.col(a).sum() + pl.col(b).sum())).alias("lula"),
                                     pl.len().alias("bus")).sort("decil")
        dec.append(dd.with_columns(pl.lit(rot).alias("serie")))
    # as MESMAS seções do 2T de 2026, na ordem de chegada do 2T, com a fatia do 1T
    x2b = x2.filter(pl.col("lula_1").is_not_null())
    dd = x2b.group_by("decil").agg((pl.col("lula_1").sum() / (pl.col("lula_1").sum() + pl.col("flavio_1").sum())).alias("lula"),
                                   pl.len().alias("bus")).sort("decil")
    dec.append(dd.with_columns(pl.lit("2026 · mesmas seções do 2º turno, votação do 1º turno").alias("serie")))
    decis = pl.concat(dec).select("serie", "decil", "lula", "bus")
    return curvas, [i2, i1, i22], chegadas, decis


def evento_recebimento(s: pl.DataFrame) -> pl.DataFrame:
    """Δ (2T − 1T) por janela de 10 min de recebimento do BU no 2º turno, mesmas seções."""
    x = s.filter(pl.col("rec2").is_not_null() & (pl.col("dois_1") > 0))
    return (
        x.group_by(pl.col("rec2").dt.truncate("10m").alias("t")).agg(
            pl.len().alias("bus"),
            (pl.col("lula_2").sum() / pl.col("dois_2").sum()).alias("lula_2t"),
            (pl.col("lula_1").sum() / pl.col("dois_1").sum()).alias("lula_1t"),
        ).sort("t").with_columns((pl.col("lula_2t") - pl.col("lula_1t")).alias("delta"), hhmm("t").alias("hora")).drop("t")
    )


# ---------------------------------------------------------------------------------------------
# 7. Distribuição horária estimada (log × proporção da seção)
# ---------------------------------------------------------------------------------------------

def distribuicao_horaria(s: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    slots = pl.read_parquet(AGG / "votos_secao_slot20.parquet")
    p = s.select(*CHAVE, "regiao", "s2", "s1", "comp_2", "lula_2", "flavio_2", "brancos_2", "nulos_2")
    p = p.with_columns(*[(pl.col(c) / pl.col("comp_2")).alias(f"p_{c}") for c in ("lula_2", "flavio_2", "brancos_2", "nulos_2")])
    j = slots.join(p, on=CHAVE, how="inner").filter(pl.col("regiao").is_in(ORDEM_REG))
    nac = j.group_by("slot").agg(
        pl.col("n").sum().alias("votos"),
        *[(pl.col("n") * pl.col(f"p_{c}")).sum().alias(c.replace("_2", "")) for c in ("lula_2", "flavio_2", "brancos_2", "nulos_2")],
        ((pl.col("n") * pl.col("s1")).sum() / pl.col("n").sum()).alias("lula_1t_mesmas"),
    ).sort("slot").with_columns(
        (pl.col("lula") / (pl.col("lula") + pl.col("flavio"))).alias("lula_est"), hhmm("slot").alias("hora")).drop("slot")
    hr = j.with_columns(pl.col("slot").dt.hour().alias("h")).group_by("regiao", "h").agg(
        pl.col("n").sum().alias("votos"),
        ((pl.col("n") * pl.col("p_lula_2")).sum() / (pl.col("n") * (pl.col("p_lula_2") + pl.col("p_flavio_2"))).sum()).alias("lula_est"),
        ((pl.col("n") * pl.col("s1")).sum() / pl.col("n").sum()).alias("lula_1t_mesmas"),
    )
    hr = hr.with_columns((pl.col("votos") / pl.col("votos").sum().over("regiao")).alias("frac_regiao"),
                         (pl.col("lula_est") - pl.col("lula_1t_mesmas")).alias("delta")).sort("regiao", "h")
    return nac, hr


# ---------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------

def main() -> None:
    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(220)
    print("1) logs por seção")
    logs, lm_uf = logs_por_secao()
    s = base_secoes(logs)
    sbr = s.filter((pl.col("sg_uf") != "ZZ") & pl.col("pareada"))

    # --- conferências de relógio ---------------------------------------------------------
    chk = sbr.select(
        ((pl.col("rec2") - pl.col("emis2_b")).dt.total_seconds() < 0).sum().alias("rec_antes_emissao_2t"),
        ((pl.col("rec1") - pl.col("emis1_b")).dt.total_seconds() < 0).sum().alias("rec_antes_emissao_1t"),
        pl.col("enc2_b").min().alias("enc2_b_min"), pl.col("enc1_b").min().alias("enc1_b_min"),
        (pl.col("enc2_b") < dt(D2, 17)).sum().alias("enc2_antes_17"), (pl.col("enc1_b") < dt(D1, 17)).sum().alias("enc1_antes_17"),
    )
    print(chk)

    # --- relógios: resumo ---------------------------------------------------------------
    rel = []
    for rot, col, d in (("Último voto (log), 2º turno", "ult_voto_b", D2), ("Encerramento, 2º turno", "enc2_b", D2),
                        ("Emissão do BU, 2º turno", "emis2_b", D2), ("Recebimento do BU pelo TSE, 2º turno", "rec2", D2),
                        ("Encerramento, 1º turno", "enc1_b", D1), ("Emissão do BU, 1º turno", "emis1_b", D1),
                        ("Recebimento do BU pelo TSE, 1º turno", "rec1", D1)):
        v = sbr.select(((pl.col(col) - pl.lit(dt(d, 17))).dt.total_seconds() / 60).alias("m")).drop_nulls()["m"]
        rel.append({"relogio": rot, "turno": 2 if d == D2 else 1, "secoes": v.len(),
                    **{f"p{q}": float(v.quantile(q / 100)) for q in (1, 10, 25, 50, 75, 90, 99)},
                    "max": float(v.max()), "frac_ate_1701": float((v < 1).mean()), "frac_ate_1710": float((v < 10).mean()),
                    "frac_apos_19": float((v >= 120).mean())})
    rel = pl.DataFrame(rel)
    print(rel)
    gravar("relogios-resumo", rel, "Os quatro relógios: minutos depois das 17h de Brasília",
           "Quantis, em minutos após 17h00 (Brasília), de cada relógio por seção. Negativo = antes das 17h.")

    # histograma por minuto (15h–24h) de cada relógio — para o gráfico de distribuição
    hist = []
    for chave, col, d in (("ult_voto_b", "ult_voto_b", D2), ("enc2_b", "enc2_b", D2), ("emis2_b", "emis2_b", D2),
                          ("rec2", "rec2", D2), ("enc1_b", "enc1_b", D1), ("rec1", "rec1", D1)):
        h = (sbr.select(((pl.col(col) - pl.lit(dt(d, 0))).dt.total_minutes()).alias("m")).drop_nulls()
             .with_columns((pl.col("m") // 5 * 5).clip(15 * 60, 24 * 60).alias("m")).group_by("m").len().sort("m"))
        hist.append(h.with_columns(pl.lit(chave).alias("relogio")))
    hist = pl.concat(hist).rename({"len": "secoes", "m": "minuto_dia"}).select("relogio", "minuto_dia", "secoes")
    gravar("relogios-histograma", hist, "Seções por horário de cada relógio (janelas de 5 min, Brasília)",
           "Contagem de seções por janela de 5 minutos. Valores fora de 15h–24h foram presos nas pontas.")

    # --- 2. votos depois das 17h ------------------------------------------------------------
    print("2) votos após 17h")
    tot = s.select(pl.col("n_log", "n_pos17", "n_pos1701", "n_pos1705", "n_pos1710", "n_pos18", "n_pos19",
                          "n_ident_pos17").sum())
    tot_br = sbr.select(pl.col("n_log", "n_pos17", "n_pos1705", "n_pos1710", "n_pos18", "n_pos19", "n_ident_pos17", "n_pos17_local").sum())
    zz = s.filter(pl.col("sg_uf") == "ZZ").select(pl.col("n_pos17").sum()).item()
    print(tot_br, "ZZ (hora local) após 17h:", zz)
    sec_tardias = sbr.filter(pl.col("n_pos17") > 0)
    pos = sec_tardias.select(
        pl.len().alias("secoes"),
        (pl.col("n_pos1710") > 0).sum().alias("secoes_pos1710"),
        (pl.col("n_pos18") > 0).sum().alias("secoes_pos18"),
        pl.col("lula_1").sum() / pl.col("dois_1").sum(),
        (pl.col("lula_2").sum() / pl.col("dois_2").sum()).alias("lula_2t"),
        ((pl.col("n_pos17") * pl.col("s2")).sum() / pl.col("n_pos17").sum()).alias("lula_2t_ponderado_pos17"),
        ((pl.col("n_pos17") * pl.col("s1")).sum() / pl.col("n_pos17").sum()).alias("lula_1t_ponderado_pos17"),
    ).rename({"lula_1": "lula_1t"})
    resto = sbr.filter(pl.col("n_pos17").fill_null(0) == 0).select(
        (pl.col("lula_1").sum() / pl.col("dois_1").sum()).alias("lula_1t"), (pl.col("lula_2").sum() / pl.col("dois_2").sum()).alias("lula_2t"))
    print(pos, resto)
    por_uf = sbr.group_by("sg_uf", "regiao").agg(
        pl.col("n_pos17").sum().alias("votos_pos17"), pl.col("n_pos1710").sum().alias("votos_pos1710"),
        pl.col("n_pos18").sum().alias("votos_pos18"),
        (pl.col("n_pos17") > 0).sum().alias("secoes_com_voto_pos17"), pl.len().alias("secoes"),
        pl.col("n_log").sum().alias("votos_log"),
        (pl.col("lula_1").sum() / pl.col("dois_1").sum()).alias("lula_1t"),
        (pl.col("lula_2").sum() / pl.col("dois_2").sum()).alias("lula_2t"),
        ((pl.col("n_pos17") * pl.col("s2")).sum() / pl.col("n_pos17").sum()).alias("lula_2t_secoes_tardias"),
        ((pl.col("n_pos17") * pl.col("s1")).sum() / pl.col("n_pos17").sum()).alias("lula_1t_secoes_tardias"),
    ).with_columns((pl.col("votos_pos17") / pl.col("votos_log")).alias("frac_pos17")).sort("votos_pos17", descending=True)
    gravar("pos17-uf", por_uf, "Votos computados a partir das 17h00 de Brasília, por UF",
           "Contagem a partir do log de cada urna (ts_computado_brasilia ≥ 17:00:00). Fatias de Lula entre os dois "
           "finalistas; 'seções tardias' = ponderadas pelo nº de votos pós-17h da seção.")
    por_mun = sbr.group_by("sg_uf", "nm_municipio", "cd_municipio_ibge").agg(
        pl.col("n_pos17").sum().alias("votos_pos17"), (pl.col("n_pos17") > 0).sum().alias("secoes_com_voto_pos17"),
        pl.col("n_log").sum().alias("votos_log"),
        ((pl.col("n_pos17") * pl.col("s2")).sum() / pl.col("n_pos17").sum()).alias("lula_2t_secoes_tardias"),
        ((pl.col("n_pos17") * pl.col("s1")).sum() / pl.col("n_pos17").sum()).alias("lula_1t_secoes_tardias"),
    ).filter(pl.col("votos_pos17") > 0).sort("votos_pos17", descending=True)
    print(por_mun.head(15))
    gravar("pos17-municipios", por_mun.head(300), "Municípios com mais votos computados depois das 17h (Brasília)",
           "Top 300 municípios por votos pós-17h no log das urnas.")
    top_sec = sbr.filter(pl.col("n_pos17") > 0).sort("n_pos17", descending=True).head(40).select(
        "sg_uf", "nm_municipio", "zona", "secao", "n_log", "n_pos17", "n_pos18", hhmm("ult_voto_b").alias("ultimo_voto"),
        hhmm("enc2_b").alias("encerramento"), hhmm("rec2").alias("recebido"), "s1", "s2", "delta")
    print(top_sec.head(15))
    gravar("pos17-secoes-top", top_sec, "Seções com mais votos depois das 17h", "Top 40 seções por votos pós-17h.")

    kpis_votos = {
        "votos_pos17": int(tot_br["n_pos17"][0]), "votos_pos1705": int(tot_br["n_pos1705"][0]),
        "votos_pos1710": int(tot_br["n_pos1710"][0]), "votos_pos18": int(tot_br["n_pos18"][0]),
        "votos_pos19": int(tot_br["n_pos19"][0]), "votos_ident_pos17": int(tot_br["n_ident_pos17"][0]),
        "votos_log": int(tot_br["n_log"][0]), "zz_pos17_local": int(zz),
        "secoes_com_voto_pos17": int(pos["secoes"][0]), "secoes_com_voto_pos1710": int(pos["secoes_pos1710"][0]),
        "secoes_com_voto_pos18": int(pos["secoes_pos18"][0]),
        "lula_1t_secoes_tardias": float(pos["lula_1t"][0]), "lula_2t_secoes_tardias": float(pos["lula_2t"][0]),
        "lula_1t_demais": float(resto["lula_1t"][0]), "lula_2t_demais": float(resto["lula_2t"][0]),
    }

    # --- 3. alegações da conta que circulou ----------------------------------------------------------------
    print("3) alegações da conta que circulou")
    alg, faixa = reproduzir_alegacoes(s)
    print(pl.DataFrame(alg)); print(pl.DataFrame(faixa))
    gravar("alegacoes-circulantes", alg, "As alegações da conta que circulou nas redes refeitas com cada relógio",
           "Fatia de Flávio entre os dois finalistas nas seções encerradas até o corte; 'flavio_1t_mesmas' = mesma conta "
           "no 1º turno, nas mesmas seções.", faixas=faixa)
    corte = tabela_corte(s)
    gravar("corte-interativo", corte, "Fatia de Flávio nas seções 'fechadas até X' — por relógio e corte",
           "Cumulativo: seções cujo relógio escolhido marca até o minuto do corte (Brasília). Inclui a mesma conta no "
           "1º turno para as mesmas seções.")

    # --- 4. composição + DiD -------------------------------------------------------------------
    print("4) composição e DiD")
    comp2 = composicao(sbr, "enc2_b", D2)
    comp1 = composicao(sbr, "enc1_b", D1)
    print(comp2); print(comp1)
    gravar("composicao-enc2", comp2, "Perfil das seções por faixa de encerramento no 2º turno (Brasília)",
           "Tamanho, capital, região, fatia de Lula (entre os finalistas) nos dois turnos e Δ, por faixa de encerramento.")
    gravar("composicao-enc1", comp1, "Perfil das seções por faixa de encerramento no 1º turno (Brasília)",
           "Mesma tabela, classificando as seções pelo encerramento do 1º turno.")
    res = (did(sbr, "enc2_b", D2, "Encerramento no 2º turno") + did(sbr, "enc1_b", D1, "Encerramento no 1º turno")
           + did(sbr, "rec2", D2, "Décimo de chegada do BU no 2º turno", decis=True)
           + did(sbr, "rec1", D1, "Décimo de chegada do BU no 1º turno", decis=True))
    res = pl.DataFrame(res)
    print(res)
    gravar("did-faixas", res, "Diferenças em diferenças: Δ Lula (2T − 1T) por faixa de encerramento, vs. seções que "
           "fecharam às 17h00", "Coeficiente (fração) de cada faixa relativo à faixa 17h00. Bruto = sem controles; "
           "ajustado = efeitos fixos de UF, decis de tamanho e de fatia de Lula no 1T, capital. EP agrupado por município. "
           "p_holm = correção de Holm entre as faixas.")
    dose = did_dose(sbr)
    print("dose", dose)
    pers = persistencia(s)
    gravar("persistencia", pers, "Faixa de encerramento no 1º × 2º turno",
           "Número de seções em cada combinação de faixas de encerramento (Brasília) e Δ médio simples.")

    # --- 5. estudo de evento ------------------------------------------------------------------
    print("5) estudo de evento")
    lm = logs_minuto_secao()
    ev = estudo_evento(s, lm)
    print(ev.filter(pl.col("hora").is_between(pl.lit("16:55"), pl.lit("17:15"))))
    gravar("evento-minuto", ev, "Votos por minuto e composição das seções ativas, 16h30–19h10 (Brasília)",
           "Votos do log por minuto; fatia de Lula ESTIMADA pela proporção da seção (2T) e a mesma conta com o 1T. "
           "Δ = diferença entre as duas. Não revela o voto de quem votou naquele minuto.")
    ev_rec = evento_recebimento(s)
    gravar("evento-recebimento", ev_rec, "Δ Lula (2T − 1T) por janela de recebimento do BU no 2º turno",
           "Seções agrupadas pela janela de 10 minutos em que o TSE recebeu o BU do 2º turno.")

    # --- 6. curvas de apuração ---------------------------------------------------------------
    print("6) curvas de apuração")
    curvas, infos, chegadas, decis = curvas_apuracao(s)
    for i in infos:
        print(i)
    cur_site = curvas.filter((pl.col("minuto_dia") % 2 == 0) | (pl.col("minuto_dia") < 20 * 60))
    gravar("curvas-apuracao", cur_site.select("eleicao", "minuto_dia", "frac_secoes", "dif", "lula_acum"),
           "Curva da apuração: diferença acumulada Lula − adversário pela hora de recebimento do BU (Brasília)",
           "Uma linha por minuto (a cada 2 min após 20h). 'dif' = votos de Lula − votos do adversário acumulados.",
           fonte="TSE — bweb (DT_BU_RECEBIDO), 2022 e 2026", infos=infos)
    gravar("chegadas-minuto", chegadas.filter(pl.col("eleicao").str.contains("2026") | (pl.col("eleicao") == "2022 · 2º turno")),
           "BUs recebidos por minuto pelo TSE", "Número de BUs recebidos em cada minuto (Brasília).",
           fonte="TSE — bweb (DT_BU_RECEBIDO), 2022 e 2026")
    gravar("decis-chegada", decis, "Fatia de Lula por décimo da ordem de chegada dos BUs",
           "Decil 0 = primeiros 10% de BUs recebidos; 9 = últimos 10%.", fonte="TSE — bweb, 2022 e 2026")
    print(decis)

    # --- 7. distribuição horária ---------------------------------------------------------------
    print("7) distribuição horária")
    nac, hr = distribuicao_horaria(sbr)
    gravar("horario-nacional", nac, "Votos por faixa de 20 minutos (Brasília) e divisão ESTIMADA por candidato",
           "Total = log das urnas. Divisão por candidato = proporção da seção aplicada a cada voto (estimativa).")
    gravar("horario-regiao", hr, "Distribuição dos votos por hora e região (Brasília)",
           "frac_regiao = parcela dos votos da região dada naquela hora; lula_est = fatia estimada de Lula.")

    # --- KPIs ---------------------------------------------------------------------------------
    alg0 = alg[0]
    alg2 = alg[2]
    kpis = [
        {"rotulo": "Votos computados a partir das 17h (Brasília), pelos logs", "valor": kpis_votos["votos_pos17"], "formato": "num"},
        {"rotulo": "Número divulgado pelo TSE", "valor": 34393, "formato": "num"},
        {"rotulo": "Votos a partir das 17h10, quando a prorrogação poderia ter efeito", "valor": kpis_votos["votos_pos1710"], "formato": "num"},
        {"rotulo": "Fatia de Flávio 'até 17h' só com o relógio local (conta que circulou)", "valor": alg0["flavio_2t_ate"], "formato": "pct"},
        {"rotulo": "A mesma conta, com horário de Brasília", "valor": alg2["flavio_2t_ate"], "formato": "pct"},
        {"rotulo": "Margem final de Lula", "valor": 64256232 - 59826041, "formato": "num"},
    ]
    salvar_json("ch06/kpis", kpis, decimais=None)
    gravar("resumo", [{**kpis_votos, **{f"dose_{k}_{kk}": vv for k, v in dose.items() for kk, vv in v.items()}}],
           "Números-chave do capítulo 6", "Resumo usado no texto.")
    print("KPIs:", kpis_votos)


if __name__ == "__main__":
    main()
