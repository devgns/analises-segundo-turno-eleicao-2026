"""Cap. 6b: o "serrote" da totalização (vídeo do prof. Marcelo Trindade).

Alegação: na curva do percentual acumulado de Bolsonaro ao longo da totalização de 2022 há "vales"
igualmente espaçados, um "algoritmo que liga e desliga" penalizando o candidato; e uma única "virada",
quando o esperado seriam várias.

Fontes:
    data/raw/externo/historico_totalizacao/  Histórico de totalização Presidente BR 1T/2T 2022 (TSE, CKAN resultados-2022)
    bweb 2022 (1º e 2º turnos, mesmas seções) e secoes_2026()

Testes:
    1. Reprodução exata dos pontos mostrados no vídeo.
    2. Periodicidade: espectro do desvio dos incrementos (2T e 1T de 2022).
    3. Assinatura dos lotes dos "vales": comparecimento, brancos+nulos e aptos por seção (não mudam se votos
       forem trocados de candidato) comparados aos perfis regionais.
    4. Placebo: as mesmas seções, na ordem de chegada do 2º turno, com os votos do 1º turno.
    5. Teste de fase (com poder): as seções que chegam numa mesma fase do minuto têm variação 1T→2T diferente
       das vizinhas do mesmo município? Permutação dentro do município + injeção sintética do "algoritmo".
    6. Viradas: série real × 3.000 ordens aleatórias; composição regional ao longo da contagem.

Rode: uv run python analises/06b_serrote_totalizacao.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import REGIAO, ROOT, salvar_json, secoes_2026  # noqa: E402

HIST = ROOT / "data" / "raw" / "externo" / "historico_totalizacao"
URL_HIST = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2022/Historico_Totalizacao_Presidente_BR_{t}_2022.zip"
CHAVE = ["sg_uf", "cd_municipio_tse", "zona", "secao"]
RNG = np.random.default_rng(2026)
GERADO = datetime.now().strftime("%Y-%m-%d")
FONTE_HIST = "TSE: Histórico de totalização Presidente BR, 2022 (dados abertos)"


def meta(titulo, descricao, fonte=FONTE_HIST):
    return {"titulo": titulo, "fonte": fonte, "descricao": descricao, "gerado_em": GERADO,
            "script": "analises/06b_serrote_totalizacao.py"}


# ---------------------------------------------------------------- histórico de totalização
def baixar_hist(t: str) -> Path:
    csv = HIST / f"Historico_Totalizacao_Presidente_BR_{t}_2022" / f"Historico_Totalizacao_Presidente_BR_{t}_2022.csv"
    if not csv.exists():
        import io, urllib.request, zipfile  # noqa: E401
        req = urllib.request.Request(URL_HIST.format(t=t), headers={"User-Agent": "Mozilla/5.0 (analise-eleicao-2026)"})
        with urllib.request.urlopen(req) as r:
            zipfile.ZipFile(io.BytesIO(r.read())).extractall(csv.parent)
    return csv


def hist(t: str) -> pl.DataFrame:
    d = pl.read_csv(baixar_hist(t), separator=";", infer_schema_length=0)
    d = d.rename({c: c.strip() for c in d.columns}).with_columns(pl.all().str.strip_chars())
    qt = [c for c in d.columns if "_QT_" in c or c.startswith("QT_")]
    pe = [c for c in d.columns if "_PE_" in c or c.startswith("PE_")]
    return (
        d.with_columns(pl.col(qt).cast(pl.Int64), pl.col(pe).str.replace(",", ".").cast(pl.Float64),
                       t=pl.col("DT_TOTALIZACAO").str.to_datetime("%d/%m/%Y %H:%M:%S"))
        .sort("t")
        .with_columns(
            secoes=pl.col("QT_SECOES_TOT_ACUMULADO"),
            pe_b=pl.col("JAIR_BOLSONARO_PE_VOTOS_TOT_ACUMULADO"),
            inc_b=pl.col("JAIR_BOLSONARO_QT_VOTOS_TOT") / (pl.col("JAIR_BOLSONARO_QT_VOTOS_TOT") + pl.col("LULA_QT_VOTOS_TOT")),
        )
    )


def espectro(h: pl.DataFrame, ate_hora: int = 19):
    """Desvio por segundo do incremento (votos B − metade dos votos B+L), sem a tendência de 5 min."""
    t0 = h["t"][0]
    s = h.filter(pl.col("t").dt.hour() < ate_hora).with_columns(seg=(pl.col("t") - t0).dt.total_seconds())
    T = int(s["seg"].max()) + 1
    x = np.zeros(T)
    v = (s["JAIR_BOLSONARO_QT_VOTOS_TOT"] - 0.5 * (s["JAIR_BOLSONARO_QT_VOTOS_TOT"] + s["LULA_QT_VOTOS_TOT"])).to_numpy()
    np.add.at(x, s["seg"].to_numpy(), v)
    x = x - np.convolve(x, np.ones(301) / 301, "same")
    f = np.fft.rfftfreq(T, 1)
    P = np.abs(np.fft.rfft(x)) ** 2
    m = (f > 1 / 300) & (f < 1 / 10)
    per, pot = 1 / f[m], P[m] / np.median(P[m])
    top = np.argsort(pot)[::-1]
    picos = []
    for i in top:  # picos distintos (≥ 5% de distância)
        if all(abs(per[i] - p) / p > 0.05 for p, _ in picos):
            picos.append((float(per[i]), float(pot[i])))
        if len(picos) == 5:
            break
    # reamostra para o site: média de potência por faixa de período (log)
    bins = np.geomspace(10, 300, 120)
    idx = np.digitize(per, bins)
    serie = [{"periodo_s": float(np.sqrt(bins[k - 1] * bins[k])), "potencia": float(pot[idx == k].max())}
             for k in range(1, len(bins)) if (idx == k).any()]
    return picos, serie


# ---------------------------------------------------------------- seções
def bweb22() -> pl.DataFrame:
    def ld(t, **cols):
        return pl.scan_parquet(ROOT / f"data/processed/bweb_secao/ano=2022/turno={t}/**/*.parquet", hive_partitioning=True
                               ).select(*CHAVE, **cols)
    t2 = ld(2, local=pl.col("nr_local_votacao"), recebido=pl.col("dt_bu_recebido"), b2=pl.col("votos_22"), l2=pl.col("votos_13"),
            aptos=pl.col("qt_aptos"), comp=pl.col("qt_comparecimento"),
            bn=pl.col("votos_brancos") + pl.col("votos_nulos")).collect()
    t1 = ld(1, b1=pl.col("votos_22"), l1=pl.col("votos_13")).collect()
    return t2.join(t1, on=CHAVE, how="inner").with_columns(regiao=pl.col("sg_uf").replace_strict(REGIAO))


def secoes26() -> pl.DataFrame:
    return secoes_2026().filter(pl.col("pareada")).select(
        *CHAVE, local=pl.col("local"), recebido=pl.col("bu_recebido_2"), b2=pl.col("flavio_2"), l2=pl.col("lula_2"),
        b1=pl.col("flavio_1"), l1=pl.col("lula_1"), regiao=pl.col("regiao"))


def ordenar(d: pl.DataFrame) -> pl.DataFrame:
    return d.sort(["recebido", *CHAVE])


def placebo(d: pl.DataFrame, janela: tuple[int, int], bloco: int = 150):
    """Correlação entre a fatia de B por bloco de chegada no 2T e a fatia das mesmas seções no 1T."""
    b2, l2, b1, l1 = [d[c].to_numpy().astype(float) for c in ("b2", "l2", "b1", "l1")]
    n = len(b2) // bloco * bloco
    f = lambda b, l: b[:n].reshape(-1, bloco).sum(1) / (b + l)[:n].reshape(-1, bloco).sum(1)  # noqa: E731
    s2, s1 = f(b2, l2), f(b1, l1)
    w = slice(janela[0] // bloco, janela[1] // bloco)
    c2 = np.cumsum(b2) / np.cumsum(b2 + l2)
    c1 = np.cumsum(b1) / np.cumsum(b1 + l1)
    x = np.arange(*janela, 50)
    serie = [{"secoes": int(i), "t2": float(c2[i] - c2[janela[0]]), "t1": float(c1[i] - c1[janela[0]])} for i in x]
    return {"corr_blocos": float(np.corrcoef(s2, s1)[0, 1]), "corr_janela": float(np.corrcoef(s2[w], s1[w])[0, 1]),
            "r2": float(np.corrcoef(s2, s1)[0, 1] ** 2), "bloco": bloco, "n_blocos": int(len(s2))}, serie


# ---------------------------------------------------------------- teste de fase com poder
def teste_fase(d: pl.DataFrame, n_perm: int = 400, janela_fase: int = 8, efeitos=(0.005, 0.01, 0.02, 0.05), periodo: int = 60):
    """Resíduo da variação 1T→2T (fatia de B entre B e L), descontada a média do local de votação, por segundo do
    minuto em que o BU chegou. H0: a fase não importa.
    Estatísticas sobre as médias ponderadas em janelas circulares de `janela_fase` segundos:
      escore z por janela (soma ponderada / erro-padrão); bilateral = maior |z|; unilateral = z mais negativo
      (a direção alegada: B penalizado). A média da janela dá o tamanho do efeito em p.p.
    Nulo: os horários de chegada ficam como foram e o resíduo é embaralhado entre as seções da mesma escola. (Uma versão
    anterior girava a fase de cada escola; isso espalha as seções pelo minuto e torna o nulo estreito demais nas janelas
    quase vazias, gerando falsos positivos.) Poder: move uma fração φ dos votos de B para L numa janela de fase sorteada."""
    d = d.filter((pl.col("b2") + pl.col("l2") > 0) & (pl.col("b1") + pl.col("l1") > 0) & pl.col("recebido").is_not_null()).with_columns(
        grupo=pl.concat_str(["sg_uf", "cd_municipio_tse", "zona", "local"], separator="-"),
        fase=(pl.col("recebido").dt.epoch("s") % periodo))
    grupo = d["grupo"].cast(pl.Categorical).to_physical().to_numpy()
    fase = d["fase"].to_numpy().astype(int)
    b2, l2, b1, l1 = [d[c].to_numpy().astype(float) for c in ("b2", "l2", "b1", "l1")]
    w = b2 + l2
    s1 = b1 / (b1 + l1)
    ng = grupo.max() + 1
    sw = np.bincount(grupo, weights=w, minlength=ng)

    def residuo(b2_):
        delta = b2_ / w - s1
        return delta - (np.bincount(grupo, weights=delta * w, minlength=ng) / sw)[grupo]

    k = np.ones(janela_fase)
    janela = lambda v: np.convolve(np.r_[v, v[:janela_fase - 1]], k, "valid")  # noqa: E731

    def medias(r, f):
        """Médias por janela circular (p.p. do efeito), escores z por janela e perfil por segundo."""
        soma = np.bincount(f, weights=r * w, minlength=periodo)
        peso = np.bincount(f, weights=w, minlength=periodo)
        quad = np.bincount(f, weights=(r * w) ** 2, minlength=periodo)
        S, W, Q = janela(soma), janela(peso), janela(quad)
        return S / np.maximum(W, 1), S / np.sqrt(np.maximum(Q, 1e-12)), soma / np.maximum(peso, 1)

    def estat(r, f):
        z = medias(r, f)[1]
        return float(np.abs(z).max()), float(-z.min())

    base = np.argsort(grupo, kind="stable")

    def embaralhar(r):
        out = np.empty_like(r)
        out[base] = r[np.lexsort((RNG.random(len(r)), grupo))]
        return out

    r0 = residuo(b2)
    (bi, uni), (m0, z0, perfil) = estat(r0, fase), medias(r0, fase)
    nulo = np.array([estat(embaralhar(r0), fase) for _ in range(n_perm)])
    p_bi = float((1 + (nulo[:, 0] >= bi).sum()) / (1 + n_perm))
    p_uni = float((1 + (nulo[:, 1] >= uni).sum()) / (1 + n_perm))
    crit = float(np.quantile(nulo[:, 1], 0.95))
    poder = []
    for phi in efeitos:
        reps, det = 40, 0
        for _ in range(reps):
            ini = RNG.integers(periodo)
            alvo = np.isin(fase, (ini + np.arange(janela_fase)) % periodo)
            det += estat(residuo(np.where(alvo, b2 * (1 - phi), b2)), fase)[1] > crit
        poder.append({"phi": phi, "poder": det / reps})
    j, jn = int(np.argmax(np.abs(z0))), int(np.argmin(z0))
    return {"z_bilateral": bi, "p_bilateral": p_bi, "z_unilateral": uni, "p_unilateral": p_uni, "z_critico": crit,
            "janela_mais_extrema": {"inicio_s": j, "media_pp": float(m0[j] * 100), "z": float(z0[j])},
            "janela_mais_negativa": {"inicio_s": jn, "media_pp": float(m0[jn] * 100), "z": float(z0[jn])},
            "n_perm": n_perm, "janela_fase_s": janela_fase, "periodo_s": periodo, "secoes": int(len(w)), "locais": int(ng),
            "perfil": [{"segundo": i, "residuo_pp": float(v * 100)} for i, v in enumerate(perfil)], "poder": poder}


# ---------------------------------------------------------------- viradas
def cruzamentos(c: np.ndarray, desde: int) -> int:
    s = np.sign(c[desde:] - 0.5)
    s = s[s != 0]
    return int((np.diff(s) != 0).sum())


def teste_viradas(d: pl.DataFrame, n_sim: int = 3000):
    b, l = d["b2"].to_numpy().astype(float), d["l2"].to_numpy().astype(float)
    tot = b + l
    c = np.cumsum(b) / np.maximum(np.cumsum(tot), 1)
    desde = len(b) // 100  # ignora o primeiro 1% (poucos votos: a fatia oscila à toa)
    real = cruzamentos(c, desde)
    sims, ultimo, maxdesv = [], [], []
    for _ in range(n_sim):
        p = RNG.permutation(len(b))
        cs = np.cumsum(b[p]) / np.maximum(np.cumsum(tot[p]), 1)
        sims.append(cruzamentos(cs, desde))
        s = np.sign(cs - 0.5)
        mud = np.flatnonzero(np.diff(s) != 0)
        ultimo.append(int(mud[-1]) if len(mud) else 0)
        maxdesv.append(float(np.abs(cs[desde:] - cs[-1]).max()))
    sims = np.array(sims)
    return {"cruzamentos_real": real, "cruzamentos_sim_media": float(sims.mean()),
            "cruzamentos_sim_p99": float(np.quantile(sims, 0.99)), "frac_sim_zero": float((sims == 0).mean()),
            "ultimo_cruzamento_sim_p99": float(np.quantile(ultimo, 0.99)),
            "desvio_max_sim_p99_pp": float(np.quantile(maxdesv, 0.99) * 100),
            "desvio_max_real_pp": float(np.abs(c[desde:] - c[-1]).max() * 100),
            "pico_real": float(c[desde:].max()), "desde": desde, "n_sim": n_sim}


def composicao(d: pl.DataFrame, passos: int = 50):
    n = d.height
    idx = np.linspace(n // passos, n, passos).astype(int)
    reg = d["regiao"].to_numpy()
    linhas = []
    for i in idx:
        r = reg[:i]
        linhas.append({"secoes": int(i), **{k: float((r == k).mean()) for k in
                                             ("Nordeste", "Sudeste", "Sul", "Norte", "Centro-Oeste")}})
    return linhas


def main():
    out = {}
    h2, h1 = hist("2T"), hist("1T")

    # 1. reprodução dos pontos do vídeo (lidos nos quadros 2:30–3:50)
    video = [(23954, 0.529867), (70197, 0.516887), (71324, 0.516603), (72747, 0.516508), (74682, 0.515568)]
    rep = []
    for x, y in video:
        r = h2.filter(pl.col("secoes") == x)
        rep.append({"secoes": x, "video": y, "tse": float(r["pe_b"][0]) if r.height else None,
                    "hora": str(r["t"][0].time()) if r.height else None})
    out["reproducao"] = rep
    fin = h2.tail(1)
    out["final_hist"] = {"lula": int(fin["LULA_QT_VOTOS_TOT_ACUMULADO"][0]),
                         "bolsonaro": int(fin["JAIR_BOLSONARO_QT_VOTOS_TOT_ACUMULADO"][0]),
                         "secoes": int(fin["secoes"][0]), "snapshots": h2.height}

    # séries para o site
    passo = max(1, h2.height // 1500)
    salvar_json("ch06b/serie-2t-2022", {"meta": meta("Percentual acumulado de Bolsonaro, 2º turno 2022",
                "Uma linha por registro do histórico de totalização (amostrado)."),
                "dados": h2.gather_every(passo).select("secoes", "pe_b", pe_l="LULA_PE_VOTOS_TOT_ACUMULADO",
                                                        hora=pl.col("t").dt.strftime("%H:%M:%S")).to_dicts()}, 6)
    z = h2.filter(pl.col("secoes").is_between(65000, 90000))
    salvar_json("ch06b/zoom-2t-2022", {"meta": meta("Zoom 65 mil–90 mil seções", "Cada ponto é um registro do histórico; "
                "inc_b = fatia de Bolsonaro só no lote que entrou naquele segundo."),
                "dados": z.select("secoes", "pe_b", "inc_b", n=pl.col("QT_SECOES_TOT"),
                                  hora=pl.col("t").dt.strftime("%H:%M:%S")).to_dicts()}, 6)

    # vales: segundos consecutivos com incremento < 0,35 (≥ 3 registros)
    v = z.with_columns(baixo=(pl.col("inc_b") < 0.35) & (pl.col("QT_SECOES_TOT") >= 5))
    v = v.with_columns(grp=(pl.col("baixo") != pl.col("baixo").shift()).cum_sum()).filter(pl.col("baixo"))
    vales = v.group_by("grp").agg(ini=pl.col("t").min(), n=pl.len(), secoes=pl.col("QT_SECOES_TOT").sum()).filter(
        pl.col("n") >= 3).sort("ini")
    ini = vales["ini"].to_list()
    out["vales_zoom"] = [{"inicio": str(a.time()), "registros": int(n), "secoes": int(s)}
                         for a, n, s in zip(ini, vales["n"], vales["secoes"])]
    out["intervalo_vales_s"] = [float((b - a).total_seconds()) for a, b in zip(ini, ini[1:])]

    # 2. periodicidade
    pk2, sp2 = espectro(h2)
    pk1, sp1 = espectro(h1)
    out["picos_2t"], out["picos_1t"] = pk2, pk1
    salvar_json("ch06b/espectro", {"meta": meta("Espectro do desvio dos incrementos",
                "Potência relativa à mediana, por período (s), 17h–19h."),
                "dados": {"t2": sp2, "t1": sp1}})

    # 3. assinatura dos lotes
    w = h2.filter((pl.col("QT_SECOES_TOT") >= 20) & (pl.col("t").dt.hour() < 19)).with_columns(
        faixa=pl.when(pl.col("inc_b") < 0.35).then(pl.lit("lotes < 35% B (vales)"))
        .when(pl.col("inc_b") < 0.45).then(pl.lit("35–45%")).when(pl.col("inc_b") < 0.55).then(pl.lit("45–55%"))
        .when(pl.col("inc_b") < 0.65).then(pl.lit("55–65%")).otherwise(pl.lit("≥ 65%")))
    ass = w.group_by("faixa").agg(
        registros=pl.len(), secoes=pl.col("QT_SECOES_TOT").sum(),
        fatia_b=pl.col("JAIR_BOLSONARO_QT_VOTOS_TOT").sum() / (pl.col("JAIR_BOLSONARO_QT_VOTOS_TOT").sum() + pl.col("LULA_QT_VOTOS_TOT").sum()),
        comparecimento=pl.col("QT_VOTOS_TOTAL").sum() / pl.col("QT_APTOS_TOT").sum(),
        brancos_nulos=(pl.col("BRANCO_QT_VOTOS_TOT").sum() + pl.col("NULO_QT_VOTOS_TOT").sum()) / pl.col("QT_VOTOS_TOTAL").sum(),
        aptos_secao=pl.col("QT_APTOS_TOT").sum() / pl.col("QT_SECOES_TOT").sum()).sort("fatia_b").with_columns(tipo=pl.lit("lote"))
    b22 = bweb22()
    reg = b22.group_by("regiao").agg(
        secoes=pl.len(), fatia_b=pl.col("b2").sum() / (pl.col("b2").sum() + pl.col("l2").sum()),
        comparecimento=pl.col("comp").sum() / pl.col("aptos").sum(), brancos_nulos=pl.col("bn").sum() / pl.col("comp").sum(),
        aptos_secao=pl.col("aptos").mean()).filter(pl.col("regiao") != "Exterior").sort("fatia_b").rename({"regiao": "faixa"}).with_columns(
        tipo=pl.lit("região"), registros=pl.lit(None, pl.UInt32), secoes=pl.col("secoes").cast(pl.Int64))
    ass = pl.concat([ass, reg.select(ass.columns)])
    salvar_json("ch06b/assinatura", {"meta": meta("Perfil dos lotes × perfil das regiões",
                "Comparecimento, brancos+nulos e aptos por seção não mudam se votos forem trocados de candidato.",
                FONTE_HIST + "; TSE: boletins de urna 2022"), "dados": ass.to_dicts()})
    out["assinatura"] = ass.to_dicts()

    # 4. placebo 2022 e 2026 (ordem de chegada reconstruída pelo bweb)
    o22 = ordenar(b22)
    out["placebo_2022"], s22 = placebo(o22, (65000, 90000))
    o26 = ordenar(secoes26())
    out["placebo_2026"], s26 = placebo(o26, (65000, 90000))
    salvar_json("ch06b/placebo", {"meta": meta("Mesmas seções, mesma ordem de chegada: votos do 2º × do 1º turno",
                "Variação do percentual acumulado desde o início da janela (65 mil seções).",
                "TSE: boletins de urna 2022 e 2026 (DT_BU_RECEBIDO)"),
                "dados": {"2022": s22, "2026": s26, "stats": {"2022": out["placebo_2022"], "2026": out["placebo_2026"]}}}, 6)

    # 5. teste de fase com poder
    print("teste de fase 2022…", flush=True)
    out["fase_2022"] = teste_fase(o22)
    print("teste de fase 2026…", flush=True)
    out["fase_2026"] = teste_fase(o26)
    salvar_json("ch06b/fase", {"meta": meta("Variação 1T→2T por segundo de chegada, descontado o município",
                "Resíduo médio (p.p.) da fatia de B/Flávio; poder = chance de detectar o 'algoritmo' sintético.",
                "TSE: boletins de urna 2022 e 2026"), "dados": {"2022": out["fase_2022"], "2026": out["fase_2026"]}})

    # 6. viradas
    print("viradas…", flush=True)
    out["viradas_2022"] = teste_viradas(o22)
    out["viradas_2026"] = teste_viradas(o26)
    c1 = h1.with_columns(d=pl.col("JAIR_BOLSONARO_QT_VOTOS_TOT_ACUMULADO") - pl.col("LULA_QT_VOTOS_TOT_ACUMULADO"))
    vir1 = c1.filter((pl.col("d") < 0) & (pl.col("secoes") > 5000)).head(1)
    c2 = h2.with_columns(d=pl.col("JAIR_BOLSONARO_QT_VOTOS_TOT_ACUMULADO") - pl.col("LULA_QT_VOTOS_TOT_ACUMULADO"))
    vir2 = c2.filter((pl.col("d") < 0) & (pl.col("secoes") > 5000)).head(1)
    out["virada_hist"] = {"1t": {"secoes": int(vir1["secoes"][0]), "hora": str(vir1["t"][0].time()),
                                 "pct_secoes": float(vir1["PE_SECOES_TOT_ACUMULADO"][0])},
                          "2t": {"secoes": int(vir2["secoes"][0]), "hora": str(vir2["t"][0].time()),
                                 "pct_secoes": float(vir2["PE_SECOES_TOT_ACUMULADO"][0])}}
    out["pico_b_hist_2t"] = float(h2.filter(pl.col("secoes") > 5000)["pe_b"].max())
    salvar_json("ch06b/composicao", {"meta": meta("Composição regional das seções já recebidas",
                "Fração de cada região entre as seções recebidas até aquele ponto (2º turno 2022).",
                "TSE: boletins de urna 2022 (DT_BU_RECEBIDO)"), "dados": composicao(o22)}, 4)

    salvar_json("ch06b/resumo", {"meta": meta("Números do capítulo 6b", "Saída completa do script."), "dados": out}, 6)
    for k, val in out.items():
        if k in ("assinatura",):
            continue
        if isinstance(val, dict) and "perfil" in val:
            val = {kk: vv for kk, vv in val.items() if kk != "perfil"}
        print(k, val)


if __name__ == "__main__":
    main()
