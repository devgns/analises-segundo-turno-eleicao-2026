# Replicação independente: modelos de urna

Execute na raiz do repositório: `UV_NO_ENV_FILE=1 uv run python analises/replicacao_codex/replicar.py`.

Participação bruta: soma dos votos de Lula dividida pela soma dos votos válidos. Os dados excluem ZZ e seções sem serial numérico positivo, votos válidos positivos, votos de Lula válidos ou chave completa; as contagens de exclusões estão no JSON. Modelos são classificados pelos limites de serial especificados na tarefa.

A regressão pondera pela quantidade de votos válidos e absorve efeitos fixos de UF, município, zona e local de votação. UE2020 é a referência. Erros padrão são agrupados por UF e município, com correção CR1 G/(G−1) × (N−1)/(N−F−K), onde F é o número de locais e K o número de dummies. IC 95% usa quantil normal 1,959964. Locais com um único modelo não identificam coeficientes, mas entram nas contagens e nos graus de liberdade. Modelos sem coeficiente identificável são omitidos da regressão e marcados com travessão. Coeficientes são pontos percentuais (pp).

Em 2026 no N+NE, o vínculo direto UE2015–UE2020 ocorre em apenas três locais de um município; não há local com UE2013 e UE2020. Portanto, os contrastes dos modelos antigos com UE2020 dependem dessa conexão escassa, e seus ICs agrupados podem ser pouco confiáveis; o intervalo arredondado de UE2015 não indica precisão real. O JSON inclui as contagens de coocorrência para cada par de modelos.

## 2022

| Região | Modelo | Lula (% dos válidos) |
|---|---|---:|
| Brasil | antiga (UE2009-2011) | 53.00 |
| Brasil | UE2013 | 51.23 |
| Brasil | UE2015 | 51.57 |
| Brasil | UE2020 | 48.95 |
| Brasil | UE2022 | — |
| N | antiga (UE2009-2011) | 50.20 |
| N | UE2013 | 45.43 |
| N | UE2015 | 55.38 |
| N | UE2020 | 46.41 |
| N | UE2022 | — |
| NE | antiga (UE2009-2011) | 75.08 |
| NE | UE2013 | 72.89 |
| NE | UE2015 | 74.04 |
| NE | UE2020 | 62.90 |
| NE | UE2022 | — |
| CO | antiga (UE2009-2011) | 39.59 |
| CO | UE2013 | 41.30 |
| CO | UE2015 | 41.80 |
| CO | UE2020 | 39.10 |
| CO | UE2022 | — |
| SE | antiga (UE2009-2011) | 46.19 |
| SE | UE2013 | 47.38 |
| SE | UE2015 | 45.56 |
| SE | UE2020 | 45.27 |
| SE | UE2022 | — |
| S | antiga (UE2009-2011) | 38.51 |
| S | UE2013 | 35.09 |
| S | UE2015 | 36.57 |
| S | UE2020 | 39.07 |
| S | UE2022 | — |

| Amostra | Seções | Locais com ≥2 modelos | Modelo | Diferença (pp) | IC 95% (pp) |
|---|---:|---:|---|---:|---:|
| Brasil | 471010 | 6744 | antiga (UE2009-2011) | 0.28 | [-0.29, 0.85] |
| Brasil | 471010 | 6744 | UE2013 | 0.37 | [-0.25, 0.99] |
| Brasil | 471010 | 6744 | UE2015 | 0.33 | [-0.26, 0.91] |
| Brasil | 471010 | 6744 | UE2022 | — | — |
| N+NE | 171553 | 2338 | antiga (UE2009-2011) | -0.59 | [-1.24, 0.06] |
| N+NE | 171553 | 2338 | UE2013 | -0.52 | [-1.24, 0.20] |
| N+NE | 171553 | 2338 | UE2015 | -0.60 | [-1.23, 0.03] |
| N+NE | 171553 | 2338 | UE2022 | — | — |
| Restante | 299457 | 4406 | antiga (UE2009-2011) | 0.29 | [-0.28, 0.86] |
| Restante | 299457 | 4406 | UE2013 | 0.39 | [-0.24, 1.02] |
| Restante | 299457 | 4406 | UE2015 | 0.35 | [-0.23, 0.94] |
| Restante | 299457 | 4406 | UE2022 | — | — |

## 2026

| Região | Modelo | Lula (% dos válidos) |
|---|---|---:|
| Brasil | antiga (UE2009-2011) | — |
| Brasil | UE2013 | 53.94 |
| Brasil | UE2015 | 51.96 |
| Brasil | UE2020 | 51.53 |
| Brasil | UE2022 | 51.83 |
| N | antiga (UE2009-2011) | — |
| N | UE2013 | 59.41 |
| N | UE2015 | 49.49 |
| N | UE2020 | 49.67 |
| N | UE2022 | 50.51 |
| NE | antiga (UE2009-2011) | — |
| NE | UE2013 | 70.40 |
| NE | UE2015 | 69.31 |
| NE | UE2020 | 68.80 |
| NE | UE2022 | 69.85 |
| CO | antiga (UE2009-2011) | — |
| CO | UE2013 | 41.69 |
| CO | UE2015 | 42.87 |
| CO | UE2020 | 40.16 |
| CO | UE2022 | 38.53 |
| SE | antiga (UE2009-2011) | — |
| SE | UE2013 | 47.75 |
| SE | UE2015 | 48.22 |
| SE | UE2020 | 47.26 |
| SE | UE2022 | 46.74 |
| S | antiga (UE2009-2011) | — |
| S | UE2013 | 33.97 |
| S | UE2015 | 33.39 |
| S | UE2020 | 38.18 |
| S | UE2022 | 38.58 |

| Amostra | Seções | Locais com ≥2 modelos | Modelo | Diferença (pp) | IC 95% (pp) |
|---|---:|---:|---|---:|---:|
| Brasil | 497897 | 8497 | antiga (UE2009-2011) | — | — |
| Brasil | 497897 | 8497 | UE2013 | 0.76 | [0.08, 1.45] |
| Brasil | 497897 | 8497 | UE2015 | 0.57 | [-0.05, 1.20] |
| Brasil | 497897 | 8497 | UE2022 | -0.04 | [-0.12, 0.05] |
| N+NE | 184597 | 3417 | antiga (UE2009-2011) | — | — |
| N+NE | 184597 | 3417 | UE2013 | 2.39 | [2.15, 2.62] |
| N+NE | 184597 | 3417 | UE2015 | 2.31 | [2.31, 2.31] |
| N+NE | 184597 | 3417 | UE2022 | -0.12 | [-0.25, 0.02] |
| Restante | 313300 | 5080 | antiga (UE2009-2011) | — | — |
| Restante | 313300 | 5080 | UE2013 | 0.75 | [0.04, 1.46] |
| Restante | 313300 | 5080 | UE2015 | 0.50 | [-0.12, 1.13] |
| Restante | 313300 | 5080 | UE2022 | 0.00 | [-0.11, 0.12] |
