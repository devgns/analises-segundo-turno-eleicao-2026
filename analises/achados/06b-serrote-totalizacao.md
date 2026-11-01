# 06b: o "serrote" da totalização (vídeo do prof. Marcelo Trindade)

Script: `analises/06b_serrote_totalizacao.py`. Dados do site: `site/public/data/ch06b/`. Capítulo: `site/src/capitulos/06b-serrote-da-totalizacao.html`.

## Pista

Um vídeo atribuído ao prof. Marcelo Trindade (X, @contraAssalto; também no YouTube) mostra a curva do percentual acumulado de Bolsonaro ao longo da totalização do **2º turno de 2022**. A pasta do notebook se chama "Eleições 2022" e o autor diz "esses são os dados de 2022". O vídeo faz duas alegações:

1. Há vales "igualmente espaçados" entre 70 mil e 85 mil seções, que seriam um "algoritmo que liga e desliga" penalizando Bolsonaro.
2. Houve uma única "virada", quando o esperado, segundo ele, seriam várias. Ele diz ter embaralhado a ordem 3 mil vezes e obtido "várias inversões".

O vídeo foi baixado do X (o YouTube bloqueou o acesso automatizado), transcrito com Whisper e analisado quadro a quadro.

## Fonte do gráfico

O gráfico vem do TSE: Histórico de totalização Presidente BR 2T 2022, pacote CKAN `resultados-2022`. O arquivo tem 5.286 registros, um por segundo de totalização. Para 2026, o histórico ainda não foi publicado (404 no CDN em 31/10/2026).

## Testes e números-chave

**1. Reprodução.** Os 5 valores legíveis no vídeo batem com o TSE até a 6ª casa decimal:

| Seções | Hora | Bolsonaro |
|---|---|---|
| 23.954 | — | 0,529867 |
| 70.197 | — | 0,516887 |
| 71.324 | — | 0,516603 |
| 72.747 | 17:42:37 | 0,516508 |
| 74.682 | — | 0,515568 |

O total final do histórico é igual à soma do bweb: Lula 60.345.999 × Bolsonaro 58.206.354.

**2. Regularidade.** Os vales do zoom começam às 17:41:41, 17:42:46, 17:43:52, 17:45:00 e 17:46:02, com intervalos de 65, 66, 68 e 62 s. Picos do espectro, em 17h–19h (potência relativa à mediana):

| Turno de 2022 | 33 s | 22 s | 66 s |
|---|---|---|---|
| 2º turno | 62× | 53× | 25× |
| 1º turno | 105× | — | 31× |

O ciclo do sistema de totalização é o mesmo nos dois turnos.

**3. Impressão digital dos lotes** (lotes com 20 seções ou mais, 17h–19h). Comparecimento, brancos e nulos e aptos por seção não mudam se votos forem trocados de candidato:

| Grupo | Seções | Bolsonaro | Comparecimento | Brancos + nulos | Aptos por seção |
|---|---|---|---|---|---|
| Lotes abaixo de 35% B | 49.799 | 30,0% | 80,1% | 5,1% | 320,7 |
| Nordeste (bweb) | — | 30,7% | 80,7% | 4,9% | 319,6 |
| Sudeste | — | — | — | — | 343 |
| Sul | — | — | — | 3,7% | — |

Os vales são lotes de seções do Nordeste. Para produzi-los trocando votos, seria preciso tirar cerca de 45% dos votos de Bolsonaro nas seções dos vales.

**4. Placebo.** Mesmas seções, ordem de chegada do 2º turno (`DT_BU_RECEBIDO`), votos do 1º turno. Correlação por blocos de 150 seções:

| Ano | Período inteiro | Janela 65k–90k |
|---|---|---|
| 2022 | 0,998 (r² = 0,996) | 0,994 |
| 2026 | 0,996 | 0,995 |

**5. Teste de fase.** Resíduo da variação 1T→2T, descontada a média do local de votação, por segundo de chegada, em janelas circulares de 8 s. A estatística é o escore z de cada janela (soma ponderada ÷ erro-padrão). O nulo mantém os horários de chegada e embaralha o resíduo entre seções da mesma escola, com 400 permutações.

