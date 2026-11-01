# Capítulo 11 — As pesquisas erraram só para um lado?

Script: `analises/11_pesquisas.py` → `site/public/data/ch11/{erros,resumo,transferencia}.json`.

## Pista
As pesquisas finais subestimaram Lula em cerca de 2,6 a 2,8 p.p. nos válidos, e nenhuma o apontou como vencedor. O Polymarket dava cerca de 77% a Flávio às 16h e virou por volta das 19h10.

## Teste (definido antes de olhar)
- **Métrica.** Fatia do PT entre os dois primeiros = PT/(PT+adversário), calculada a partir dos votos totais publicados. Erro = resultado − pesquisa (positivo = subestimou o PT).
- **Pesquisas.** A última de cada instituto, com campo nos 7 a 8 dias finais.
- **Linha de base.** 2º turnos de 2014, 2018 e 2022; 1º turnos de 2022 e 2026.

## Números-chave
- **2026, 2º turno.** As 18 pesquisas finais subestimaram Lula. Erro médio de **+2,63 p.p.** (mín. +1,17 Vox Brasil; máx. +3,91 Real Time). Era +2,59 antes da conferência de fontes de 30/10 (Veritá e Instituto França corrigidos).
  - Datafolha: +2,31. Quaest: +2,33. AtlasIntel: +2,55. CNT/MDA: +2,50. PoderData: +2,30. Nexus: +2,32. Palver: +2,29.
- **Erro médio na série** (negativo = superestimou o PT):

  | Eleição | Erro médio | Faixa |
  |---|---|---|
  | 2014, 2º turno | −0,86 | — |
  | 2018, 2º turno | −0,63 | — |
  | 2022, 1º turno | **−3,92** | −5,68 a −2,05 |
  | 2022, 2º turno | −0,96 | |
  | 2026, 1º turno | −1,50 | |
  | 2026, 2º turno | **+2,63** | +1,17 a +3,91 |

  - No 1º turno de 2022, os válidos de Bolsonaro foram subestimados em 5,2 p.p. em média.
  - No 1º turno de 2026, os válidos de Flávio foram subestimados em 2,9 p.p. em média, e os de Lula acertados (+0,15).
- **Fatia bipartidária oficial** (calculada dos BUs): 2026, 2º turno = 51,785%; 2026, 1º turno = 48,99%; 2022, 2º turno = 50,90%; 2022, 1º turno = 52,86%.
- **Erro em erros-padrão amostrais teóricos:** de 1,0 a 8,2 por pesquisa (o máximo é a Veritá, n = 15.554). A régua não inclui o erro não amostral, que costuma ser cerca de 2× o teórico (Shirani-Mehr et al., 2018).
- **Lula à frente, numericamente, nas finais de 2026:** Vox Brasil (20–22/10; 50,6% dos válidos, confirmado no O Liberal) e Colectta (23/10; só na Wikipédia, não localizada na imprensa). Portanto, “nenhuma apontou Lula” é falso no sentido estrito e verdadeiro para os grandes institutos.

## Correções aos números citados em alegações e em pesquisas
- **Datafolha final** (23–24/10, n=4.050): o registro é **BR-09540/2026**, como dizia as alegações (CNN Brasil, Tribuna de Jundiaí e Diário do Pará). A versão anterior desta nota dizia BR-03112, número que só aparece no Diário do Nordeste e foi descartado. Válidos: Flávio 51 × Lula 49. Totais: 48 × 47, BN 3, NS 2. O “49,11%” não é um número publicado.
- **Quaest final:** 23–24/10, n=3.702, BR-09158/2026. Válidos: 51 × 49. Totais: 46 × 45. BN 8, indecisos 1. A rodada de 17–20/10 citada no PDF não era a final.
- **AtlasIntel:** 18–23/10, n=4.990, BR-06380/2026. Válidos: 50,8 × 49,2. Totais: 49,9 × 48,4.
- **CNT/MDA:** a final é a de 21–23/10, n=2.032, BR-02136/2026, com 50,7 × 49,3 nos válidos e 46,3 × 45,0 nos totais. A de 13–15/10 (50,5 × 49,5, BR-00652) era a anterior.
- **Real Time Big Data:** 19–22/10, n=2.000, BR-09670. Válidos: 52 × 48. Totais: 49 × 45. Confere com o PDF.
- **PoderData, Nexus e Palver:** os números do PDF (19–21/10, 18–20/10) não eram as rodadas finais. As finais são as de 23–24/10 (PoderData 49 × 48, BR-02828/2026, válidos 51 × 49; Nexus 47 × 46, BR-08234/2026, válidos 50,5 × 49,5; ambos na CNN Brasil) e a Palver divulgada em 24/10 (50 × 49; campo 22–24/10 só na Wikipédia). Não verificamos os 52,4 × 47,6 de “eleitor provável” da Nexus.
- **Inconsistência do PDF sobre o Datafolha:** “47/46 nos totais → 50/50” refere-se à rodada de 20–22/10 (totais 47 × 46). Na conta exata, isso dá 50,5 × 49,5; o instituto arredondou e publicou 50 × 50.

