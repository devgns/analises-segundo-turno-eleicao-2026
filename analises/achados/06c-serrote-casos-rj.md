# 06c: o "serrote" nos nove casos do RJ

Script: `analises/06c_serrote_casos_rj.py`. Dados do site: `site/public/data/ch06c/`. Capítulo: `site/src/capitulos/06c-serrote-nos-casos-rj.html`.

## Pista

Nos nove municípios do capítulo 4 (Campos dos Goytacazes, Região dos Lagos e Silva Jardim), Lula disparou e Flávio ficou estagnado. A hipótese testada é que esse resultado veio de um mecanismo intermitente, como o "algoritmo que liga e desliga" do vídeo do capítulo 6b, que teria penalizado Flávio ao longo da apuração.

## Dados

- 2.950 seções dos casos e 34.725 do resto do RJ, todas pareadas nos dois turnos.
- A ordem de chegada vem de `DT_BU_RECEBIDO` do 2º turno. Os boletins dos casos chegaram entre 19:03:38 e 21:10:26.
- Não há histórico de totalização de 2026, nem histórico por município.

## Testes e números

**Medida.** Por seção, y = Δ da fatia de Flávio entre os finalistas (1T→2T). Dela se desconta a média ponderada do local de votação, o que dá o resíduo r.

**Nulo.** Os horários de chegada ficam fixos e r é embaralhado dentro do local, com 1.000 permutações.

| Grupo | Fase (z por janela de 8 s, unilateral) | Periodicidade (30 s a 20 min) | Tendência |
|---|---|---|---|
| Nove casos (2.950 seções) | p = 0,48 (−0,16 p.p., s 44–51) | p = 0,69 | p = 0,47 (−1,12 p.p./h) |
| Campos (1.190 seções) | p = 0,80 | p = 0,56 | p = 0,87 (+0,50 p.p./h) |
| Resto do RJ | p = 0,031 (−0,16 p.p., s 7–14) | p = 0,39 | p = 0,33 |

O p = 0,031 do resto do RJ vira 0,28 com Holm sobre 9 testes.

**Poder do teste de fase** (retirada de φ% dos votos de Flávio numa janela de 8 s; 100 simulações):

| Grupo | φ = 1% | φ = 2% | φ = 5% | φ = 20% |
|---|---|---|---|---|
| Nove casos | 78% | 95% | 94% | 100% |
| Campos | 17% | 79% | 85% | 96% |

O poder não chega a 100% porque janelas injetadas em segundos quase vazios afetam poucas seções.

**Placebo do 1º turno** (correlação por blocos de 25 seções; 10 em municípios pequenos):

| Município | r |
|---|---|
| Araruama | 0,85 |
| Búzios | 0,90 |
| Saquarema | 0,90 |
| Arraial do Cabo | 0,93 |
| Cabo Frio | 0,93 |
| São Pedro da Aldeia | 0,95 |
| Campos | 0,96 |
| Iguaba Grande | 0,96 |
| Silva Jardim | 0,98 |

**Estagnação de Flávio:**
- **Campos:** caiu em 594 seções e subiu em 533. Na ordem de chegada, foram −1.960 votos na 1ª metade e +571 na 2ª. A tendência dentro da escola é nula (p = 0,87).
- **Silva Jardim:** +24 / −23.
- **Araruama:** +501 / −490.

## Achado de método

Uma versão do teste de fase com nulo de rotação por escola deu p = 0,001 nos casos (−0,67 p.p.) e no resto do RJ. Era um falso positivo: a janela extrema caía nos segundos 59–06, em que chegam cerca de 20 seções dos casos, e o nulo girado não reproduz janelas quase vazias. A correção (horários fixos e escore z) foi aplicada também ao capítulo 6b.

## Veredito proposto: refutada

Refutada para a hipótese de mecanismo intermitente no tempo da apuração. A anomalia de nível do capítulo 4 permanece; este teste não a explica nem a desfaz.

## Limites

- Uma alteração constante, igual em todas as seções, não deixa rastro no tempo (ver capítulos 2, 4 e 5).
- O tempo da votação dentro da urna não é testável: o RDV é embaralhado por lei e o log não registra o voto.
- O horário de recebimento é uma aproximação da ordem de totalização.
- Campos tem poder de 79% para uma retirada de 2% concentrada numa janela de 8 s.

## Fontes

Nenhuma nova; usa `tse-boletins`.
