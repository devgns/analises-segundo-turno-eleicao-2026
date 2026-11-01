"""Limites de margens, geografia do comparecimento e escala ilustrativa.

Rodar após 02_mapa_virada.py: uv run python analises/12_limites_e_escala.py
Os limites individuais pressupõem o mesmo conjunto de eleitores nas seções pareadas;
igualdade de aptos é necessária para essa hipótese, mas não a comprova.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl

from comum import secoes_2026, salvar_json

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site/public/data"
SCRIPT = "analises/12_limites_e_escala.py"


def main():
    s = secoes_2026()
    iguais = s.filter(pl.col("pareada") & (pl.col("aptos_1") == pl.col("aptos_2")) & (pl.col("aptos_1") > 0))
    # Grupo inicial: abstenção + brancos/nulos. Fréchet por seção, para o
    # cruzamento com Lula no 2º turno, condicionado ao mesmo eleitorado.
    d = iguais.with_columns((pl.col("aptos_1") - pl.col("validos_1")).alias("grupo"))
    d = d.with_columns(
        (pl.col("grupo") + pl.col("lula_2") - pl.col("aptos_1")).clip(lower_bound=0).alias("minimo"),
        pl.min_horizontal("grupo", "lula_2").alias("maximo"),
    )
    resultado = d.select(pl.len().alias("secoes"), pl.col("aptos_1").sum().alias("aptos"),
                         pl.col("grupo").sum().alias("grupo_inicial"), pl.col("lula_2").sum().alias("lula_2"),
                         pl.col("minimo").sum(), pl.col("maximo").sum()).row(0, named=True)
    resultado["secoes_fora"] = s.height - d.height
    resultado["aptos_fora"] = int(s["aptos_2"].sum() - d["aptos_2"].sum())
    uf = (s.group_by("sg_uf", "regiao").agg(pl.col("comp_1", "comp_2", "aptos_1", "aptos_2", "lula_2", "flavio_2").sum())
          .with_columns((pl.col("comp_2") - pl.col("comp_1")).alias("delta_comparecimento"),
                        (pl.col("lula_2") / (pl.col("lula_2") + pl.col("flavio_2"))).alias("fatia_lula"))
          .sort("delta_comparecimento", descending=True))
    meta = {"script": SCRIPT, "fonte": "TSE — boletins por seção, 2026", "gerado_em": date.today().isoformat()}
    salvar_json("ch01/limites-frechet", {"meta": meta | {"descricao": "Limites de Fréchet por seção para abstenção ou branco/nulo no 1º turno e Lula no 2º. Supõe o mesmo eleitorado; não identifica novos votos válidos nem comprova fluxos."}, "dados": [resultado]})
    salvar_json("ch01/comparecimento-uf", {"meta": meta | {"descricao": "Saldos por UF, incluindo exterior ZZ. Saldos não identificam votos ou fluxos individuais."}, "dados": uf.to_dicts()})
    # O intercepto mede Δ na fatia de Lula, não Δ na margem. Uma troca t
    # aumenta a fatia em t/N e a margem em 2t, com N fixo.
    interceptos = json.loads((DATA / "ch02/modelo-intercepto.json").read_text())["dados"]
    intercepto = next(r["intercepto"] for r in interceptos if r["modelo"] == "municipio 2026")
    totais = s.select(pl.col("lula_2", "flavio_2", "biom_sh_1", "biom_sh_2").sum()).row(0, named=True)
    n = totais["lula_2"] + totais["flavio_2"]
    t = round(intercepto * n)
    escala_path = DATA / "ch12/escala.json"
    escala = json.loads(escala_path.read_text())
    # O intercepto é um ponto contrafactual do modelo, sem tradução em votos: não entra na escala.
    escala["dados"] = [x for x in escala["dados"] if not x["mecanismo"].startswith("Componente comum")]
    if not any(x["mecanismo"].startswith("Total de habilitações sem biometria") for x in escala["dados"]):
        escala["dados"].append({"mecanismo": "Total de habilitações sem biometria (estoque)", "votos": totais["biom_sh_2"], "multiplicador": 1, "efeito_max": totais["biom_sh_2"], "situacao": "sem pegadas", "capitulo": 12, "script_origem": SCRIPT})
    escala["meta"]["script"] = SCRIPT
    escala["meta"]["descricao"] += " Valores são referências de escala, não estimativas de irregularidade; categorias se sobrepõem e não devem ser somadas."
    # Evitar mudança cumulativa na descrição ao reexecutar.
    escala["meta"]["descricao"] = escala["meta"]["descricao"].split(" Valores são referências")[0] + " Valores são referências de escala, não estimativas de irregularidade; categorias se sobrepõem e não devem ser somadas."
    escala_path.write_text(json.dumps(escala, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"limites": resultado, "intercepto": intercepto, "trocas_ilustrativas": t, "margem_ilustrativa": 2*t,
                      "ufs_lula_ate_50": uf.filter(pl.col("fatia_lula") <= 0.5)["delta_comparecimento"].sum(),
                      "ufs_lula_acima_50": uf.filter(pl.col("fatia_lula") > 0.5)["delta_comparecimento"].sum(),
                      "norte": uf.filter(pl.col("regiao") == "Norte")["delta_comparecimento"].sum()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