## Transferência (só os números das pesquisas; matriz completa no cap. 3)
- **Datafolha, 6–7/10 (verificado):** entre os eleitores de Cury, Renan, Caiado e Zema, **46% Flávio, 32% Lula, 15% branco/nulo**. Aplicado aos 9.316.747 votos dos eliminados, isso daria cerca de 4,3 mi para Flávio e 3,0 mi para Lula.
- **Não localizados na fonte primária nem na imprensa (busca em 30/10):** Datafolha 20–22/10 com 47% × 26%; Quaest com 43% × 37% (eliminados), retenção 95%/94% e 36% × 40% (ausentes/brancos/nulos). A reportagem do Datafolha 20–22/10 (O Povo, BR-09709/2026) não traz cruzamento por voto no 1º turno.
- **O que a Quaest 17–20/10 (BR-08535/2026, divulgada em 21/10) publicou:** cruzamentos por candidato, sem agregado nem retenção. Cury: 48% Lula, 33% Flávio, 16% BN, 3% indecisos. Renan Santos: 51% Flávio, 25% Lula, 24% BN. Caiado: 57% Flávio, 21% Lula, 22% BN. Zema não aparece. Ponderados pelos válidos do 1º turno (Cury 2,89%, Renan 2,24%, Caiado 2,18%), dão ≈ 45,7% Flávio × 32,9% Lula, ou 58% para Flávio entre quem escolhe um finalista. As alegações dizia 43 × 37 (54%). **Diverge do usado no cap. 3** (ver relatório ao responsável; cap. 3 não foi editado).
- **Quaest 10–13/10 (BR-08729/2026, divulgada em 14/10):** Cury 34% Lula × 30% Flávio; Renan 40% Flávio × 14% Lula; Caiado 42% Flávio × 23% Lula.

## Veredito proposto: `parcial`
- *(Reavaliado após a conferência de 30/10: as correções aumentam o erro médio de 2026 de +2,59 para +2,63 e não mudam nenhuma conclusão.)*
- **A anomalia existe na direção.** É a primeira vez na série 2014–2026 que o erro médio das finais vai contra o PT; antes, sempre o favorecia, entre 0,6 e 3,9 p.p. As 18 de 18 pesquisas erraram para o mesmo lado. O erro mudou de sinal entre os turnos de 2026.
- **O tamanho não é inédito:** o 1º turno de 2022 teve erro maior, em sentido oposto.
- **Há explicações inocentes plausíveis:**
  - tendência de alta de Lula em todas as séries;
  - correção excessiva depois de 2022;
  - comparecimento diferencial (+2,96 mi entre os turnos).
- **O dado de pesquisa não distingue** essas explicações de um deslocamento uniforme da contagem.
- **Polymarket: `nao-testavel`.** A cotação reflete apostas que reagem a parciais e boatos; não é dado independente.

## Casos mais “suspeitos”
Os maiores erros pró-Lula: Real Time Big Data (+3,91), Datatrends (+3,87; não conferido), Alfa (+3,82), Gerp (+3,36), Veritá (+3,34), Instituto França (+3,19).