| Ano | Janela mais desfavorável ao candidato | p unilateral (direção alegada) | Janela mais extrema | p bilateral |
|---|---|---|---|---|
| 2022 | −0,010 p.p. (s 27–34) | 0,15 | +0,012 p.p. | 0,82 |
| 2026 | −0,006 p.p. (s 31–38) | 1,0 | +0,053 p.p. a favor de Flávio (s 54–01) | 0,81 |

- **Poder:** tirar 0,5% dos votos de B numa janela de 8 s por minuto é detectado em 40 de 40 simulações, nos dois anos.
- **Histórico do método** (registrado também no capítulo):
  1. A primeira versão permutava dentro do município e deu p = 0,02 (2022) e 0,0025 (2026). Esse nulo quebra a correlação entre seções da mesma escola.
  2. A segunda versão girava a fase de cada escola e deu p = 0,0025 em 2026. Esse nulo espalha as seções pelo minuto, enquanto na realidade alguns segundos quase não recebem boletins. As janelas quase vazias têm média instável, e o nulo girado era estreito demais. O resultado eram falsos positivos, que apareceram também nos casos do RJ (capítulo 6c).
  3. A versão final mantém os horários e usa o escore z.

**6. Viradas.** Ordem reconstruída de 2022, comparada com 3.000 ordens aleatórias:

| Medida | Ordens aleatórias | Ordem real |
|---|---|---|
| Ordens sem virada depois do primeiro 1% | 99,97% | — |
| Última virada (p99) | até a seção 2.498 | — |
| Desvio máximo em relação ao resultado final (p99) | 0,73 p.p. | 7,5 p.p. |

- **Composição regional:** o Nordeste é 6% das primeiras 9.440 seções e chega a 28% no fim; o Sul cai de 25% para 15%.
- **2º turno de 2022 (histórico):** o pico de Bolsonaro foi 56,84%, e a virada aconteceu às 18:42:53, com 66,8% das seções.
- **1º turno de 2022 (histórico):** Lula passou Bolsonaro uma única vez, às 19:59:54, com 68,0% das seções.
- **2026 (reconstruído):** Flávio teve no máximo 50,5% depois do primeiro 1%, e a liderança trocou de mãos 16 vezes até cerca de 235 mil seções.

## Veredito proposto: refutada

O gráfico é real e os vales são periódicos. Mas a periodicidade é do sistema de totalização, e os vales são lotes de outra região, e não votos trocados. Quatro evidências independentes sustentam isso:

- a impressão digital dos lotes;
- o placebo do 1º turno;
- a ausência de efeito de fase, com poder alto;
- o mesmo ciclo no 1º turno.

A "virada única" é o esperado com uma ordem regional. Nenhum teste usa 2022 como referência "limpa" para absolver 2026.

## Limites e pendências

- Uma alteração uniforme gravada nos próprios BUs, sem ligação com o ciclo, não é testada aqui (ver capítulos 2 e 5).
- A ordem de totalização não é a de recebimento: a totalização anda cerca de 2 mil seções atrás. A ligação exata entre registros do histórico e seções falhou: só 763 de 5.286 registros casaram por janela contígua dentro da UF.
- A causa técnica do lote nordestino a cada ~66 s não foi documentada pelo TSE.
- Falta o histórico de totalização de 2026.

## Fontes

| id | Título | URL | Acesso |
|---|---|---|---|
| `tse-historico-totalizacao` | TSE, Histórico de totalização Presidente BR 1T/2T 2022 | https://dadosabertos.tse.jus.br/dataset/resultados-2022 | 2026-10-31 |
| `video-trindade-x` | Vídeo no X | https://x.com/contraAssalto/status/2114744372503707994 | 2026-10-31 |
| `video-trindade-yt` | Vídeo no YouTube | https://youtu.be/rkhRoUjrsM4 | 2026-10-31 |
