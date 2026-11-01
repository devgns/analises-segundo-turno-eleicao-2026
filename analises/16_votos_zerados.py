"""Zeros por candidato nas mesmas seções, 2026 e 2022.

Uso: uv run python analises/16_votos_zerados.py
No primeiro turno, zero significa nenhum voto nominal ao candidato mesmo que
outros candidatos tenham recebido votos. No segundo, o adversário de Lula é
Flávio (2026) ou Jair Bolsonaro (2022). Exclui seções sem votos válidos.
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import polars as pl

from comum import bweb, salvar_json

spec = importlib.util.spec_from_file_location("extremos", Path(__file__).with_name("09_extremos.py"))
extremos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extremos)
CHAVE = ["sg_uf", "cd_municipio_tse", "zona", "secao"]


def main():
    bases = {2026: extremos.base_2026(), 2022: extremos.base_2022()}
    contagens, contagens_completas, persistencia = [], [], []
    for ano, df in bases.items():
        for turno in (1, 2):
            lf = bweb(ano, turno)
            validos = pl.col("votos_validos")
            if ano == 2026 and turno == 1 and "votos_28" in lf.collect_schema().names():
                validos = validos - pl.col("votos_28").fill_null(0)
            completo = lf.select(validos.alias("validos"), pl.col("votos_13").fill_null(0).alias("lula"),
                                 pl.col("votos_22").fill_null(0).alias("direita")).collect()
            completo = completo.filter(pl.col("validos") > 0)
            for candidato, coluna in (("Lula", "lula"), ("Flávio" if ano == 2026 else "Jair Bolsonaro", "direita")):
                contagens_completas.append({"ano": ano, "turno": turno, "candidato": candidato,
                                            "secoes_validas": completo.height,
                                            "zero": completo.filter(pl.col(coluna) == 0).height})
            d = df.filter(pl.col(f"validos_{turno}") > 0)
            for candidato, coluna in (("Lula", "lula"), ("Flávio" if ano == 2026 else "Jair Bolsonaro", "flavio")):
                contagens.append({"ano": ano, "turno": turno, "candidato": candidato, "secoes_validas": d.height,
                                  "secoes_sem_validos": df.height - d.height,
                                  "zero": d.filter(pl.col(f"{coluna}_{turno}") == 0).height})
        zeros = df.filter((pl.col("validos_2") > 0) & (pl.col("flavio_2") == 0))
        soma = zeros.select(pl.col("flavio_1").sum(), pl.col("flavio_1").max().alias("max_primeiro"),
                            pl.col("validos_2").sum(), pl.col("validos_2").median().alias("mediana_validos"),
                            ((pl.col("validos_1") > 0) & (pl.col("flavio_1") == 0)).sum().alias("zero_ambos"),
                            ((pl.col("validos_1") > 0) & (pl.col("flavio_1") > 0)).sum().alias("positivo_primeiro"),
                            ((pl.col("lula_1") / (pl.col("lula_1") + pl.col("flavio_1"))) >= .9).sum().alias("lula_90_finalistas"))
        persistencia.append({"ano": ano, "secoes": zeros.height, **soma.row(0, named=True)})

    z26 = bases[2026].filter((pl.col("validos_2") > 0) & (pl.col("flavio_2") == 0))
    antigo = bases[2022].select(*CHAVE, pl.col("local").alias("local_2022"),
                                 *[pl.col(f"{c}_{t}").alias(f"{c}_2022_{t}")
                                   for t in (1, 2) for c in ("lula", "flavio", "validos")])
    j = z26.join(antigo, on=CHAVE, how="left").sort(["flavio_1", "validos_2"], descending=[True, True])
    cruzamento = {"secoes_2026": j.height, "encontradas_2022": int(j["validos_2022_2"].is_not_null().sum()),
                  "nao_encontradas_2022": int(j["validos_2022_2"].is_null().sum()),
                  "zero_bolsonaro_2022_t1": j.filter((pl.col("validos_2022_1") > 0) & (pl.col("flavio_2022_1") == 0)).height,
                  "zero_bolsonaro_2022_t2": j.filter((pl.col("validos_2022_2") > 0) & (pl.col("flavio_2022_2") == 0)).height,
                  "zero_bolsonaro_ambos_2022": j.filter((pl.col("validos_2022_1") > 0) & (pl.col("validos_2022_2") > 0) &
                                                         (pl.col("flavio_2022_1") == 0) & (pl.col("flavio_2022_2") == 0)).height}
    linhas = j.select(*CHAVE, "nm_municipio", "local", "local_2022", "lula_1", "flavio_1", "validos_1",
                      "lula_2", "flavio_2", "validos_2", "lula_2022_1", "flavio_2022_1", "validos_2022_1",
                      "lula_2022_2", "flavio_2022_2", "validos_2022_2").to_dicts()
    meta = {"titulo": "Seções sem voto no candidato", "fonte": "TSE — BUs por seção, 2022 e 2026",
            "script": "analises/16_votos_zerados.py", "gerado_em": date.today().isoformat(),
            "descricao": "contagens_completas inclui todas as seções; contagens e persistencia usam as pareadas entre turnos no respectivo ano. Em ambos, o turno contado deve ter ao menos um voto válido. A chave pode permanecer igual mesmo se os eleitores ou o local mudarem. Em 2022 o candidato é Jair Bolsonaro, não Flávio."}
    salvar_json("ch09/votos-zerados", {"meta": meta, "contagens": contagens, "contagens_completas": contagens_completas, "persistencia": persistencia,
                                       "cruzamento": cruzamento, "dados": linhas})
    print(json.dumps({"contagens_pareadas": contagens, "contagens_completas": contagens_completas, "persistencia": persistencia, "cruzamento": cruzamento,
                      "maior_perda_2026": linhas[0]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
