# 01 — A conta nacional: de onde vieram os 10,4 milhões de votos de Lula

- **Script:** `analises/01_conta_nacional.py` (roda do zero em cerca de 5 s). Números completos em `analises/achados/dados/01-conta-nacional.json`.
- **Dados do site:** `site/public/data/ch01/*.json`.
- **Capítulo:** `site/src/capitulos/01-conta-nacional.{html,js}`.

## Veredito proposto: `refutada`

> Placar sugerido. **Pista:** "Os 10,4 milhões de votos a mais de Lula no 2º turno não têm origem aritmética plausível." **Resumo:** "A conta fecha voto a voto nos 1,94 milhão de boletins de 2022 e 2026. O excedente de 1,06 mi sobre os eliminados vem do comparecimento (+2,96 mi) e da queda de brancos e nulos (−1,82 mi). A migração mínima exigida por seção (147 mil) é o espelho da de 2022 (77 mil, no sentido inverso)."

**Justificativa:**
- A suspeita contábil está refutada: os resíduos das alegações não existem nos dados oficiais.
- Na conta nacional, o ganho de Lula de fato excede os eliminados. Mas a identidade fecha sem exigir nenhuma migração nacional Flávio→Lula.
- Por seção, existe uma migração mínima obrigatória. Ela tem o mesmo padrão de 2022, com sinal trocado e magnitude 1,9× maior (cerca de 1,3× por p.p. de virada). É diferença de grau, não de natureza.
- Fica um traço genuinamente distinto: o aumento de comparecimento entre turnos (+2,96 mi, 5,2× o de 2022). Ele aparece no texto como ponto em aberto.
- Se o integrador preferir `parcial` por esse traço, a justificativa também se sustenta. Recomendo `refutada` porque a pista tal como formulada ("sem origem aritmética") é contradita pelo teste.

## Pistas e testes

### a base derivada não fecha

**Teste:** verificar as identidades em cada BU do BWeb, nos 4 conjuntos (2026 t1/t2, 2022 t1/t2):
- comp = válidos + brancos + nulos;
- válidos = Σ nominais;
- aptos ≥ comp;
- abstenção = aptos − comp.

Depois, somar as seções dos municípios do RJ.

**Resultado:**
- **0 violações** em 499.206 + 499.205 + 472.028 + 472.028 = **1.942.467 BUs**. A soma do resíduo R é 0 em todos.
- Particularidade: em 2026 t1, `votos_validos` do BWeb inclui os 5.246 votos do candidato 28 (anulado). `comum.py` os move para nulos, como o painel.
- Resíduo oficial no 2º turno = **0** em todos os municípios da tabela das alegações. A diferença está toda no CSV derivado que circulou. Os ΔLula e ΔFlávio somados das seções batem exatamente com os das alegações.

| Município | R no CSV derivado que circulou | R oficial |
|---|---|---|
| Campos dos Goytacazes | +3 | 0 |
| Araruama | +2 | 0 |
| Búzios | −9 | 0 |
| Arraial do Cabo | −2 | 0 |
| Cabo Frio | +98 | 0 |
| Iguaba Grande | −10 | 0 |
| São Pedro da Aldeia | −2 | 0 |
| Saquarema | −6 | 0 |

**"499.205 seções" (conta que circulou):** confere.
- 499.206 seções no t1 e 499.205 no t2, todas pareadas.
- A única seção só no t1 é ZZ 30686, zona 0001, seção 0443 (30 aptos, 2 votantes).
- As 16.142 seções agregadas são idênticas nos dois turnos.

**Pequena divergência com a conta que circulou:** ela dá eleitorado de 158.745.502. A soma dos BUs dá 158.745.007 no t1 e 158.744.977 no t2.
- A diferença de 495 provavelmente é a definição de eleitorado do painel.
- O comparecimento bate exatamente.

### conta nacional (2026 vs 2022)

