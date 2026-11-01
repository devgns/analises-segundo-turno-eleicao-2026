# Capítulo 03: Para onde foram os eleitores de Cury, Renan, Caiado e Zema

- **Script:** `analises/03_transferencia.py`. Roda com `uv run python analises/03_transferencia.py` em cerca de 2 min, com bootstrap de 200 reamostragens. A variável de ambiente `N_BOOT` muda o número de reamostragens.
- **Saída numérica completa:** `analises/achados/03-transferencia-numeros.txt`.
- **Dados do site:** `site/public/data/cap03-*.json`:
  - matriz, matriz-2022, modelos, regioes, ufs, candidatos, goias, faixas, poder, viabilidade, sim e kpis.
- **Capítulo:** `site/src/capitulos/03-transferencia-de-votos.html` e `.js`.
- **Worker próprio do simulador:** `site/src/workers/transferencia.worker.js`, tarefa `transferencia03`, passado via `criarWorker`.

## Pista

Esta pista vem de alegações que circulam. Entre os turnos:

- Lula ganhou 10.376.696 votos;
- Flávio ganhou 3.721.538 votos;
- os eliminados somavam 9.316.747 votos.

O ganho de Lula sozinho supera todo o estoque dos eliminados. A suspeita se apoia em três pontos:

- eleitor de direita raramente migra para Lula;
- três dos quatro eliminados apoiaram Flávio (Zema em 05/10, Caiado em 06/10 e Cury em 08/10; Renan não apoiou ninguém);
- as pesquisas mostravam os eleitores dos eliminados pendendo para Flávio:
  - **Datafolha de 06–07/10** (divulgado em 08/10; verificado): 46% Flávio, 32% Lula, 15% branco/nulo.
  - **Quaest de 17–20/10** (BR-08535/2026, divulgada em 21/10; verificada, só por candidato):
    - Cury: 48% Lula, 33% Flávio;
    - Renan: 51% Flávio, 25% Lula;
    - Caiado: 57% Flávio, 21% Lula.

    Ponderada pelos votos, dá 45,7% Flávio × 32,9% Lula, ou 58,1% Flávio entre quem escolhe um finalista.
  - **Números de alegações descartados**: Datafolha 20–22/10 com 47 × 26; Quaest com 43 × 37, retenção de 95/94 e ausentes 36 × 40. Não foram localizados em nenhuma fonte (conferência do cap. 11, 30/10).

**Pergunta:** o resultado oficial exige taxas de transferência incompatíveis com as pesquisas e com essas premissas?

## Teste (definido antes de olhar)

1. **Matriz de transição por inferência ecológica.**
   - **Método:** regressão de Goodman restrita, com mínimos quadrados ponderados pelo eleitorado do 1º turno, taxas em [0, 1] e cada linha somando 1.
   - **Origens:** Lula, Flávio, Cury, Renan, Caiado, Zema, demais, branco/nulo e abstenção.
   - **Destinos:** Lula, Flávio, branco/nulo e abstenção. Os destinos são reescalados para somar o eleitorado do 1º turno.
   - **Ajuste:** feito por UF sobre 497.752 seções pareadas e agregado ao Brasil ponderando pelos votos de origem.
   - **Seções excluídas:** exterior, seções com menos de 20 aptos e seções em que o cadastro variou mais de 5% entre os turnos.
   - **Solver:** SLSQP para as estimativas pontuais. Para os lotes de bootstrap e o modelo local, FISTA com projeção no simplex. O problema é convexo, e a diferença entre os dois solvers ficou abaixo de 0,5 p.p. (testado).
2. **Incerteza.** Bootstrap de municípios estratificado por UF, com 200 reamostragens e IC 95% por percentil.
3. **Robustez.** O modelo foi ajustado também de forma nacional única, por região, localmente (um ajuste por município com 60 seções ou mais, cobrindo 81% do eleitorado, e o resto por UF) e no nível municipal.
4. **Linha de base de 2022.** Mesmo método no nível municipal, com Ciro, Tebet e os demais como eliminados.
5. **Descritivo sem modelo.** Variação de votos por faixa de força de Lula no 1º turno, por município, em 2026 e em 2022.
6. **Experimentos naturais.** Caiado em Goiás (12,3% dos válidos), Zema em Minas, Cury e Renan em São Paulo (a maior fatia de ambos entre as UFs com pelo menos 3 milhões de eleitores).
7. **Viabilidade e pesquisas** (só números verificados).
   - **Modelo contábil:** condicionado ao total oficial de válidos. Lula previsto em função de:
     - retenção e troca dos finalistas;
     - participação e divisão de cada eliminado;
     - divisão dos "novos" votantes.
   - **Retenção dos finalistas:** nenhuma pesquisa verificada a publicou, então usamos a estimada pelos dados.
   - **Novos votantes:** divididos como o cabeçalho (válidos) da própria pesquisa. Variante: 50/50.
   - **Zema:** a Quaest não publicou; usamos o número de Caiado.
   - **Grade:** fração dos eliminados para Flávio × retenção de Flávio. Fixos: retenção de Lula estimada; 78,6% dos eliminados votam em um finalista (Quaest); novos votantes 49,4% Lula.
   - **Saídas:** o erro implícito e a fração dos novos votantes que Lula precisaria receber.
