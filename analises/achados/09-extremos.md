# Capítulo 09: Seções extremas

Script: `analises/09_extremos.py` → `site/public/data/ch09/*.json`.
Tempo de execução: cerca de 10 minutos. Usa 400 simulações e o cálculo de caudas beta-binomiais para cerca de 1 milhão de seções.

## Pista
As alegações aponta 106 seções com 100% dos válidos para Lula e 4 para Flávio. Ele propõe testar com um nulo beta-binomial com proporção local e separar extremos persistentes de extremos novos.

## Teste
1. Contar seções com 100%, ≥95% e ≥90% dos válidos para cada candidato. Feito em quatro eleições:
   - 2026, 2º turno;
   - 2026, 1º turno, mesmas seções, usando a fatia entre Lula e Flávio;
   - 2022, 2º turno, seção a seção;
   - 2022, 1º turno.
2. Nulo hierárquico.
   - Proporção esperada: a do restante do local de votação, deixando a própria seção de fora (leave-one-out, com mínimo de 20 votos). Na falta disso, usa-se o restante do município.
   - Sobredispersão rho: estimada por momentos, separadamente por região e por tipo de vizinhança.
   - Simulação: Beta → Binomial com o nº real de válidos de cada seção, 400 repetições.
3. Persistência: comparar a fatia do candidato no 1º turno com a da mesma seção no 2º turno.
4. Peso dos extremos na margem nacional.
5. Diferença-em-diferenças contra o local de votação.
   - Previsão do 2º turno: logit(p₂) = logit(local₂) + [logit(seção₁) − logit(local₁)].
   - Cauda beta-binomial, BH-FDR sobre os 2N testes unilaterais.
   - Mesmo procedimento em 2022 (1º→2º turno) como linha de base.

## Números-chave

As contagens da tabela usam apenas seções com referência de vizinhança válida. Uma recontagem das seções pareadas com pelo menos um voto válido em 2022 encontrou **143** seções com zero para Jair Bolsonaro no 2º turno, das quais 141 entram no modelo. O detalhamento de zeros por candidato nos dois turnos e das chaves correspondentes entre anos está em `analises/16_votos_zerados.py` e `site/public/data/ch09/votos-zerados.json`.

| Contagem | Observado | Esperado pelo nulo (IC 90%) |
|---|---|---|
| 100% Lula, 2026 2º t. | **106** | 83,7 (72–95) → razão 1,27 |
| 100% Flávio, 2026 2º t. | **4** | 11,2 (6–17) → razão 0,36 |
| 100% Lula, 2022 2º t. | **141** | 103,2 (88–118) → razão **1,37** |
| 100% Bolsonaro, 2022 2º t. | 4 | 8,8 |
| 100% Lula, 2026 1º t. (fatia entre os 2) | 79 | 74,9 |
| 100% Flávio, 2026 1º t. | 8 | 22,7 |

- **Limiar ≥95%**, razão observado/esperado para Lula: 1,12 (2026 2º t.), 1,07 (2026 1º t.), 1,13 (2022 2º t.), 1,12 (2022 1º t.).
- **Limiar ≥90%**, mesma razão: 1,07, 1,07, 1,10 e 1,10.
- **O nulo erra sempre do mesmo jeito nas quatro eleições.** Subestima a cauda de Lula e superestima a de Flávio/Bolsonaro (razões de 0,17 a 0,58). A conclusão, por isso, apoia-se na comparação entre eleições, não no valor-p absoluto.
- **Persistência.**
  - As 106 seções 100% Lula tinham ≥90% de Lula no 1º turno (fatia entre os 2); 102 tinham ≥95% e 50 já tinham 100%.
  - As 4 seções 100% Flávio já eram 100% Flávio no 1º turno.
  - Das 1.749 seções com ≥95% para Lula no 2º turno, 1.729 são persistentes (≥90% no 1º turno) e só 20 são novas.
- **Perfil das 106.**
  - Região: Norte 65, Nordeste 29, Centro-Oeste 6, Sudeste 3, Sul 3.
  - Tamanho: mediana de 124,5 válidos, máximo 354 (Tabatinga, AM).
  - Municípios mais frequentes: Uiramutã (7), Atalaia do Norte (5), São Gabriel da Cachoeira (5), Turiaçu (4), Santa Isabel do Rio Negro, Goiatins e Oriximiná (3 cada). São áreas de terras indígenas e quilombolas.
  - As 4 de Flávio: Arroio do Padre (RS), Cândido Godói (RS), Jacareacanga (PA) e Chaves (PA).
- **Peso na margem.**
  - As 106 seções 100% Lula somam 14.860 votos de margem, 0,34% da margem nacional de 4.430.191. O ganho em relação ao 1º turno foi de 589 votos.
  - As 6.899 seções com ≥90% para Lula somam 26% da margem, mas ganharam só 81.467 votos de margem entre os turnos.
- **Diferença-em-diferenças por local** (499.127 seções testáveis):
  - FDR 5% em 2026: 11 seções a favor de Lula (+845 na margem) e 7 a favor de Flávio (−584). Efeito líquido: +261 votos.
  - FDR 5% em 2022: 13 a favor de Lula e 9 a favor de Bolsonaro.
  - A rho estimada para o resíduo DiD ficou no piso (1e-4). Ou seja, a previsão por local mais 1º turno é quase binomial: as seções mantêm muito bem sua posição relativa entre os turnos.

## Veredito proposto: `refutada`
- Os números de 106 e 4 estão corretos.
- A assimetria é estrutural: aparece nos quatro turnos analisados e é maior em 2022.
- Os extremos são persistentes desde o 1º turno.
- O peso desses extremos na margem é desprezível.
- As seções que destoam de seu local de votação são simétricas e tão numerosas quanto em 2022.
- Nada aponta para urnas "preenchidas".

## Casos mais estranhos (para conferência física de BU e log)
- **Santa Rosa do Purus (AC), z3 s95.** Lula foi de 49% para 79%, enquanto o local foi de 53% para 55% (q≈0). Em 2022, a mesma seção foi a mais pró-Bolsonaro (58%→20%). É volátil nos dois sentidos.
- **Manoel Urbano (AC), z3 s160.** Lula caiu de 112 para 48 votos e Flávio subiu de 55 para 104. Isso arrasta a vizinha, s100, para a lista oposta. Em 2022, a s100 foi de 2% para 78% de Lula.
- **Barcelos (AM), s37 e s39.** As duas seções do mesmo local inverteram de posição (18%→54% e 30%→19%).
- **Monte Belo do Sul (RS), s51.** Artefato do modelo: local com quase 0% de Lula, onde o logit exagera a previsão.
- **Anapu (PA), s254.** 97% de Lula num local com 28%, mas já tinha 81% no 1º turno.
- **Ipixuna (AM), s63.** Flávio caiu de 61 para 2 votos (Lula: 135→167).
- **Santa Rita de Cássia (BA), s57.**
- A lista completa está em `site/public/data/ch09/did-top.json`.

## Fontes
- `tse-boletins` (já registrada).
- Para 2022: boletins de urna 2022, se o integrador tiver id próprio (o cap. 1 usa `tse-boletins-2022`).

## Pendências e sugestões
- Não temos o nome dos locais de votação. Um cadastro de locais do TSE ("eleitorado_local_votacao") permitiria rotular as seções como aldeia, quilombo etc.
- Conferir BU e log das seções da lista DiD, em especial Manoel Urbano s100/s160 e Santa Rosa do Purus s95.
