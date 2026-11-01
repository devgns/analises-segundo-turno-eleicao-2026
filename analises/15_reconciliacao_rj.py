"""Concilia diferenças entre log principal, logs substituídos e BU nos nove municípios."""
import json
import unicodedata
from pathlib import Path

from comum import salvar_json

DATA = Path(__file__).resolve().parent.parent / "site/public/data"


def normalizar(x):
    return "".join(c for c in unicodedata.normalize("NFKD", x.upper()) if not unicodedata.combining(c))


def main():
    casos = json.loads((DATA / "cap04-casos.json").read_text())["dados"]
    nomes = {normalizar(x["municipio"]) for x in casos}
    logs = json.loads((DATA / "ch08/substituicoes.json").read_text())["dados"]
    dados = [x for x in logs if x["uf"] == "RJ" and normalizar(x["municipio"]) in nomes]
    ultimo = sum(x["votos_ultima_urna"] - x["comparecimento"] for x in dados)
    todos = sum(x["dif_bu"] for x in dados)
    saida = {"secoes_com_deficit": len(dados), "diferenca_log_principal": ultimo,
             "diferenca_logs_incluindo_substituidas": todos, "secoes": dados}
    salvar_json("ch04/reconciliacao-logs", {"meta": {"script": "analises/15_reconciliacao_rj.py", "fonte": "TSE — BUs e logs de urnas substituídas", "descricao": "A lista cobre apenas seções com déficit do log principal; não detecta seções cujo log principal exceda o BU."}, "dados": saida})
    print(json.dumps({k: v for k, v in saida.items() if k != "secoes"}, ensure_ascii=False))
    for x in dados:
        print(x["municipio"], x["zona"], x["secao"], x["votos_ultima_urna"] - x["comparecimento"], x["dif_bu"])


if __name__ == "__main__":
    main()