8. **Teste de poder.** Três alterações uniformes sintéticas foram injetadas nas seções reais, cada uma de cerca de 2,2 p.p., e a matriz foi reestimada.

## Números-chave

### Matriz principal de 2026 (ajuste por UF, IC 95%)

| Origem | → Lula | → Flávio | → Branco/nulo | → Abstenção |
|---|---|---|---|---|
| Lula | 98,9% (98,6–99,1) | 0,0% | 0,2% | 1,0% |
| Flávio | 0,2% (0,1–0,3) | 98,8% (98,6–99,1) | 0,3% | 0,7% |
| Cury (3,45 mi) | 52,9% (51,3–54,4) | 28,2% (26,3–29,5) | 14,9% | 4,1% |
| Renan (2,68 mi) | 39,3% (37,4–40,6) | 34,9% (33,4–36,2) | 16,9% | 8,8% |
| Caiado (2,61 mi) | 33,3% (28,2–37,4) | 51,2% (48,5–53,5) | 11,6% | 3,9% |
| Zema (0,33 mi) | 5,1% (2,0–9,2) | 81,4% (77,3–84,4) | 10,3% | 3,2% |
| Demais | 84,3% | 7,7% | 6,8% | 1,2% |
| Branco/nulo do 1º turno | 62,0% (59,6–63,7) | 1,4% | 36,1% | 0,5% |
| Abstenção do 1º turno | 9,7% (9,3–10,2) | 2,4% | 1,1% | 86,8% |

- **Eliminados:** entre os que escolheram um finalista, 47,0% (45,4–48,2) foram para Flávio.
- **Novos votantes válidos** (brancos, nulos ou ausentes no 1º turno): 7,76 milhões, 88,7% (87,7–89,4) para Lula.
- **Previsto × real:** Lula 64,05 mi × 64,04 mi; Flávio 59,69 mi × 59,64 mi.

### Retenção de Flávio e divisão dos eliminados em todas as especificações de 2026

| Especificação | Retenção de Flávio | Flávio → Lula | Eliminados → Flávio (entre válidos) | Novos → Lula |
|---|---|---|---|---|
| Nacional | 99,2% | 0,0% | 52,0% | 97% |
| Por região | 98,9% | 0,0% | 47,9% | 91% |
| Por UF | 98,8% | 0,2% | 47,0% | 89% |
| Local | 97,8% | 0,5% | 50,6% | 84% |
| Municipal nacional | 100% | 0,0% | 50,5% | 100% |
| Municipal por região | 99,7% | 0,0% | 44,8% | 95% |

### 2022, municipal por região

- **Retenção:** Bolsonaro 100%, Lula 98,9%.
- **Eliminados para Bolsonaro:** 53,2% (48,7–60,6) entre válidos; 65,3% no ajuste nacional.
- **Linhas de branco/nulo e de abstenção:** instáveis. Branco/nulo vai 35% para Bolsonaro no ajuste por região e 25% para Lula no nacional.
- **Leitura:** as linhas de branco/nulo e abstenção não são confiáveis no método. Os 89% de 2026 devem ser lidos como "maioria", não como valor preciso.

### Por região (2026)

| Região | Eliminados → Flávio (entre válidos) | Retenção de Flávio |
|---|---|---|
| Sul | 62,1% | 100% |
| Centro-Oeste | 55,2% | 99,5% |
| Sudeste | 46,8% | 99,0% |
| Nordeste | 36,1% | 98,1% |
| Norte | 35,0% | 96,3% (Flávio → Lula 1,3%) |

### Experimentos naturais

- **Goiás:**
  - pelo modelo, Caiado foi 50,8% (46,7–53,0) para Flávio e 35,0% (31,9–39,4) para Lula;
  - na regressão municipal, cada voto de Caiado se associa a +0,52 voto para Flávio e +0,30 voto para Lula;
  - o resultado coincide com a estimativa nacional.
