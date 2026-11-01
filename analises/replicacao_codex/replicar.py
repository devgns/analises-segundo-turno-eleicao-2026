#!/usr/bin/env python3
"""Reproduce comparisons from the section parquet files; run from the repo root."""
import json
from pathlib import Path

import numpy as np
import polars as pl
from scipy.linalg import qr

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REGIONS = {
    'N': 'AC AM AP PA RO RR TO'.split(),
    'NE': 'AL BA CE MA PB PE PI RN SE'.split(),
    'CO': 'DF GO MS MT'.split(),
    'SE': 'ES MG RJ SP'.split(),
    'S': 'PR RS SC'.split(),
}
UF_REGION = {uf: region for region, ufs in REGIONS.items() for uf in ufs}
MODELS = ['antiga (UE2009-2011)', 'UE2013', 'UE2015', 'UE2020', 'UE2022']
TARGETS = [0, 1, 2, 4]
KEY = ['sg_uf', 'cd_municipio_tse', 'zona', 'nr_local_votacao']
COLS = ['cd_municipio_tse', 'zona', 'secao', 'nr_local_votacao',
        'nr_urna_efetivada', 'votos_13', 'votos_22', 'votos_validos']


def load(year):
    base = ROOT / f'data/processed/bweb_secao/ano={year}/turno=2'
    parts = []
    for uf, region in UF_REGION.items():
        path = base / f'sg_uf={uf}' / 'part-0000.parquet'
        if not path.is_file():
            raise FileNotFoundError(path)
        parts.append(pl.read_parquet(path, columns=COLS).with_columns(
            pl.lit(uf).alias('sg_uf'), pl.lit(region).alias('regiao')))
    df = pl.concat(parts).with_columns(
        pl.col('nr_urna_efetivada').cast(pl.Int64, strict=False).alias('serial'))
    df = df.with_columns(
        pl.when(pl.col('serial') < 1650000).then(0)
        .when(pl.col('serial') < 1750000).then(1)
        .when(pl.col('serial') < 2000000).then(2)
        .when(pl.col('serial') < 2250000).then(3)
        .otherwise(4).alias('modelo_id'))
    # A null serial must never be interpreted as UE2022.
    valid = (pl.col('serial').is_not_null() & (pl.col('serial') > 0)
             & pl.col('votos_validos').is_not_null() & (pl.col('votos_validos') > 0)
             & pl.col('votos_13').is_not_null()
             & (pl.col('votos_13') >= 0) & (pl.col('votos_13') <= pl.col('votos_validos')))
    for col in KEY + ['secao']:
        valid &= pl.col(col).is_not_null() & (pl.col(col).str.strip_chars() != '')
    usable = df.filter(valid)
    duplicates = usable.group_by(['sg_uf', 'cd_municipio_tse', 'zona', 'secao']).len().filter(pl.col('len') > 1)
    if duplicates.height:
        raise ValueError(f'{year}: {duplicates.height} duplicate section keys')
    return usable, {'linhas_entrada_sem_ZZ': df.height, 'linhas_excluidas': df.height - usable.height}


def raw(df):
    result = []
    for region in ['Brasil', *REGIONS]:
        subset = df if region == 'Brasil' else df.filter(pl.col('regiao') == region)
        for idx, name in enumerate(MODELS):
            rows = subset.filter(pl.col('modelo_id') == idx)
            votes = rows['votos_validos'].sum()
            lula = rows['votos_13'].sum()
            result.append({'regiao': region, 'modelo': name, 'secoes': rows.height,
                           'votos_lula': lula, 'votos_validos': votes,
                           'percentual_lula': 100 * lula / votes if votes else None})
    return result


