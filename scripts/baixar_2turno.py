"""Baixa o resultado do 2º turno presidencial de 2026 do painel do TSE e gera Parquets.

Fonte: https://resultados.tse.jus.br/oficial/ele2026/6258/ (eleição 6258, cargo 0001).
Os JSONs brutos ficam em cache em data/raw/, então rodar de novo só baixa o que falta.

Uso:
    uv run scripts/baixar_2turno.py            # usa cache
    uv run scripts/baixar_2turno.py --refresh  # rebaixa tudo
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import polars as pl

ELEICAO = "6258"
E = f"e{int(ELEICAO):06d}"  # nos nomes de arquivo o código vem com zeros: e006258
BASE = f"https://resultados.tse.jus.br/oficial/ele2026/{ELEICAO}"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / ELEICAO
OUT = ROOT / "data" / "processed"
HEADERS = {"User-Agent": "Mozilla/5.0 (analise-eleicao-2026)"}


def fetch_json(url: str, dest: Path, refresh: bool, tentativas: int = 5) -> dict:
    if dest.exists() and not refresh:
        return json.loads(dest.read_bytes())
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
            data = json.loads(body)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            return data
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if i == tentativas - 1 or getattr(exc, "code", None) == 404:
                raise
            time.sleep(2**i)
    raise AssertionError("inalcançável")


def num(s: str | None) -> float | None:
    """Converte '51,79' / '64256232' do TSE para número."""
    if s in (None, ""):
        return None
    return float(s.replace(",", "."))


def parse_resultado(d: dict) -> tuple[dict, list[dict]]:
    """Achata um arquivo *-c0001-e006258-u.json em (totais da abrangência, linhas por candidato)."""
    s, e, v = d["s"], d["e"], d["v"]
    totais = {
        "dt_totalizacao": f"{d['dt']} {d['ht']}",
        "secoes_total": int(s["ts"]),
        "secoes_totalizadas": int(s["st"]),
        "eleitores_aptos": int(e["te"]),
        "comparecimento": int(e["c"]),
        "abstencao": int(e["a"]),
        "votos_totais": int(v["tv"]),
        "votos_validos": int(v["vv"]),
        "votos_brancos": int(v["vb"]),
        "votos_nulos": int(v["tvn"]),
        "pct_comparecimento": num(e["pcn"]),
        "pct_abstencao": num(e["pan"]),
        "pct_brancos": num(v["pvbn"]),
        "pct_nulos": num(v["ptvnn"]),
    }
    candidatos = []
    for cargo in d["carg"]:
        for agr in cargo["agr"]:
            for par in agr["par"]:
                for c in par["cand"]:
                    candidatos.append(
                        {
                            "nr_candidato": int(c["n"]),
                            "nm_urna": c["nmu"],
                            "nm_candidato": c["nm"],
                            "sg_partido": par["sg"],
                            "nm_coligacao": agr["nm"],
                            "situacao": c["st"],
                            "votos": int(c["vap"]),
                            "pct_validos": num(c["pvapn"]),
                        }
                    )
    return totais, candidatos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="ignora o cache e rebaixa tudo")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    cfg = fetch_json(f"{BASE}/config/mun-{E}-cm.json", RAW / "config" / "mun-cm.json", args.refresh)
    municipios = [
        {
            "sg_uf": uf["cd"].upper(),
            "nm_uf": uf["ds"],
            "cd_municipio_tse": mu["cd"],
            "cd_municipio_ibge": mu["cdi"] or None,
            "nm_municipio": mu["nm"],
            "capital": mu["c"] == "s",
            "zonas": mu["z"],
        }
        for uf in cfg["abr"]
        for mu in uf["mu"]
    ]
    ufs = sorted({m["sg_uf"].lower() for m in municipios})

    # Tarefas: Brasil, cada UF e cada município (ZZ = exterior, "municípios" são cidades no exterior)
    tarefas: dict[tuple[str, str], tuple[str, Path]] = {}
    for abr in ["br", *ufs]:
        tarefas[("uf", abr)] = (
            f"{BASE}/dados/{abr}/{abr}-c0001-{E}-u.json",
            RAW / abr / f"{abr}-c0001-{E}-u.json",
        )
    for m in municipios:
        uf, cd = m["sg_uf"].lower(), m["cd_municipio_tse"]
        tarefas[("mu", cd)] = (
            f"{BASE}/dados/{uf}/{uf}{cd}-c0001-{E}-u.json",
            RAW / uf / f"{uf}{cd}-c0001-{E}-u.json",
        )

    resultados: dict[tuple[str, str], dict] = {}
    falhas = []
    with ThreadPoolExecutor(args.workers) as pool:
        futs = {pool.submit(fetch_json, url, dest, args.refresh): k for k, (url, dest) in tarefas.items()}
        for i, fut in enumerate(as_completed(futs), 1):
            k = futs[fut]
            try:
                resultados[k] = fut.result()
            except Exception as exc:  # noqa: BLE001
                falhas.append((k, tarefas[k][0], repr(exc)))
            if i % 500 == 0 or i == len(futs):
                print(f"{i}/{len(futs)} arquivos", flush=True)

    # Municípios
    linhas_cand, linhas_mun = [], []
    for m in municipios:
        d = resultados.get(("mu", m["cd_municipio_tse"]))
        if d is None:
            continue
        totais, cands = parse_resultado(d)
        base = {k: v for k, v in m.items() if k != "zonas"}
        linhas_mun.append({**base, "n_zonas": len(m["zonas"]), **totais})
        linhas_cand += [{**base, **c} for c in cands]

    # UFs + Brasil
    linhas_uf_cand, linhas_uf = [], []
    for abr in ["br", *ufs]:
        d = resultados.get(("uf", abr))
        if d is None:
            continue
        totais, cands = parse_resultado(d)
        linhas_uf.append({"sg_uf": abr.upper(), **totais})
        linhas_uf_cand += [{"sg_uf": abr.upper(), **c} for c in cands]

    OUT.mkdir(parents=True, exist_ok=True)
    mun_cand = pl.DataFrame(linhas_cand)
    mun = pl.DataFrame(linhas_mun)

    # Tabela larga: uma linha por município com votos de cada candidato lado a lado
    votos_wide = mun_cand.pivot(
        on="nm_urna", index="cd_municipio_tse", values="votos", aggregate_function="first"
    ).rename(lambda c: c if c == "cd_municipio_tse" else "votos_" + c.lower().replace(" ", "_"))
    mun_wide = mun.join(votos_wide, on="cd_municipio_tse", how="left")

    saidas = {
        "municipio_candidato.parquet": mun_cand,
        "municipio.parquet": mun_wide,
        "uf_candidato.parquet": pl.DataFrame(linhas_uf_cand),
        "uf.parquet": pl.DataFrame(linhas_uf),
    }
    for nome, df in saidas.items():
        df.write_parquet(OUT / nome)
        print(f"{OUT / nome}: {df.shape}")

    # Checagem: soma dos municípios bate com o total Brasil?
    br = next(r for r in linhas_uf if r["sg_uf"] == "BR")
    soma = mun.select(pl.col("votos_validos", "comparecimento", "eleitores_aptos").sum()).row(0, named=True)
    for col, total in soma.items():
        status = "OK" if total == br[col] else f"DIVERGE (BR={br[col]})"
        print(f"soma municípios {col}={total} {status}")

    if falhas:
        print(f"\n{len(falhas)} falhas:")
        for k, url, err in falhas[:20]:
            print(" ", k, url, err)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