- **Minas Gerais:** Zema foi 75,7% (65,6–85,5) para Flávio.
- **São Paulo:** Cury foi 53,5% para Lula e 25,7% para Flávio; Renan, 38,2% para Lula e 30,6% para Flávio.

### Descritivo sem modelo (municípios): o achado mais forte a favor de "algo mudou"

**Fatia da direita no crescimento líquido dos dois finalistas entre os turnos:**

| Faixa de Lula no 1º turno | 2022 | 2026 |
|---|---|---|
| Menos de 20% | 88% | 51% |
| 40 a 50% | 72% | 27% |
| 80% ou mais | 52% | 4% |

A queda é de 37 a 53 p.p. em **todas** as faixas.

**Brancos e nulos nos redutos de Lula:**

- em 2026, caíram de 1,4 a 1,7 p.p. do eleitorado;
- em 2022, subiram de 0,2 a 0,3 p.p.

**Comparecimento:**

- em 2026, subiu de 1,3 a 2,2 p.p. em todas as faixas;
- em 2022, ficou entre −0,3 e +1,7 p.p.

### Pesquisas verificadas × oficial

Lula oficial: 51,785% dos válidos. Retenção dos finalistas igual à estimada pelos dados.

| Cenário | Eliminados → Flávio (entre válidos) | Lula previsto | Oficial − previsto | Novos 50/50 | Fração dos novos que Lula precisaria (cabeçalho) | Com retenção de 100% |
|---|---|---|---|---|---|---|
| Quaest 17–20/10, por candidato | 58,7% | **48,61%** | **+3,17 p.p.** | 48,65% | 99,0% de 7,9 mi (49,4%) | 108,4% |
| Datafolha 06–07/10, agregado | 59,0% | **48,51%** | **+3,28 p.p.** | 48,64% | 98,9% de 8,0 mi (48,0%) | 108,3% |
| Inferência ecológica | 47,0% | 51,76% | +0,02 p.p. | 49,34% | 89% | 97% |

**Por candidato:** fração para Flávio entre quem escolheu um finalista, dados (IC 95%) × Quaest.

| Candidato | Dados | Quaest |
|---|---|---|
| Cury | 34,8% (32,6–36,4) | 40,7% |
| Renan | 47,0% (45,2–48,8) | 67,1% |
| Caiado | 60,6% (56,7–65,4) | 73,1% |
| Zema | 94,1% (89,6–97,7) | não publicado |
| Todos | 47,0% (45,4–48,2) | 58,1% (Datafolha: 59,0%) |

O ordenamento dos candidatos é o mesmo; a pesquisa é 6 a 20 p.p. mais favorável a Flávio em todos eles.

- **Curva de reprodução:** exige retenção de Flávio de 94,7% (com 30% dos eliminados para Flávio) a 89,5% (com 60%), com metade de quem o deixa indo para Lula.
- **Comparação com o erro de cabeçalho** (detalhes no cap. 11):
  - Quaest 17–20/10: 49,4% para Lula, erro de 2,4 p.p.;
  - Datafolha 06–07/10: 48%, erro de 3,8 p.p.;
  - erro médio das pesquisas finais de 2026: +2,63 p.p.;
  - 1º turno de 2022: −3,92 p.p. em média, com Bolsonaro subestimado em 5,2 p.p.;
  - 2º turno de 2022: Datafolha e Quaest davam 52% e Ipec 54% para Lula, que teve 50,9%.
- **Leitura:** um erro implícito de 3,2–3,3 p.p. fica no limite alto, mas dentro do histórico.

### Teste de poder (reestimação por UF)

| Cenário | Votos movidos | Retenção de Flávio | Flávio → Lula | Eliminados → Flávio | Abstenção → Lula | Leitura |
|---|---|---|---|---|---|---|
| Dados reais | — | 98,8% | 0,2% | 47,0% | 9,7% | — |
| Virada uniforme de 4,8% dos votos de Flávio | 2,86 mi; Lula vai a 54,09% | 95,3% | 2,5% | 38,6% | 11,6% | Deixa impressão digital, que não aparece nos dados reais. Parte é absorvida pelos eliminados. |
| Enchimento: 20% dos ausentes viram votos de Lula | 5,99 mi; Lula vai a 54,01% | 98,9% | 0,3% | 46,5% | 27,1% | Absorvido como "mobilização". Indistinguível. |
| Enchimento proporcional a Lula (+9%) | 5,76 mi; Lula vai a 53,92% | 99,0% | 0,2% | 39,0% | 19,7% | Indistinguível. Também empurra a divisão dos eliminados para Lula. |

