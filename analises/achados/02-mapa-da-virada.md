# 02 — O mapa da virada: deslocamento uniforme entre turnos? (2026 vs 2022)

- **Script:** `analises/02_mapa_virada.py` (cerca de 25 s). Números em `analises/achados/dados/02-mapa-da-virada.json`.
- **Dados do site:** `site/public/data/ch02/*.json`. GeoJSON em `site/public/data/geo/br-municipios.json`.
- **Capítulo:** `site/src/capitulos/02-mapa-da-virada.{html,js}`.

## Veredito proposto: `inconclusiva`

> Placar sugerido. **Pista:** "Um deslocamento quase uniforme em todo o país 'moveu a média' e escondeu fraudes locais." **Resumo:** "O componente comum existe (+1,75 p.p. a favor de Lula), mas é do mesmo tamanho do de 2022 (−2,08 p.p., a favor de Bolsonaro), e 2026 não foi mais uniforme que 2022. Contagens de votos não distinguem esse componente de uma alteração uniforme."

**Justificativa:**
- O protocolo diz que um deslocamento uniforme é indistinguível de comportamento real usando só 2026.
- A comparação com 2022 não mostra excesso: o intercepto tem a mesma magnitude, a dispersão é maior e não menor, e a fração na direção nacional é igual.
- Logo, nada sustenta a tese. Mas o teste também não consegue refutá-la na forma "alteração uniforme de ≤ 2 p.p.".
- As subalegações (contagem de municípios e Sul) conferem nos números e têm espelho exato em 2022. Como "indício de anomalia", ficam **refutadas**.
- Se o integrador quiser separar: contagem de municípios e Sul `refutada`, tese central `inconclusiva`.

## Testes e números-chave

Linha de base: 2022. Os testes foram definidos antes de olhar os resultados.

### A. "5.378 × 184"

Municípios: 5.571 em 2026 e 5.570 em 2022, sem o exterior.

| Métrica | 2026 Lula | 2026 Flávio | 2022 Lula | 2022 Bolsonaro |
|---|---|---|---|---|
| Ganhou votos nominais | 5.491 | 4.624 | 4.561 | 5.476 |
| Perdeu votos nominais | 79 | 938 | 982 | 92 |
| Maior ganho absoluto | 5.228 | 339 | 715 | 4.849 |
| Ganhou fatia entre finalistas | 5.411 | 160 | 114 | 5.456 |
| Melhorou margem sobre válidos | 5.389 | 182 | 923 | 4.647 |

Nenhuma métrica dá exatamente 5.378 × 184. A mais próxima é a margem sobre válidos (5.389 × 182). Na métrica de fatia, a "quase unanimidade" é igual em 2022: 98,0% para Bolsonaro contra 97,1% para Lula em 2026.

### B. Uniformidade da Δfatia de Lula entre finalistas

Valores sem ponderação. Seções com ≥ 50 votos em finalistas.

| | Média | DP | IQR | Na direção nacional |
|---|---|---|---|---|
| Municípios 2026 | +2,34 p.p. | 1,25 | 1,74 | 97,1% |
| Municípios 2022 | −1,85 p.p. | 1,02 | 1,26 | 98,0% |
| Seções 2026 (497.002) | +2,91 | 2,36 | 3,08 | 89,8% |
| Seções 2022 (470.134) | −1,64 | 2,19 | 2,83 | 77,9% |

- **2026 não é mais uniforme.** A dispersão municipal é maior.
- Nas seções, a fração maior na direção nacional vem da média maior: o DP é semelhante.
- A correlação entre Δ municipal 2026 e Δ 2022 é **0,008**: a geografia não se repete.
- Por região (municípios, média 2026): N +2,09, NE +1,56, CO +2,79, SE +2,95, Sul +2,59.
- Mesma medida em 2022: N −1,77, NE −1,51, CO −1,99, SE −1,83, Sul −2,36.

### C. Componente comum (intercepto)

**Modelo** (WLS, peso = votos dos finalistas no 1º t., erros HC1):
- Δfatia ~ o + dc + dbn + s + o·s + dc·s + dbn·s + região (soma zero).
- o = eliminados/finalistas₁; dc = Δcomp/finalistas₁; dbn = queda de BN/finalistas₁; s = fatia₁ − 0,5.

**Derivação:** Δfatia ≈ troca_líquida + (λ − fatia₁)·reservatório. O intercepto é a troca líquida direta entre finalistas por voto de finalista, num local sem reservatório e com fatia de 50%.

| | Intercepto | IC 95% | R² | DP residual (pond.) |
|---|---|---|---|---|
| Municípios 2026 | **+1,75 p.p.** | [+1,55; +1,94] | 0,65 | 0,65 p.p. |
| Municípios 2022 | **−2,08 p.p.** | [−2,23; −1,92] | 0,41 | 0,63 p.p. |
| Seções 2026 | +1,86 | [+1,84; +1,88] | 0,21 | 2,04 |
| Seções 2022 | −2,11 | [−2,13; −2,10] | 0,17 | 1,93 |
| Sem região, municípios | +1,85 / −1,88 | | | |