## Fontes (id, título, url, acesso)
- `ch11-datafolha-2410`: Diário do Nordeste, “Datafolha no 2º turno: Flávio Bolsonaro tem 51% e Lula 49% em votos válidos” (24/10/2026). https://diariodonordeste.verdesmares.com.br/pontopoder/datafolha-no-2-turno-flavio-bolsonaro-tem-51-e-lula-49-em-votos-validos-1.3800996. Acesso: 2026-10-29.
- `ch11-quaest-2410`: O Liberal, “Quaest: Flávio Bolsonaro tem 51% dos votos válidos e Lula 49% na véspera do segundo turno”. https://www.oliberal.com/politica/quaest-flavio-bolsonaro-tem-51-dos-votos-validos-e-lula-49-na-vespera-do-segundo-turno-1.1186432. Acesso: 2026-10-29.
- `ch11-atlas-2410`: SBT News, “AtlasIntel: Flávio tem 50,8% contra 49,2% de Lula”. https://sbtnews.sbt.com.br/noticia/politica/atlas-intel-flavio-tem-50-8-contra-49-2-de-lula. Acesso: 2026-10-29.
- `ch11-mda-2410`: Midiamax, “CNT/MDA: Flávio Bolsonaro tem 50,7% dos votos válidos; Lula 49,3%”. https://midiamax.com.br/brasil/2026/cnt-mda-flavio-bolsonaro-tem-507-votos-validos-lula-493/. Acesso: 2026-10-29.
- `ch11-realtime-2310`: Jornal Opção, “RealTime Big Data: Flávio tem 52% e Lula, 48% dos votos válidos”. https://www.jornalopcao.com.br/ultimas-noticias/realtime-big-data-flavio-tem-52-e-lula-48-dos-votos-validos-881600/. Acesso: 2026-10-29.
- `ch11-wiki-2026`: Wikipedia, “Opinion polling for the 2026 Brazilian presidential election”. https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Brazilian_presidential_election. Acesso: 2026-10-29.
- `ch11-wiki-2022`: Wikipedia, “Opinion polling for the 2022 Brazilian presidential election”. https://en.wikipedia.org/wiki/Opinion_polling_for_the_2022_Brazilian_presidential_election. Acesso: 2026-10-29.
- `ch11-hist-2014`: Jornal do Brasil, “Dilma na frente de Aécio, apontam últimas pesquisas do Ibope e Datafolha” (25/10/2014). https://www.jb.com.br/eleicoes-2014/noticias/2014/10/25/amp/dilma-na-frente-de-aecio-aponta-ultimas-pesquisas-do-ibope-e-datafolha.html. Acesso: 2026-10-29.
- `ch11-hist-2018`: Sul21, “Ibope traz Bolsonaro com 54% e Haddad com 46%; no Datafolha, Bolsonaro tem 55% e Haddad 45%” (27/10/2018). https://sul21.com.br/?p=32342. Acesso: 2026-10-29.
- `ch11-datafolha-transf`: DGABC, “46% dos eleitores de Cury, Renan Santos, Caiado e Zema migram para Flávio, aponta Datafolha”. https://www.dgabc.com.br/Noticia/4351747/46-dos-eleitores-de-cury-renan-santos-caiado-e-zema-migram-para-flavio-aonta-datafolha. Acesso: 2026-10-29.
- `ch11-polymarket`: Times Brasil (CNBC), “Flávio dispara no mercado de apostas e chega à reta final com 75% de probabilidade”. https://timesbrasil.com.br/eleicoes-2026/decisao-2026-flavio-dispara-no-mercado-de-apostas-e-chega-a-reta-final-da-eleicao-com-75-de-probabilidade-de-vitoria/. Acesso: 2026-10-29.
- `ch11-shirani-mehr`: Shirani-Mehr, Rothschild, Goel e Gelman (2018), “Disentangling Bias and Variance in Election Polls”, JASA 113(522). https://doi.org/10.1080/01621459.2018.1448823. Acesso: 2026-10-29.

## Pendências
- ~~Os resultados oficiais de 2014 e 2018 foram digitados de memória~~ — conferidos no TSE em 30/10 (ver abaixo).
- Critério de seleção: a Ideia (15–19/10, 46 × 48) termina 6 dias antes do 2º turno de 2026 e não está incluída; no 1º turno de 2026, Real Time (26–30/9), Indexa (27–29/9), Ideia (25–28/9) e Nexus (25–27/9) também ficaram de fora. Não alterado nesta revisão (é escolha de amostra, não número errado).
- Os números do 1º turno de 2018 não foram incluídos.
- Os institutos menores de 2026 e todos os de 2022 vêm da Wikipédia; a maioria foi conferida em 30/10 (abaixo). O Quaest do 1º turno de 2022 (24–27/9) é a última rodada Quaest listada na Wikipédia; não localizamos rodada posterior.
- A Band (27/10) tem uma matéria sobre os motivos do erro, mas retornou 403.