## Veredito proposto: `parcial`

**A anomalia existe:**

- com a divisão dos eliminados das pesquisas verificadas, Flávio venceria: Lula ficaria com 48,61% (Quaest) ou 48,51% (Datafolha), uma distância de 3,2 a 3,3 p.p.;
- o oficial exige eliminados divididos quase ao meio (47% para Flávio, contra 58% a 59% nas pesquisas; Renan 47% contra 67%) e novos votantes majoritariamente lulistas (estimados em 89%). Nenhuma pesquisa verificada mediu esse grupo; se ele seguisse o cabeçalho das pesquisas, Lula precisaria de 99% dele;
- em relação a 2022, a fatia da direita no crescimento entre turnos caiu de 37 a 53 p.p. em todas as faixas, um deslocamento amplo e de mesmo sentido.

**Há explicação inocente plausível que os dados não conseguem descartar:**

- os dados não exigem virada de eleitores de Flávio (retenção de 98,8% e fluxo Flávio → Lula de 0,2%, simétricos aos de Lula);
- a divisão dos eliminados é coerente por candidato (Zema 81% e Caiado 51% para Flávio; Cury 53% para Lula, compatível com um eleitorado popular) e por região (Sul 62% para Flávio, Nordeste 36%);
- a queda de brancos e nulos e o aumento de comparecimento onde Lula é forte são o rastro típico de mobilização;
- a distância para as pesquisas (3,2 a 3,3 p.p.) tem a ordem de grandeza do erro de cabeçalho delas (2,4 a 3,8 p.p. em 2026) e dos erros de 2022 (lá, em sentido oposto, com 5,2 p.p. contra Bolsonaro no 1º turno);
- uma virada uniforme do tamanho do erro das pesquisas deixaria marca que não aparece. Já um enchimento uniforme a partir de ausentes ou anulados não seria visto por este método.

Não é `sustentada` porque a anomalia é do tamanho do erro histórico das pesquisas e tem mecanismo inocente coerente. Não é `refutada` porque o padrão 2026 × 2022 e o tipo "enchimento" não podem ser excluídos com o boletim de urna.

## Casos mais suspeitos

São as UFs com menor retenção estimada de Flávio. São UFs pequenas, com IC largo e ajuste instável.

| UF | Retenção de Flávio | Flávio → Lula | Eliminados → Flávio | Novos → Lula |
|---|---|---|---|---|
| AP | 87,1% | 7,7% | 38,1% | 100% |
| AC | 87,8% | 2,7% | 60,9% | 76,6% |
| RR | 88,8% | 2,1% | 74,1% | 92,8% |
| AM | 95,3% | 3,3% | 36,8% | 100% |
| RJ | 95,4% | 0,0% | 46,4% | 77,8% |
| TO | 96,0% | 1,2% | 37,7% | 100% |

- AL, AM, AP, MA e PA têm novos votantes → Lula em 100%, no limite da restrição.
- Na faixa de municípios com Lula acima de 80% no 1º turno, Flávio cresceu só 0,25 p.p. do eleitorado, contra 5,38 p.p. de Lula. Em 2022, Bolsonaro cresceu 1,51 p.p. nessa mesma faixa, e Lula, 1,39.
- Não foi aplicada correção para buscas múltiplas porque não houve caça a extremos. Os números por UF são descritivos.

## Limites (o que o teste não exclui)

- **Falácia ecológica e viés de agregação.** O IC do bootstrap mede ruído, não esse viés. A dispersão entre especificações é a medida honesta.
- **Fluxos são líquidos.** Rotatividade de comparecimento (quem votou no 1º turno e faltou no 2º, e o inverso) não aparece.
- **Enchimento uniforme e virada pequena (1 a 2%) são indistinguíveis de comportamento real.** Exigem comparecimento físico, biometria, logs e papel (caps. 7 e 8).
- **Pesquisas:** os números citados em alegações não localizados foram descartados. As pesquisas verificadas não publicaram retenção nem o voto de quem anulou ou se absteve no 1º turno; nos cenários, essas peças vêm dos dados ou de suposições declaradas. Os subgrupos de cada eliminado têm poucas centenas de entrevistados (margem de 6 a 8 p.p.) e dependem do voto lembrado do 1º turno.
- **2022 tem limites como linha de base:** granularidade municipal, outros candidatos.

## Fontes