def regression(df):
    # Group IDs are formed from the complete composite keys, preserving UF boundaries.
    df = df.with_columns(pl.struct(KEY).rank('dense').cast(pl.Int64).alias('place'),
                         pl.struct(['sg_uf', 'cd_municipio_tse']).rank('dense').cast(pl.Int64).alias('municipio'))
    place = df['place'].to_numpy() - 1
    municipality = df['municipio'].to_numpy() - 1
    model = df['modelo_id'].to_numpy()
    w = df['votos_validos'].to_numpy().astype(float)
    y = df['votos_13'].to_numpy() / w
    x = np.column_stack([model == k for k in TARGETS]).astype(float)
    n, k = x.shape
    f, g = int(place.max() + 1), int(municipality.max() + 1)
    sw = np.bincount(place, weights=w, minlength=f)
    y = y - np.bincount(place, weights=w*y, minlength=f)[place] / sw[place]
    for j in range(k):
        x[:, j] -= np.bincount(place, weights=w*x[:, j], minlength=f)[place] / sw[place]
    cross = x.T @ (w[:, None] * x)
    _, r, pivot = qr(cross, pivoting=True)
    rank = np.linalg.matrix_rank(cross)
    selected = sorted(pivot[:rank].tolist())
    if any(cross[j, j] > 1e-8 for j in range(k) if j not in selected):
        raise ValueError('Nonzero model dummies are collinear; reference contrasts are ambiguous')
    x = x[:, selected]
    cross = cross[np.ix_(selected, selected)]
    k = rank
    bread = np.linalg.inv(cross)
    beta = bread @ (x.T @ (w*y))
    resid = y - x @ beta
    scores = np.column_stack([np.bincount(municipality, weights=w*x[:, j]*resid, minlength=g)
                              for j in range(k)])
    # CR1, counting all absorbed place effects in the residual degrees of freedom.
    correction = g/(g-1) * (n-1)/(n-f-k)
    cov = correction * bread @ (scores.T @ scores) @ bread
    se = np.sqrt(np.diag(cov))
    multi = df.group_by(KEY).agg(pl.col('modelo_id').n_unique().alias('modelos')).filter(pl.col('modelos') >= 2).height
    sets = df.group_by(KEY).agg(pl.col('modelo_id').unique().alias('modelos'))
    pairs = []
    for a in range(len(MODELS)):
        for b in range(a + 1, len(MODELS)):
            both = sets.filter(pl.col('modelos').list.contains(a) & pl.col('modelos').list.contains(b))
            pairs.append({'modelos': [MODELS[a], MODELS[b]], 'locais': both.height,
                          'municipios': both.select(['sg_uf', 'cd_municipio_tse']).unique().height})
    return {'secoes': n, 'locais': f, 'locais_com_dois_ou_mais_modelos': multi,
            'municipios_clusters': g, 'correcao_cr1': correction,
            'coocorrencias_modelos': pairs,
            'coeficientes': [dict(modelo=MODELS[idx],
                                  coef_pp=float(100*beta[selected.index(j)]) if j in selected else None,
                                  erro_padrao_pp=float(100*se[selected.index(j)]) if j in selected else None,
                                  ic95_pp=[float(100*(beta[selected.index(j)] + sign*1.959963984540054*se[selected.index(j)])) for sign in (-1, 1)] if j in selected else None)
                              for j, idx in enumerate(TARGETS)]}


def fmt(x):
    return '—' if x is None else f'{x:.2f}'


def readme(results):
    lines = ['# Replicação independente: modelos de urna', '',
             'Execute na raiz do repositório: `UV_NO_ENV_FILE=1 uv run python analises/replicacao_codex/replicar.py`.', '',
             'Participação bruta: soma dos votos de Lula dividida pela soma dos votos válidos. '
             'Os dados excluem ZZ e seções sem serial numérico positivo, votos válidos positivos, '
             'votos de Lula válidos ou chave completa; as contagens de exclusões estão no JSON. '
             'Modelos são classificados pelos limites de serial especificados na tarefa.', '',
             'A regressão pondera pela quantidade de votos válidos e absorve efeitos fixos de '
             'UF, município, zona e local de votação. UE2020 é a referência. Erros padrão '
             'são agrupados por UF e município, com correção CR1 G/(G−1) × (N−1)/(N−F−K), '
             'onde F é o número de locais e K o número de dummies. IC 95% usa quantil normal '
             '1,959964. Locais com um único modelo não identificam coeficientes, mas entram '
             'nas contagens e nos graus de liberdade. Modelos sem coeficiente identificável são '
             'omitidos da regressão e marcados com travessão. Coeficientes são pontos percentuais (pp).', '']
    lines += ['Em 2026 no N+NE, o vínculo direto UE2015–UE2020 ocorre em apenas três locais '
              'de um município; não há local com UE2013 e UE2020. Portanto, os contrastes dos '
              'modelos antigos com UE2020 dependem dessa conexão escassa, e seus ICs agrupados '
              'podem ser pouco confiáveis; o intervalo arredondado de UE2015 não indica precisão real. '
              'O JSON inclui as contagens de coocorrência para cada par de modelos.', '']
    for year, result in results.items():
        lines += [f'## {year}', '', '| Região | Modelo | Lula (% dos válidos) |', '|---|---|---:|']
        for row in result['bruto']:
            lines.append(f"| {row['regiao']} | {row['modelo']} | {fmt(row['percentual_lula'])} |")
        lines += ['', '| Amostra | Seções | Locais com ≥2 modelos | Modelo | Diferença (pp) | IC 95% (pp) |', '|---|---:|---:|---|---:|---:|']
        for group, reg in result['regressoes'].items():
            for c in reg['coeficientes']:
                ci = f"[{c['ic95_pp'][0]:.2f}, {c['ic95_pp'][1]:.2f}]" if c['ic95_pp'] else '—'
                lines.append(f"| {group} | {reg['secoes']} | {reg['locais_com_dois_ou_mais_modelos']} | {c['modelo']} | {fmt(c['coef_pp'])} | {ci} |")
        lines.append('')
    (OUT / 'README.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    results = {}
    for year in (2022, 2026):
        df, audit = load(year)
        groups = {'Brasil': df, 'N+NE': df.filter(pl.col('regiao').is_in(['N', 'NE'])),
                  'Restante': df.filter(~pl.col('regiao').is_in(['N', 'NE']))}
        results[str(year)] = {'auditoria': audit, 'bruto': raw(df),
                              'regressoes': {name: regression(part) for name, part in groups.items()}}
        print(year, audit, flush=True)
    (OUT / 'resultado.json').write_text(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    readme(results)


if __name__ == '__main__':
    main()
