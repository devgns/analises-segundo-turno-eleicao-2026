# Capítulo 10: Benford, dígitos e impressão digital

Script: `analises/10_benford.py`, com cerca de 25 min de execução e 200 simulações × 2 nulos × 18 testes. Grava em `site/public/data/ch10/*.json`.

O script reutiliza o nulo do cap. 9: carrega `09_extremos.py` via importlib e usa as funções `loo` e `rho_momentos`.

## Pista
O relatório que circulou nas redes diz que os totais por seção "violam Benford", sem mostrar números. As alegações pede que Benford só seja usado com nulo simulado.

## Teste
Dígitos analisados nos votos por seção de Lula e de Flávio (Bolsonaro em 2022), em três eleições: 2026 2º turno, 2026 1º turno e 2022 2º turno.
- 1º dígito (1BL), contagens ≥ 1.
- 2º dígito (2BL, Mebane), contagens ≥ 10.
- Último dígito, contagens ≥ 100.

Cada série é comparada com:
- **Benford teórico** (teste ingênuo): χ² e MAD.
- **Nulo simulado:** cada seção usa seu tamanho real e a proporção leave-one-out do seu local de votação. Há duas versões, binomial e beta-binomial (com a rho do cap. 9), com 200 eleições simuladas cada. Calculamos o χ² contra a média simulada, o valor-p pela distribuição simulada do χ² e a faixa de 95% de cada dígito.

Aplicamos também o teste ingênuo às eleições simuladas, que são honestas por construção.

Por fim, a impressão digital de Klimek et al. (2012): histograma 2D de comparecimento × fatia de Lula, células de 2 p.p.

## Números-chave

**Teste ingênuo.** Rejeita Benford em 100% das 200 eleições honestas simuladas, nos 18 testes e nos dois nulos.
- 1º dígito de Lula em 2026, 2º turno: χ² = 297.064, contra 290.163 de mediana nas eleições simuladas honestas.
- 2022, 2º turno: 288.854. 2026, 1º turno: 223.191.

**Contra o nulo beta-binomial, 2026 2º turno:**

| Dígito | Lula | Flávio |
|---|---|---|
| 1º dígito | χ² 139, p = 0,005 | χ² 15,2, p = 0,015 |
| 2BL | χ² 10,7, p = 0,16 | χ² 12,6, p = 0,11 |
| Último dígito | χ² 6,4, p = 0,68 | χ² 11,4, p = 0,23 |

**Linhas de base no 1º dígito (Lula):** 2026 1º turno, χ² 198; 2022 2º turno, χ² 162. As duas são maiores que em 2026 2º turno.
- No 2BL e no último dígito, nenhum dos 12 testes rejeita a 1%. O único p < 0,05 é o 2BL de Lula em 2022 (p = 0,045).

**MAD do 1º dígito, Lula 2026 2º turno:** 0,0011 contra o nulo e 0,079 contra Benford.

**Média do 2BL (Mebane), Lula:**
- 2026: 3,858, com faixa simulada de 3,859 a 3,870.
- 2022: 3,853, com faixa de 3,857 a 3,867.
- As duas eleições ficam na borda inferior, igualmente.

**Impressão digital:**

| | 2026 2º t. | 2026 1º t. | 2022 2º t. |
|---|---|---|---|
| corr(comparecimento, fatia de Lula) | 0,046 | 0,064 | −0,086 |
| Seções com comparecimento ≥ 95% | 639 | 559 | 232 |
| … e Lula ≥ 95% | 64 | 26 | 31 |
| … e Flávio/Bolsonaro ≥ 95% | 2 | 3 | 2 |

As 64 seções de 2026 2º turno (`klimek-2026.json`):
- 59 já tinham comparecimento ≥ 90% no 1º turno (mediana de 94,6%).
- 52 já davam ≥ 95% a Lula.
- Somam +316 votantes e margem de 10.300.

**Variação do comparecimento entre os turnos:**
- Nas 1.749 seções com Lula ≥ 95%: +0,30 p.p.
- Nas 41 seções com Flávio ≥ 95%: +2,02 p.p.
- Em todas as seções: +1,71 p.p.

Isso é o oposto do que o enchimento de urnas pró-Lula produziria.

## Veredito proposto: `refutada`
- A "violação" de Benford é um artefato: aparece igual em 2022, no 1º turno e em eleições honestas simuladas.
- Contra o nulo correto, o 2BL e o último dígito são limpos.
- O 1º dígito tem um desajuste de modelo menor em 2026 do que nas linhas de base.
- A impressão digital não tem a cauda de enchimento.

## Casos mais suspeitos
Não se aplica a nível de seção. As 64 seções com comparecimento e Lula ≥ 95% estão concentradas em MA (13), BA (10) e PA (9); Tocantinópolis tem 5 e Barra do Corda tem 4. São persistentes desde o 1º turno.

## Limites
Os testes de dígitos são fracos contra manipulação proporcional e sutil. Um deslocamento uniforme não deixa marca nos dígitos.

## Fontes
- `ch10-klimek`: Klimek, Yegorov, Hanel e Thurner (2012), "Statistical detection of systematic election irregularities", PNAS 109(41):16469–16473. https://doi.org/10.1073/pnas.1210722109. Acesso: 2026-10-29.
- `ch10-mebane`: Mebane, W. (2006), "Election Forensics: Vote Counts and Benford's Law", Political Methodology Society. http://www-personal.umich.edu/~wmebane/pm06.pdf. Acesso: 2026-10-29.
- `ch10-deckert`: Deckert, Myagkov e Ordeshook (2011), "Benford's Law and the Detection of Election Fraud", Political Analysis 19(3):245–268. https://doi.org/10.1093/pan/mpr014. Acesso: 2026-10-29.
- `tse-boletins` (já registrada).

## Pendências
- Os dados de 2022 só incluem o 2º turno nos testes de dígitos. O 1º turno de 2022 ficou de fora para poupar tempo de execução.