```json
[
  {"id": "cap03-alegacoes", "titulo": "alegações que circulam", "url": null, "acesso": "2026-10-29"},
  {"id": "cap03-datafolha-0810", "titulo": "Diario de Pernambuco — Datafolha: 46% dos eleitores de candidatos derrotados no 1º turno migram para Flávio Bolsonaro (08/10/2026)", "url": "https://www.diariodepernambuco.com.br/politica/2026/10/11726210-datafolha-46-dos-eleitores-de-candidatos-derrotados-no-1-turno-migram-para-flavio-bolsonaro.html", "acesso": "2026-10-29"},
  {"id": "cap03-quaest-2110", "titulo": "O Povo — Pesquisa Quaest mostra Flávio Bolsonaro com 45% e Lula 44% (campo 17–20/10/2026, BR-08535/2026)", "url": "https://mais.opovo.com.br/jornal/politica/2026/10/22/pesquisa-quaest-mostra-flavio-bolsonaro-com-45-e-lula-44.html", "acesso": "2026-10-29"},
  {"id": "ch11-quaest-cruz-2110", "titulo": "Diario de Pernambuco — Quaest: 48% dos eleitores de Augusto Cury migram para Lula e 33% para Flávio (17–20/10, BR-08535/2026)", "url": "https://www.diariodepernambuco.com.br/politica/2026/10/11727201-quaest-48-dos-eleitores-de-augusto-cury-migram-para-lula-e-33-para-flavio.html", "acesso": "2026-10-30"},
  {"id": "cap03-datafolha-2210", "titulo": "O Povo — Datafolha tem empate numérico entre Flávio Bolsonaro e Lula com 50% dos votos válidos (campo 20–22/10/2026, BR-09709/2026)", "url": "https://mais.opovo.com.br/jornal/politica/2026/10/22/datafolha-tem-empate-numerico-entre-flavio-bolsonaro-e-lula-com-50-dos-votos-validos.html", "acesso": "2026-10-29"},
  {"id": "cap03-pesquisas-2022", "titulo": "Brasil de Fato — Datafolha, Ipec, Atlas, Quaest e MDA: as pesquisas deste sábado, véspera da eleição (29/10/2022)", "url": "https://www.brasildefato.com.br/2022/10/29/datafolha-ipec-atlas-quaest-e-mda-as-pesquisas-deste-sabado-vespera-da-eleicao", "acesso": "2026-10-29"},
  {"id": "cap03-erros-2022-1t", "titulo": "O Povo — Lula segue em vantagem em pesquisa para segundo turno, segundo Datafolha (07/10/2022; erros do 1º turno)", "url": "https://www.opovo.com.br/noticias/mundo/2022/10/07/lula-segue-em-vantagem-em-pesquisa-para-segundo-turno-segundo-datafolha.html", "acesso": "2026-10-29"}
]
```

Os dados oficiais (boletins de urna, TSE) devem usar o id que o integrador já tiver para o bweb. O capítulo os cita só no texto da figura (`data-fonte`).

## Pendências e sugestões ao integrador

- **Placar:** `{ "id": "transferencia-de-votos", "veredito": "parcial", "pista": "Os eleitores de Cury, Renan, Caiado e Zema não explicam o crescimento de Lula.", "resumo": "Com a divisão dos eliminados das pesquisas verificadas (Quaest por candidato, Datafolha 06–07/10), Flávio venceria (Lula 48,5–48,6%; distância de 3,2–3,3 p.p.); os dados não exigem virada de eleitores de Flávio (retenção estimada de 98,8%), mas exigem eliminados divididos ao meio e novos votantes majoritariamente lulistas, e o padrão entre turnos difere muito de 2022." }`
- **Sankey:** o integrador já o registrou em `src/lib/echarts.js`.
- **Números de alegações descartados:** os cruzamentos não localizados foram removidos do script, do texto e do simulador. Restam só a Quaest de 17–20/10 por candidato e o Datafolha de 06–07/10. O id `ch11-quaest-cruz-2110` (já em `fontes.json`) é reutilizado. O `cap03-datafolha-2210` não é mais citado no texto, mas fica listado.
- **Testes que separariam enchimento de mobilização:** a hipótese de enchimento uniforme a partir de ausentes ou anulados só se testa com dados de comparecimento por eleitor. Em particular, se a queda de brancos e nulos nos redutos de Lula vem acompanhada de mais habilitações sem biometria (cap. 7) ou de padrões temporais nos logs (cap. 8). Vale cruzar.
- **Estilo dos botões:** os botões de cenário do simulador usam a classe compartilhada `.botao` com estilo inline mínimo. Se houver um padrão de "chips" de cenário, vale adotar.