## Verificação de fontes (conferência de 30/10/2026)

Status: **confirmado** = valor do script bate com a fonte; **corrigido** = valor do script/achado estava errado e foi trocado; **não localizado** = não achamos fonte primária nem imprensa (mantido com o rótulo no texto). Para pesquisas cuja fonte só traz válidos, “confirmado” significa que os totais do script reproduzem os válidos publicados, a menos de arredondamento.

### Resultados oficiais
| Item | Valor | Fonte | Status |
|---|---|---|---|
| 2014, 2º turno: Dilma | 51,64% (54.501.118 votos) × Aécio 48,36% | TSE, “Plenário do TSE proclama resultado definitivo do segundo turno da eleição presidencial” (dez./2014) | confirmado |
| 2018, 2º turno: Haddad | 44,87% (Bolsonaro 55,13%, 57.797.847 votos) | TSE, “Eleições 2018: Justiça Eleitoral conclui totalização dos votos do segundo turno”; Poder360 (Haddad 47.040.859) | confirmado |
| 2022, 1º turno: Lula × Bolsonaro | 48,43% × 43,20% → fatia 52,86% | TSE, “100% das seções totalizadas: confira como ficou o quadro eleitoral após o 1º turno” | confirmado |
| 2022, 2º turno: Lula | 50,90% | TSE, “TSE proclama eleitos presidente e vice-presidente…” (dez./2022) | confirmado (calculado dos BUs; bate com o TSE) |
| 2026, 1º turno: Flávio × Lula | 47,03% × 45,16% → fatia 48,99% | O Povo 22/10 e DGABC 23/10, citando o TSE | confirmado |
| 2026, 2º turno: Lula | 51,785% (BUs) | imprensa cita 51,78%–51,79% | confirmado (TSE oficial não acessado diretamente) |

### Pesquisas finais históricas
| Item | Valor no script | Fonte | Status |
|---|---|---|---|
| Datafolha 24–25/10/2014 (BR-01210/2014, n=19.318) | Dilma 52% válidos (totais 47 × 43) | Jornal do Brasil, 25/10/2014 | confirmado |
| Ibope 24–25/10/2014 (BR-01195/2014, n=3.010) | Dilma 53% válidos (totais 49 × 43) | Jornal do Brasil, 25/10/2014 | confirmado |
| Datafolha 26–27/10/2018 (BR-02460/2018, n=18.371) | Haddad 45% válidos | Poder360, 27/10/2018 | confirmado |
| Ibope 26–27/10/2018 (BR-02934/2018, n=3.010) | Haddad 46% válidos | Poder360, 27/10/2018 | confirmado |
| Datafolha 30/9–1/10/2022 (BR-00245/2022) | 48 × 34 totais (válidos 50 × 36) | Bloomberg Línea, 1/10/2022 | confirmado |
| Ipec 29/9–1/10/2022 (BR-00999/2022) | 47 × 34 totais | Poder360 (só válidos 51 × 37) | confirmado (válidos); totais só na Wikipédia |
| Quaest 24–27/9/2022 | 46 × 33 | Jornal Opção (28/9/2022, título “46% contra 33%”) | confirmado |
| AtlasIntel 28–30/9/2022; CNT/MDA 28–30/9/2022; Ideia 23–28/9/2022 | 49,8 × 40,7; 44,2 × 36,3; 47 × 37 | só Wikipédia | não localizado |
| Datafolha 28–29/10/2022 | 49 × 45 (válidos 52 × 48) | Brasil de Fato e O Jacaré, 29/10/2022 | confirmado |
| Ipec 27–29/10/2022 (n=4.272) | 50 × 43 (válidos 54 × 46) | O Jacaré, 29/10/2022 | confirmado |
| Quaest 27–29/10/2022 | 45 × 42 | Brasil de Fato (só válidos 52 × 48) | confirmado (válidos); totais só na Wikipédia |
| AtlasIntel 26–29/10/2022 | 52,4 × 45,7 | O Jacaré (válidos 53,4 × 46,6) | confirmado |
| CNT/MDA 26–28/10/2022 | 46,9 × 44,9 | Jornal Opção (válidos 51,1 × 48,9) | confirmado |
| Paraná Pesquisas 26–28/10/2022 | 47,1 × 46,3 | O Jacaré (válidos 50,4 × 49,6) | confirmado |
| PoderData 23–25/10/2022 (n=5.000) | 49 × 44 | Money Times / Poder360 (válidos 53 × 47) | confirmado |
| Futura 24–26/10/2022 | 46,6 × 47,2 | campo confirmado (Terra Brasil); números só na Wikipédia | não localizado |

