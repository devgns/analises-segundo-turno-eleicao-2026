"""Gera site/simulador/index.html: o simulador de transferência de votos do 1º para o 2º turno,
aba do site. O layout fica em site/simulador/template.html; a moldura do site (abas, tema,
rodapé) é carregada por site/src/paginas/simulador.js. Rode `npm run build` em site/ depois.

Busca no painel do TSE o resultado presidencial do 1º turno (eleição 6257) e do 2º turno (6258)
e as fotos oficiais dos candidatos, e embute tudo no HTML.

Uso:
    uv run scripts/gerar_simulador.py
"""

import base64
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "site" / "simulador" / "template.html"
SAIDA = ROOT / "site" / "simulador" / "index.html"
# Trecho do <head>: aplica o tema salvo antes da pintura e carrega a moldura.
CABECA_SITE = """<script>
  try { const t = localStorage.getItem('tema-relatorio'); if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t; } catch (e) {}
</script>
<script type="module" src="/src/paginas/simulador.js"></script>"""
BASE = "https://resultados.tse.jus.br/oficial/ele2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (analise-eleicao-2026)"}

# Candidatos com card próprio (número na urna -> nome de exibição); o resto vira "Demais candidatos"
DESTAQUES = {
    "13": "Lula",
    "22": "Flávio Bolsonaro",
    "70": "Augusto Cury",
    "14": "Renan Santos",
    "55": "Ronaldo Caiado",
    "30": "Romeu Zema",
}
FINALISTAS = ("13", "22")


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as resp:
        return resp.read()


def resultado(eleicao: str) -> dict:
    d = json.loads(get(f"{BASE}/{eleicao}/dados/br/br-c0001-e{int(eleicao):06d}-u.json"))
    cands = [
        {"numero": c["n"], "nome_urna": c["nmu"], "partido": p["sg"], "sqcand": c["sqcand"], "votos": int(c["vap"])}
        for a in d["carg"][0]["agr"]
        for p in a["par"]
        for c in p["cand"]
    ]
    return {
        "atualizado": f"{d['dt']} {d['ht']}",
        "secoes_pct": d["s"]["pst"],
        "aptos": int(d["e"]["te"]),
        "comparecimento": int(d["e"]["c"]),
        "abstencao": int(d["e"]["a"]),
        "validos": int(d["v"]["vv"]),
        "brancos": int(d["v"]["vb"]),
        "nulos": int(d["v"]["tvn"]),
        "candidatos": sorted(cands, key=lambda c: -c["votos"]),
    }


def main() -> None:
    t1, t2 = resultado("6257"), resultado("6258")

    destaques, demais = [], []
    for c in t1["candidatos"]:
        if c["numero"] in DESTAQUES:
            foto = get(f"{BASE}/6257/fotos/br/{c['sqcand']}.jpeg")
            destaques.append({
                "id": c["numero"],
                "nome": DESTAQUES[c["numero"]],
                "partido": c["partido"],
                "votos": c["votos"],
                "finalista": c["numero"] in FINALISTAS,
                "foto": "data:image/jpeg;base64," + base64.b64encode(foto).decode(),
            })
        else:
            demais.append({"nome": c["nome_urna"].title(), "partido": c["partido"], "votos": c["votos"]})

    dados = {
        "t1": {k: v for k, v in t1.items() if k != "candidatos"},
        "t2": {
            **{k: v for k, v in t2.items() if k != "candidatos"},
            "lula": next(c["votos"] for c in t2["candidatos"] if c["numero"] == "13"),
            "flavio": next(c["votos"] for c in t2["candidatos"] if c["numero"] == "22"),
        },
        "candidatos": destaques,
        "demais": demais,
    }
    assert sum(c["votos"] for c in destaques) + sum(c["votos"] for c in demais) == t1["validos"]

    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DADOS__*/{}", json.dumps(dados, ensure_ascii=False))
    SAIDA.write_text(html.replace("<!--__SITE_CABECA__-->", CABECA_SITE), encoding="utf-8")
    print(f"{SAIDA} ({SAIDA.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