- **Por região, 2026:** N +1,02, NE +1,83, CO +3,01, SE +2,34, Sul +1,03.
- **Por região, 2022:** N −1,72, NE −1,89, CO −3,55, SE −1,63, Sul −3,25.
- **Magnitude:** +1,75 p.p. ≈ 1,9 mi de troca líquida Flávio→Lula, ou rotatividade diferencial equivalente. Em 2022, ≈ 2,25 mi Lula→Bolsonaro.

**Para onde foram os reservatórios** (taxa implícita para Lula num município 50/50):

| | 2026 | 2022 |
|---|---|---|
| Novos votantes (Δcomp) | ≈ 48% (mun.) a 53% (seção), seguindo a inclinação local | ≈ 52% |
| Ex-brancos/nulos | **≈ 76% (mun.) / 71% (seção)** | ≈ 55% |

- Os novos votantes não favoreceram Lula desproporcionalmente. Isso é evidência contra a hipótese de inflar votos via comparecimento.
- Os ex-brancos/nulos favoreceram Lula. É um traço específico de 2026, com estimativa ecológica.

**Goodman** (`ch02/goodman.json`, não usado no site):
- Estima Flávio→Lula de −3,5% e Lula→Flávio de −4,7%.
- Também estima BN₁→Lula de 102% (municípios). Instável: ilustra os limites da inferência ecológica.

**Caudas dos resíduos (municípios, |resíduo| > 3 p.p.):**
- 2026: 54 (9 a favor de Lula, 45 contra).
- 2022: 32 (5 a favor de Lula, 27 contra).
- Retirado o componente comum, os atípicos de 2026 pendem contra Lula.

**Casos mais suspeitos** (maior resíduo a favor de Lula, 2026):

| Município | Eleitores | Δ Lula | Δ Flávio | Δfatia | Resíduo | Δfatia 2022 |
|---|---|---|---|---|---|---|
| Rafael Godeiro/RN | 3.668 | +314 | −280 | +10,19 p.p. | +7,88 | −4,00 |
| Pracuúba/AP | 4.022 | −132 | −469 | +7,36 | +4,68 | −3,14 |
| Paranhos/MS | 9.430 | +896 | +4 | +5,98 | +4,22 | −1,33 |
| São Tomé/RN | 9.586 | +613 | −302 | +6,09 | +4,01 | −0,49 |
| Lajes Pintadas/RN | 5.231 | +357 | −170 | +5,50 | +3,71 | +0,09 |

- **Maiores resíduos contra Lula:** Belo Monte/AL (−10,9), Santo Antônio de Lisboa/PI (−9,2), Uirapuru/GO (−6,1).
- **Ressalva:** não houve correção formal para múltiplas comparações sobre o resíduo. São extremos entre 5.571 e servem como lista de inspeção, não como evidência.
- **9 municípios do RJ:**
  - Δfatia bruta entre os percentis 78 e 99,9.
  - Resíduo entre os percentis 51 e 98,9.
  - Campos é o maior (98,9).
  - Detalhe no cap. 4.

### D. Sul

**2026:**
- Lula ganhou votos nos 1.191 municípios; Flávio, em 1.187 (PR 397/399, SC 294/295, RS 496/497).
- ΔLula +1.332.846; ΔFlávio +866.745 (confere com as alegações).
- Δfatia: PR +3,18, SC +3,27, RS +3,06, Sul +3,19 p.p.

**2022 (espelho):**
- Bolsonaro ganhou votos nos 1.191 municípios; Lula, em 981.
- ΔBolsonaro +1.372.117; ΔLula +300.994.
- Δfatia de Lula: −2,11 p.p.

## O que não exclui

- Uma alteração uniforme de até ~2 p.p. é indistinguível de comportamento real com contagens de votos.
- Se 2022 também tivesse alteração, a comparação não revelaria nenhuma das duas.
- O intercepto é extrapolação (não há município sem eliminados). Especificações alternativas o movem em décimos de ponto.

## Sugestões ao integrador

- **Componentes:** nenhuma alteração necessária.
- **Bug encontrado e contornado:** `data-tabela="false"` numa `<figure>` (como sugere o CONTRIBUTING) colide com o seletor de slot de tabela `[data-tabela]`. O console mostra "não exporta tabelas['false']". Contornei passando `tabela: false` no objeto JS. Sugestão: documentar assim, ou fazer `capitulos.js` ignorar `figure[data-tabela]`.
- **Malha:** a do IBGE tem 5.570 polígonos. Falta Boa Esperança do Norte/MT.
  - Bruto: `data/raw/geo/ibge-malha-municipios/br_municipios_qualidade_minima.geojson`.
  - Simplificado: Douglas-Peucker com 0,012° e 3 casas decimais → 2,49 MB.
  - Propriedades: `codigo_ibge` e `nome`.
- **Tamanho:** `ch02/municipios.json` tem 1,3 MB (5.571 linhas, chaves curtas). Acima do ideal de 1 MB, mas fica em ~0,3 MB com gzip.

## Fontes (ids para fontes.json)

- `tse-boletins` (já existe) e `tse-boletins-2022` (nova; ver achados 01).
- `{id: "ibge-malhas", titulo: "IBGE — API de Malhas Territoriais v3, municípios do Brasil, qualidade mínima", url: "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=municipio&formato=application/vnd.geo+json&qualidade=minima", acesso: "2026-10-29"}` (**nova**).