### 2026, 2º turno: pesquisas finais
| Item | Valor no script | Fonte | Status |
|---|---|---|---|
| Datafolha 23–24/10 — registro | BR-09540/2026 | CNN Brasil; Tribuna de Jundiaí; Diário do Pará | **corrigido** (achado dizia BR-03112) |
| Datafolha 23–24/10 — números | 47 × 48, bnI 5 (BN 3, NS 2); válidos 49 | Tribuna de Jundiaí; Diário do Nordeste | confirmado |
| Quaest 23–24/10 (BR-09158/2026, n=3.702) | 45 × 46, bnI 9 (BN 8, ind. 1) | O Liberal; CNN Brasil | confirmado |
| AtlasIntel 18–23/10 (BR-06380/2026, n=4.990) | 48,4 × 49,9, bnI 1,7 | SBT News; CNN Brasil | confirmado |
| CNT/MDA 21–23/10 (BR-02136/2026, n=2.032) | 45,0 × 46,3, bnI 8,7 (BN 5,8, ind. 2,9) | Midiamax; CNN Brasil | confirmado |
| Real Time Big Data 19–22/10 (BR-09670/2026) | 45 × 49, bnI 6 | DGABC, 23/10 (Jornal Opção retorna 403) | confirmado |
| PoderData/Aya 23–24/10 (BR-02828/2026) | 48 × 49 | CNN Brasil (válidos 49 × 51) | confirmado |
| Nexus/BTG 23–24/10 (BR-08234/2026) | 46 × 47 | CNN Brasil (válidos 49,5 × 50,5) | confirmado |
| Futura 23–24/10 (BR-09726/2026) | 47,9 × 48,2 | CNN Brasil (válidos 49,9 × 50,1) | confirmado |
| Gerp 22–24/10 (BR-09327/2026) | 46 × 49 | CNN Brasil (válidos 48 × 52) | confirmado |
| Palver (divulgada 24/10) | 49 × 50 | Tribuna de Jundiaí | confirmado (campo 22–24/10 só na Wikipédia) |
| Veritá 19–23/10 (BR-03181/2026, n=15.554) | **46,46 × 49,44, bnI 4,10** (válidos 48,44) | Congresso em Foco, 25/10 | **corrigido** (era 47,8 × 49,8 × 2,4) |
| Instituto França 21–23/10 (BR-04863/2026, n=1.537) | 43,1 × **45,6**, bnI 11,3 (válidos 48,6) | Times Brasil, 24/10 | **corrigido** (Flávio era 45,1) |
| Alfa Inteligência (BR-08496/2026, n=2.700) | campo **18–22/10**; 46 × 49,9 (válidos 48 × 52) | Times Brasil, 23/10 | **corrigido** (campo era 19–22/10); números confirmados |
| Ipespe/Abrapel 20–22/10 (n=1.500) | 47 × 48 | Poder360 (válidos 49,5 × 50,5) | confirmado (válidos); totais só na Wikipédia |
| Vox Brasil 20–22/10 (n=2.100) | 45,4 × 44,3 (válidos 50,6) | O Liberal, 23/10 | confirmado |
| Indexa/Broadcast 20–21/10 (n=2.000) | 44,1 × 45,2 (válidos 49,4) | O Liberal, 22/10 | confirmado |
| Colectta 23/10 | 46,5 × 46 | só Wikipédia | **não localizado** |
| Datatrends 19–21/10 | 46 × 50 | só Wikipédia (achada só a rodada 7–9/10) | **não localizado** |

