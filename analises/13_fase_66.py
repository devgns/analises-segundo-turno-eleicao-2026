"""Teste exploratório de pulso de 66 s no recebimento de BUs, não na totalização."""
import importlib.util
import json
from pathlib import Path

from comum import salvar_json

spec = importlib.util.spec_from_file_location("serrote", Path(__file__).with_name("06b_serrote_totalizacao.py"))
serrote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serrote)


def main():
    resultados = {}
    for ano, dados in ((2022, serrote.bweb22), (2026, serrote.secoes26)):
        print(f"fase de 66 s: {ano}", flush=True)
        resultados[str(ano)] = serrote.teste_fase(dados(), n_perm=199, periodo=66, efeitos=(0.005, 0.02, 0.05))
        print(json.dumps(resultados[str(ano)] | {"perfil": "omitido"}, ensure_ascii=False), flush=True)
    salvar_json("ch06b/fase-66", {"meta": {"script": "analises/13_fase_66.py", "fonte": "TSE — BUs por seção de 2022 e 2026", "descricao": "Análise exploratória: 66 fases, janela móvel de 8 s, permutação do resíduo dentro do local; 199 permutações, 40 injeções por tamanho, semente 2026. Horários de recebimento, não de totalização."}, "dados": resultados})


if __name__ == "__main__":
    main()