| | 2026 | 2022 |
|---|---|---|
| Δ Lula | +10.376.694 | +3.086.495 |
| Δ adversário | +3.721.538 | +7.134.009 |
| Eliminados (1º t.) | 9.316.747 | 9.897.870 |
| Δ comparecimento | **+2.960.239** | +570.424 |
| Δ (brancos + nulos) | −1.821.246 | +247.790 |
| Fatia de Lula entre finalistas | 48,99% → 51,79% (+2,80 p.p.) | 52,86% → 50,90% (−1,95 p.p.) |
| Ganho de quem estava atrás ÷ eliminados | 111,4% | 72,1% |
| Ganho de quem estava atrás − eliminados | +1.059.947 | −2.763.861 |
| Fatia do ganho conjunto para quem estava atrás | 73,6% | 69,8% |

A identidade ΔL + ΔA = eliminados + Δcomp − ΔBN fecha exatamente nos dois anos.

### Reservatório por seção e migração direta mínima

**Fato-chave:** numa seção, "ganho de Lula > eliminados + Δcomp − ΔBN" equivale exatamente a "ΔFlávio < 0".

| | 2026 | 2022 |
|---|---|---|
| Seções em que o adversário de Lula perdeu votos | 82.180 (16,5%) | 14.700 (3,1%) |
| Seções em que Lula perdeu votos | 9.590 (1,9%) | 88.977 (18,8%) |
| Perda ≥ 10 votos (quem perdeu fatia) | 8.366 (Flávio) | 11.920 (Lula) |
| Migração mínima Adv→Lula (Σ seções) | **147.362** (44.900 seções) | 3.658 |
| Migração mínima Lula→Adv (Σ seções) | 1.646 | **77.499** (24.869 seções) |
| Mesma soma, nível município | 15.643 | 3.470 |
| Nível UF / Brasil | 0 / 0 | 0 / 0 |
| Limite "com rotatividade total" | 20 | 29 |

- **Fórmula** (hipótese sem rotatividade): max(0, ΔL − O1 − max(0,Δcomp) − max(0,−ΔBN)).
- **Razão 2026/2022:** 1,90 em valor bruto e cerca de 1,33 por p.p. de virada (52,7 mil vs 39,7 mil por p.p.).
- **Casos mais suspeitos** (maior migração mínima Flávio→Lula; `ch01/secoes-maior-perda-flavio.json`):
  - Santa Rosa do Purus/AC, z3 s95: Lula 102→174, Flávio 105→47, mín. 55.
  - Barcelos/AM, z18 s37: mín. 39.
  - Rafael Godeiro/RN, z37: seções 77, 74, 72 e 79, com mín. de 21 a 26 cada.
  - São Gonçalo do Amarante/CE, z36 s54: 25.
  - Anapu/PA, z80 s254: 25.
- Rafael Godeiro aparece também como o maior resíduo municipal do cap. 2. Recomendo cruzar com logs (cap. 8) e com o cap. 9.

## O que não exclui

- A coerência interna dos BUs não prova correspondência com os votos digitados (alteração pré-BU).
- A migração mínima é um piso sob hipótese extrema. Com rotatividade, qualquer migração (inclusive 0) fecha a conta.
- O aumento de comparecimento (+2,96 mi) não foi comparado com a série histórica (2006–2018).

## Pendências

1. Série histórica de Δcomparecimento entre turnos (2006–2018) para dizer se +2,96 mi é inédito. **De memória, não verificado:** em 2014 e 2018 o comparecimento caiu entre turnos. Precisa de dados do TSE antes de publicar.
2. Cruzar o Δcomparecimento por seção com as habilitações nos logs do 2º turno (cap. 8). O 1º turno não tem logs.

## Fontes (ids para fontes.json)

- `{id: "tse-boletins", ...}` (já existe).
- `{id: "tse-boletins-2022", titulo: "TSE — Boletins de urna por seção, Eleições 2022, 1º e 2º turnos (BWeb)", url: "https://dadosabertos.tse.jus.br/", acesso: "2026-10-29"}` (**nova**, citada no cap. 1).