### 2026, 1º turno
| Item | Valor no script | Fonte | Status |
|---|---|---|---|
| Datafolha 3/10 (BR-01708/2026, n=4.006) | 42 × 40, bnI 7 | O Liberal, 3/10 | confirmado |
| Quaest 2–3/10 (BR-02197/2026, n=3.702) | 40 × 38, bnI 13 | Money Times / Muita Informação (válidos 46 × 45) | confirmado |
| AtlasIntel 27/9–2/10 | 46,7 × 43,8 | imprensa traz válidos 47 × 44,1 | confirmado (válidos) |
| CNT/MDA 29/9–2/10 | 43,1 × 38, bnI 9,7 | DGABC (válidos 47,8 × 42,1) | confirmado |
| Futura, Palver, PoderData, Vox Brasil | — | só Wikipédia | não localizado |

### Tendências citadas no texto
| Item | Valor | Fonte | Status |
|---|---|---|---|
| Datafolha, Lula nos válidos: 48 → 49 → 50 → 49 | 8/10, 15/10, 22/10, 24/10 | O Povo 8/10 e 22/10; Bem Paraná | confirmado |
| AtlasIntel, Lula: “47,2 → 48,9 → 49,2” (válidos) | sem fonte para 47,2 | SBT News: 45,7 (8/10) → 47,6 (18/10) → 48,4 (final), nos totais | **corrigido** no texto para a série de totais |

### Cruzamentos de transferência
| Item | Valor | Fonte | Status |
|---|---|---|---|
| Datafolha 6–7/10, eliminados | 46 Flávio × 32 Lula × 15 BN | DGABC; O Liberal; Jornal do Comércio | confirmado |
| Datafolha 20–22/10, eliminados | 47 × 26 | reportagem da rodada (O Povo) não traz o cruzamento | **não localizado** |
| Quaest “22/10”, eliminados | 43 × 37 | Quaest 17–20/10 publicou só por candidato (≈ 46 × 33 ponderado) | **não localizado; publicado diverge** |
| Quaest, retenção Lula/Flávio | 95 / 94 | — | **não localizado** |
| Quaest, ausentes/brancos/nulos | 36 Flávio × 40 Lula | — | **não localizado** |

