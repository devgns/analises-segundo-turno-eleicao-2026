"""Capítulo 08 — baixa e lê os logs COMPLETOS das seções em que o log tem menos votos que o BU.

O coletor (scripts/baixar_logs_urna.py) lê só o `logd.dat` de cada log.jez, que é o log da ÚLTIMA urna
usada na seção. Quando a urna é substituída durante a votação, o log.jez traz também, como arquivos .jez
internos, os logs das urnas anteriores. Este script baixa de novo o log.jez das seções com
n_votos_log < comparecimento (e de uma amostra aleatória de controle com n_votos_log = comparecimento),
lê TODOS os logs internos e verifica se a soma dos votos fecha com o BU.

Saída: data/processed/base/substituicoes_logs.parquet (uma linha por arquivo de log dentro do log.jez).
Uso: uv run python analises/08_substituicoes.py   (~10 min; rede: resultados.tse.jus.br)
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from baixar_logs_urna import BASE as URL_BASE  # noqa: E402
from baixar_logs_urna import DIA, P, get, parse_log  # noqa: E402
from comum import BASE, secoes_2026  # noqa: E402

SAIDA = BASE / "substituicoes_logs.parquet"
N_CONTROLE = 400


def _ler_logd(nome: str, dados: bytes) -> dict:
    eleitores, resumo = parse_log(dados)
    texto = dados.decode("latin-1")
    linhas_dia = [ln for ln in texto.splitlines() if ln.startswith(DIA)]
    urna = linhas_dia[0].split("\t")[2] if linhas_dia else None
    if urna is None:
        for ln in texto.splitlines():
            c = ln.split("\t")
            if len(c) >= 5:
                urna = c[2]
                break
    tsc = [e["ts_computado"] for e in eleitores]
    return {
        "arquivo": nome, "urna": urna, "modelo_urna": resumo["modelo_urna"],
        "contingencia": "Urna de contingência" in texto,
        "n_votos": len(eleitores),
        "n_sem_digital": sum(1 for e in eleitores if e.get("tipo_habilitacao") != "biométrica"),
        "ts_pronta": resumo["ts_urna_pronta"], "ts_primeiro": min(tsc, default=None), "ts_ultimo": max(tsc, default=None),
        "n_alertas": resumo["n_alertas"], "n_erros": resumo["n_erros"],
    }


def _jez_recursivo(nome: str, dados: bytes, prof: int = 0) -> list[dict]:
    out = []
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        for nm in z.namelist():
            b = z.read(nm)
            if nm.endswith(".jez") and prof < 3:
                out += _jez_recursivo(f"{nome}/{nm}", b, prof + 1)
            elif nm.endswith(".dat") and nm.startswith("logd"):
                out.append({**_ler_logd(f"{nome}/{nm}", b), "interno": prof > 0})
    return out


def processar(sec: dict) -> list[dict]:
    uf, mu, zo, se = sec["sg_uf"].lower(), sec["cd_municipio_tse"], sec["zona"], sec["secao"]
    pasta = f"{URL_BASE}/dados/{uf}/{mu}/{zo}/{se}"
    aux = json.loads(get(f"{pasta}/{P}-{uf}-m{mu}-z{zo}-s{se}-aux.json"))
    com_log = [h for h in aux.get("hashes", []) if any(a["tp"] == "log" for a in h.get("arq", []))]
    hashes = [h for h in com_log if h.get("st") == "Totalizado"] or [h for h in com_log if h.get("st") == "Recebido"]
    linhas = []
    for h in hashes:
        for a in h["arq"]:
            if a["tp"] != "log":
                continue
            jez = get(f"{pasta}/{h['hash']}/{a['nm']}")
            for r in _jez_recursivo(a["nm"], jez):
                linhas.append({**{k: sec[k] for k in ("sg_uf", "cd_municipio_tse", "zona", "secao", "grupo")},
                               "hash": h["hash"][:16], "n_hashes": len(hashes), **r})
    return linhas


def main() -> None:
    s = secoes_2026().filter(pl.col("comp_2").is_not_null() & (pl.col("sg_uf") != "ZZ"))
    falta = s.filter(pl.col("n_votos_log") < pl.col("comp_2")).with_columns(pl.lit("deficit").alias("grupo"))
    ctrl = (s.filter(pl.col("n_votos_log") == pl.col("comp_2")).sample(N_CONTROLE, seed=20261025)
            .with_columns(pl.lit("controle").alias("grupo")))
    alvo = pl.concat([falta, ctrl]).select("sg_uf", "cd_municipio_tse", "zona", "secao", "grupo").to_dicts()
    print(f"{len(falta)} seções com déficit + {len(ctrl)} de controle", flush=True)
    linhas, falhas = [], []
    with ThreadPoolExecutor(12) as pool:
        futs = {pool.submit(processar, a): a for a in alvo}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                linhas += f.result()
            except Exception as exc:  # noqa: BLE001
                falhas.append({**futs[f], "erro": repr(exc)})
            if i % 200 == 0:
                print(f"  {i}/{len(alvo)}", flush=True)
    df = pl.DataFrame(linhas, infer_schema_length=None)
    df.write_parquet(SAIDA)
    print(f"ok: {df.height} logs; falhas={len(falhas)}", flush=True)
    if falhas:
        print(pl.DataFrame(falhas).head(10))


if __name__ == "__main__":
    main()