### Novas fontes ({id, titulo, url, acesso}) — para incluir em `fontes.json` pelo responsável
- `{id: "ch11-cnn-finais-2026", titulo: "CNN Brasil — Pesquisas mostram Flávio numericamente à frente de Lula, na margem de erro (registros de Datafolha, PoderData, Quaest, CNT/MDA, Gerp, Nexus, AtlasIntel, Futura)", url: "https://www.cnnbrasil.com.br/eleicoes/ultimas-pesquisas-segundo-turno-eleicao/", acesso: "2026-10-30"}`
- `{id: "ch11-datafolha-2410-tj", titulo: "Tribuna de Jundiaí — Datafolha 24/10/2026 (BR-09540/2026; 48 × 47; BN 3, NS 2)", url: "https://tribunadejundiai.com.br/politica/eleicoes-2026/pesquisa-datafolha-presidente-flavio-bolsonaro-lula-24-outubro-2026/", acesso: "2026-10-30"}`
- `{id: "ch11-datafolha-registro", titulo: "Diário do Pará — Pesquisa Datafolha: quando saem os próximos números (BR-09540/2026, campo 23–24/10, n=4.050)", url: "https://diariodopara.com.br/eleicoes-2026/pesquisa-datafolha-quando-saem-os-proximos-numeros-sobre-lula-e-flavio/", acesso: "2026-10-30"}`
- `{id: "ch11-realtime-2310-dgabc", titulo: "DGABC — Real Time Big Data: Flávio tem 52% dos votos válidos contra 48% de Lula (BR-09670/2026)", url: "https://www.dgabc.com.br/Noticia/4354342/real-time-big-data-flavio-tem-52-dos-votos-validos-contra-48-de-lula-em-empate-tecnico", acesso: "2026-10-30"}`
- `{id: "ch11-verita-2410", titulo: "Congresso em Foco — Flávio tem 51,56% dos votos válidos e Lula 48,44%, diz Veritá (BR-03181/2026)", url: "https://www.congressoemfoco.com.br/noticia/123609/flavio-tem-51-56-dos-votosvalidos-e-lula-48-44--diz-verita", acesso: "2026-10-30"}`
- `{id: "ch11-franca-2410", titulo: "Times Brasil — Instituto França: Flávio 51,4% × Lula 48,6% dos válidos (BR-04863/2026)", url: "https://timesbrasil.com.br/eleicoes-2026/decisao-2026-na-vespera-do-2o-turno-flavio-bolsonaro-tem-514-dos-votos-validos-contra-486-de-lula-diz-instituto-franca/", acesso: "2026-10-30"}`
- `{id: "ch11-alfa-2310", titulo: "Times Brasil — Alfa Inteligência: Flávio 52% × Lula 48% dos válidos (BR-08496/2026, campo 18–22/10)", url: "https://timesbrasil.com.br/brasil/decisao-2026-flavio-bolsonaro-tem-52-dos-votos-validos-contra-48-de-lula-no-2o-turno-aponta-pesquisa-alfa-inteligencia/", acesso: "2026-10-30"}`
- `{id: "ch11-ipespe-2310", titulo: "Poder360 — Flávio tem 50,5% contra 49,5% de Lula, diz Ipespe/Abrapel", url: "https://www.poder360.com.br/poder-eleicoes-2026/flavio-tem-505-contra-495-de-lula-diz-ipespe-abrapel/", acesso: "2026-10-30"}`
- `{id: "ch11-vox-2310", titulo: "O Liberal — Em votos válidos, Lula tem 50,6% contra 49,4% de Flávio, mostra Vox Brasil", url: "https://www.oliberal.com/politica/em-votos-validos-lula-tem-50-6-contra-49-4-de-flavio-mostra-pesquisa-vox-brasil-1.1185727", acesso: "2026-10-30"}`
- `{id: "ch11-indexa-2210", titulo: "O Liberal — Flávio tem 45,2% ante 44,1% de Lula, mostra Indexa/Broadcast", url: "https://www.oliberal.com/politica/flavio-tem-45-2-ante-44-1-de-lula-em-empate-tecnico-mostra-pesquisa-indexa-broadcast-1.1185405", acesso: "2026-10-30"}`
- `{id: "ch11-palver-2410", titulo: "Tribuna de Jundiaí — Pesquisa Palver: Flávio Bolsonaro tem 50% e Lula 49% no segundo turno", url: "https://tribunadejundiai.com.br/politica/eleicoes-2026/pesquisa-palver-flavio-bolsonaro-tem-50-e-lula-49-no-segundo-turno/", acesso: "2026-10-30"}`
- `{id: "ch11-quaest-cruz-2110", titulo: "Diario de Pernambuco — Quaest: 48% dos eleitores de Augusto Cury migram para Lula e 33% para Flávio (17–20/10, BR-08535/2026)", url: "https://www.diariodepernambuco.com.br/politica/2026/10/11727201-quaest-48-dos-eleitores-de-augusto-cury-migram-para-lula-e-33-para-flavio.html", acesso: "2026-10-30"}`
- `{id: "ch11-quaest-cruz-1410", titulo: "O Liberal — Quaest: 34% dos eleitores de Cury migram para Lula no 2º turno e 30% para Flávio (10–13/10, BR-08729/2026)", url: "https://www.oliberal.com/politica/quaest-34-dos-eleitores-de-cury-migram-para-lula-no-2-turno-e-30-para-flavio-1.1182658", acesso: "2026-10-30"}`
- `{id: "ch11-datafolha-2210-opovo", titulo: "O Povo — Datafolha tem empate numérico com 50% dos válidos (20–22/10, BR-09709/2026; sem cruzamento por voto no 1º turno)", url: "https://mais.opovo.com.br/jornal/politica/2026/10/22/datafolha-tem-empate-numerico-entre-flavio-bolsonaro-e-lula-com-50-dos-votos-validos.html", acesso: "2026-10-30"}`
- `{id: "ch11-atlas-serie", titulo: "SBT News — AtlasIntel: Flávio tem 50,8% contra 49,2% de Lula (série: Lula 45,7 em 8/10, 47,6 em 18/10)", url: "https://sbtnews.sbt.com.br/noticia/politica/atlas-intel-flavio-tem-50-8-contra-49-2-de-lula", acesso: "2026-10-30"}`
- `{id: "ch11-datafolha-0310", titulo: "O Liberal — Datafolha: Lula tem 45% dos votos válidos e Flávio Bolsonaro 42% no 1º turno (BR-01708/2026)", url: "https://www.oliberal.com/politica/datafolha-lula-tem-45-dos-votos-validos-e-flavio-bolsonaro-42-no-1-turno-1.1176498", acesso: "2026-10-30"}`
- `{id: "ch11-tse-2014", titulo: "TSE — Plenário do TSE proclama resultado definitivo do segundo turno da eleição presidencial (2014)", url: "https://www.tse.jus.br/comunicacao/noticias/2014/Dezembro/plenario-do-tse-proclama-resultado-definitivo-do-segundo-turno-da-eleicao-presidencial", acesso: "2026-10-30"}`
- `{id: "ch11-tse-2018", titulo: "TSE — Eleições 2018: Justiça Eleitoral conclui totalização dos votos do segundo turno", url: "https://www.tse.jus.br/comunicacao/noticias/2018/Outubro/eleicoes-2018-justica-eleitoral-conclui-totalizacao-dos-votos-do-segundo-turno", acesso: "2026-10-30"}`
- `{id: "ch11-tse-2022-1t", titulo: "TSE — 100% das seções totalizadas: confira como ficou o quadro eleitoral após o 1º turno (2022)", url: "https://www.tse.jus.br/comunicacao/noticias/2022/Outubro/100-das-secoes-totalizadas-confira-como-ficou-o-quadro-eleitoral-apos-o-1o-turno", acesso: "2026-10-30"}`
- `{id: "ch11-tse-2022-2t", titulo: "TSE — TSE proclama eleitos presidente e vice-presidente da República Luiz Inácio Lula da Silva e Geraldo Alckmin", url: "https://www.tse.jus.br/comunicacao/noticias/2022/Dezembro/tse-proclama-eleitos-presidente-e-vice-presidente-da-republica-luiz-inacio-lula-da-silva-e-geraldo-alckmin", acesso: "2026-10-30"}`
- `{id: "ch11-hist-2018-p360", titulo: "Poder360 — Ibope: Bolsonaro 54% x 46% Haddad; Datafolha: Bolsonaro 55% x 45% Haddad (27/10/2018)", url: "https://www.poder360.com.br/eleicoes/ibope-bolsonaro-54-x-46-haddad-datafolha-bolsonaro-55-x-45-haddad/", acesso: "2026-10-30"}` — substitui `ch11-hist-2018` (Sul21 retornou erro 520).
- `{id: "ch11-2022-1t-datafolha", titulo: "Bloomberg Línea — Datafolha: Lula mantém 50% dos votos válidos para o 1º turno, e Bolsonaro, 36% (BR-00245/2022)", url: "https://www.bloomberglinea.com.br/2022/10/01/datafolha-lula-mantem-50-dos-votos-validos-para-o-1-turno-e-bolsonaro-36/", acesso: "2026-10-30"}`
- `{id: "ch11-2022-1t-ipec", titulo: "Poder360 — Ipec: Lula tem 51% dos votos válidos, contra 37% de Bolsonaro (BR-00999/2022)", url: "https://www.poder360.com.br/pesquisas/ipec-lula-tem-51-dos-votos-validos-contra-37-de-bolsonaro/", acesso: "2026-10-30"}`
- `{id: "ch11-2022-2t-vespera", titulo: "Brasil de Fato — Datafolha, Ipec, Atlas, Quaest e MDA: as pesquisas deste sábado, véspera da eleição (29/10/2022)", url: "https://www.brasildefato.com.br/2022/10/29/datafolha-ipec-atlas-quaest-e-mda-as-pesquisas-deste-sabado-vespera-da-eleicao", acesso: "2026-10-30"}`
- `{id: "ch11-2022-2t-ojacare", titulo: "O Jacaré — Vantagem de Lula sobre Bolsonaro em pesquisas nacionais vai de 0,8 a 8 pontos (29/10/2022)", url: "https://www.ojacare.com.br/2022/10/29/vantagem-de-lula-sobre-bolsonaro-em-pesquisas-nacionais-vai-de-08-a-8-pontos", acesso: "2026-10-30"}`
