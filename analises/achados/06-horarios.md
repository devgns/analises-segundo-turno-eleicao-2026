# Capítulo 6: A prorrogação e as seções tardias

Scripts:
- `uv run python analises/06b_bweb2022_recebido.py --turno 2`: roda uma vez e baixa o bweb 2022.
- `uv run python analises/06_horarios.py`

Dados do site: `site/public/data/ch06/*.json`. Capítulo: `site/src/capitulos/06-prorrogacao-secoes-tardias.{html,js}`.

## Veredito proposto: `refutada`

A inferência eleitoral (a prorrogação e as seções tardias teriam virado o resultado) é refutada. Os fatos operacionais são verdadeiros:
- a prorrogação foi decidida às 17h02;
- houve 115 minutos sem recebimento de BU.

Resumo para o placar: "O 52,39% só aparece com o relógio local sem fuso e mede a composição das seções (as mesmas deram 55,20% a Flávio no 1º turno). Os logs mostram 34.330 votos após 17h (0,77% da margem), e o deslocamento entre turnos é o mesmo em todas as faixas de encerramento."

Uma alternativa defensável seria `parcial`, porque existe um gradiente residual de até +0,26 p.p. com controles. Ele não se sustenta como anomalia:
- aparece igual no placebo do 1º turno;
- é nulo nas seções que cumpriram a prorrogação.

Por isso recomendo `refutada`.

## Convenções de relógio (verificadas)

- O bweb (`dt_abertura`, `dt_encerramento`, `dt_emissao_bu`) e o `bu_secao` (`ts_*`) usam o horário **local**. O `bu_secao` é idêntico ao bweb em 100% das seções.
- O `dt_bu_recebido` está em **Brasília**: nenhum BU é recebido antes da emissão convertida para Brasília. A exceção são 8 seções no 2º turno e 60 no 1º, com diferenças de poucos minutos, consistentes com desvio de relógio da urna.
- Convertido para Brasília, o encerramento mínimo é 17h00min09s nos dois turnos. Nenhuma seção fechou antes das 17h de Brasília.
- O `ts_ultimo_voto` dos logs também é local.

**Bug encontrado num dado compartilhado.** Em `data/processed/bweb_secao/ano=2022`, **todas as colunas de data são nulas**. O layout de 2022 usa `dd/mm/aaaa`, e `scripts/baixar_bweb.py` só faz parse de `aaaa-mm-dd`.
- Não mexi no cache. Gerei `data/processed/agregados/cap06_bweb2022_t2.parquet` com o `06b` (SHA-512 conferido).
- Sugestão ao integrador: no `baixar_bweb.py`, usar `pl.coalesce` dos dois formatos e regerar 2022.

## Pistas, testes e números-chave

### 1. Os números da conta que circulou (todos reproduzidos)

| Alegação | Reprodução | Definição necessária |
|---|---|---|
| Flávio 52,39% "até 17h" | 52,39% (150.771 seções) | `DT_ENCERRAMENTO` **local**, sem fuso, até 17h00min59s |
| Lula > 6,1 mi nas demais | 6.177.830 | idem |
| 88.071.750 "eleitores" 17h01–17h15 | 88.071.750 | é o **comparecimento**, relógio local, 17h01:00–17h15:59 |
| 1.856.306 após 19h | 1.856.250 (Brasília, >19h00min00s) / 1.858.274 (local, ≥19h) | diferença < 0,01% |

O que muda com outra definição:
- **Em horário de Brasília** (até 17h00min59s), Flávio tem **50,99%**.
- **Nas mesmas seções no 1º turno**, Flávio tinha **55,20%** na versão local e **53,73%** na versão de Brasília. O deslocamento entre turnos dessas seções (cerca de −2,8 p.p. para Flávio) é o mesmo do resto do país.
- O relógio local inclui como "até 17h" todo AC/RO/RR/MT/MS e quase todo o AM, que fecham às 15h ou 16h locais.

### 2. Votos após as 17h (logs)

Os logs cobrem 497.880 urnas e 127.697.456 votos, e foram agregados por seção em streaming. Entre `ts_computado_brasilia ≥ 17:00:00` e as 19h06 (último voto) foram computados **34.330** votos:

| Faixa | Logs (este estudo) | TSE |
|---|---|---|
| 17h–18h | 32.337 | 32.399 |
| 18h–19h | 1.982 | 1.981 |
| ≥19h | 11 | 13 |
| **Total** | **34.330** | **34.393** |

- A diferença de 63 votos (0,18%) é compatível com cerca de 158 mil votos sem log público.
- O urnas-tardias e a CNN chegam aos mesmos 34.330.
- **Concentração no início:** 29.001 votos (84%) entraram até 17h05, sendo 13.961 no minuto 17h00. Só **4.198** foram computados depois de 17h10, em 2.962 seções.
- **Peso no resultado:** 34.330 votos equivalem a 0,77% da margem de 4.430.191.
- **Outras definições:** pelo horário de identificação do eleitor ≥17h são 25.676 votos; pelo relógio local ≥17h, 31.232. O exterior teve 417 votos após as 17h locais.
- **UFs:** SP 8.860, BA 4.190, RJ 4.150, MG 2.253, PE 1.636.
- **Municípios:** São Paulo 4.492, Rio 2.341, Salvador 1.768, Brasília 980.
- **Seções com voto tardio** (29.854): Lula tinha 50,81% no 1º turno e 53,98% no 2º (Δ +3,17 p.p.). No resto, foi de 48,86% para 51,63% (Δ +2,77 p.p.).

### 3. Composição e DiD (mesmas seções)

- **Δ por faixa de encerramento** (fatia de Lula entre os finalistas no 2º turno menos a do 1º): fica entre **+2,30 e +3,25 p.p. em todas as faixas**, embora o nível de partida varie de 46,3% (17h00) a 56,5%.
- **Regressão:** WLS com peso nos votos dos finalistas; efeitos fixos de UF, decis de tamanho e de fatia no 1º turno, capital; erro-padrão agrupado por município; correção de Holm.

Resultados em relação às seções que fecharam às 17h00:

| Classificação | Faixa | Δ extra | IC 95% | p (Holm) |
|---|---|---|---|---|
| Encerramento do 2º turno | 17h05–09 | +0,16 p.p. | 0,07–0,26 | 0,005 |
| Encerramento do 2º turno | 17h10–29 | +0,26 p.p. | 0,10–0,42 | 0,007 |
| Encerramento do 2º turno | 18h00–59 | −0,04 p.p. | — | n.s. |
| Encerramento do 2º turno | ≥19h (6.352 seções que cumpriram a prorrogação) | +0,05 p.p. | −0,14 a +0,25 | n.s. |
| **Placebo:** encerramento do 1º turno | 17h05–17h59 | +0,21 a +0,29 p.p. | — | todos p < 0,001 |

- **Persistência das seções lentas:** 60% das seções com encerramento após 17h10 no 2º turno também fecharam tarde no 1º, contra 32% na base.
- **Dose:** um aumento de 100% na fração de votos após 17h dá +0,79 p.p. (p = 0,08), mas a média dessa fração é 0,03%. A partir de 17h10, o efeito é −0,30 p.p. (p = 0,44).
- **Estudo de evento por minuto** (composição das seções ativas): o Δ fica em cerca de +3,1 p.p. de 16h56 a 17h20, sem quebra às 17h02.

### 4. Curva de apuração e pausas

**2026, 2º turno:**
- Primeiro BU às 17h05.
- **Nenhum BU entre 17h08 e 19h03 (115 min).** É o maior intervalo, e coincide com a suspensão anunciada.
- Mediana de 202 min entre a emissão e o recebimento do BU, contra 89 min no 1º turno.
- Virada definitiva às **20h23**, com 47,3% dos BUs recebidos. A maior vantagem de Flávio foi de 342.531 votos.

**Comparações:**
- **2026, 1º turno:** maior pausa durante a apuração de 27 min (19h32). As de 70 e 61 min já são da cauda, depois da meia-noite.
- **2022, 2º turno:** virada às 18h43, com 68,2% dos BUs, depois de Lula estar até 752.011 votos atrás. Maior pausa de 80 min (22h57, cauda).

**Gradiente por décimo de chegada** (fatia de Lula no último décimo contra o primeiro):

| Série | Primeiro décimo | Último décimo |
|---|---|---|
| 2026, 2º turno | 50,5% | 53,7% |
| 2022, 2º turno | 48,0% | 54,3% |
| Mesmas seções na ordem de chegada do 2º turno, votos do 1º turno | 47,9% | 50,6% |

- O gradiente de 2026 é **menor** que o de 2022.
- Nas mesmas seções, o gradiente já existia no 1º turno.
- **DiD por décimo de chegada** (ajustado): nenhum décimo é significativo após Holm, e todos ficam abaixo de 0,13 p.p. No placebo com o 1º turno, os efeitos são de +0,06 a +0,18 p.p.

### 5. Horário do voto

- 60% dos votos foram computados antes do meio-dia.
- Nas seções que votavam em cada faixa de 20 minutos, o Δ estimado vai de +2,83 a +3,10 p.p.
- Por região, o Δ é estável ao longo do dia: NE cerca de +2,0 a 2,1, SE cerca de +3,5 a 3,6 p.p.
- A divisão por candidato é **estimada** pela proporção da seção.

## Casos mais suspeitos (top N)

- **Seções com mais votos após 17h:**
  - Ouro Branco/AL, zona 50, seção 79: 39 de 44 votos no log foram após 17h. Fechou às 19h00.
  - São Paulo, zona 247, seção 724: 24 votos.
  - São Paulo, zona 280, seção 913: 23 votos.
  - São Miguel das Matas/BA: 22 votos.
  - Água Preta/PE: 20 votos.
  - Bagé/RS, zona 142, seção 263: todos os 15 votos do log foram após 17h.
- **Log muito menor que o comparecimento:** Ouro Branco e Bagé têm esse padrão, típico de urna substituída (o log público é o da urna de contingência). Encaminhar ao capítulo 8.
- **Pausa de 115 min no recebimento** (17h08–19h03): é o fato operacional mais forte. Os dados dizem *quando* os BUs chegaram, não o que a totalização fez na pausa.

## O que não exclui

- Um deslocamento nacional uniforme. É indistinguível de comportamento real só com estes testes.
- O processamento durante a pausa. Precisa de conferência de assinatura e hash dos BUs, que não foi feita.
- Desvios no relógio interno das urnas.
- O voto individual dos eleitores tardios (sigilo).

## Pendências

- O bug de datas de 2022 no `baixar_bweb.py` (acima).
- Conciliar seção por seção os 63 votos de diferença com o TSE.
- Conferir assinaturas e hash de amostras de BUs recebidos depois da pausa.
- O 2022 1º turno não foi incluído na curva (o cache de 2022 tem datas nulas). O `06b --turno 1` resolve, se o integrador quiser.
- Não abri o site no navegador. O build passa, mas convém uma checagem visual dos gráficos `ch06-did` (série custom com barras de erro) e do interativo `[data-ch06-corte]`.

## Fontes (para fontes.json)

```json
[
 {"id":"tse-34mil","titulo":"TSE — Eleições 2026: mais de 34 mil votos foram registrados após as 17h no 2º turno","url":"https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleicoes-2026-mais-de-34-mil-votos-foram-registrados-apos-as-17h-no-2o-turno","acesso":"2026-10-29"},
 {"id":"tse-balanco-2t","titulo":"TSE — Presidente do TSE anuncia reeleição de Lula e faz balanço do 2º turno","url":"https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/presidente-do-tse-anuncia-reeleicao-de-lula-e-faz-balanco-do-2o-turno-das-eleicoes-2026","acesso":"2026-10-29"},
 {"id":"oliberal-34mil","titulo":"O Liberal — TSE: 34,4 mil pessoas votaram após 17h no segundo turno (32.399 / 1.981 / 13; decisão às 17h02)","url":"https://www.oliberal.com/politica/tse-34-4-mil-pessoas-votaram-apos-17h-no-segundo-turno-das-eleicoes-1.1187558","acesso":"2026-10-29"},
 {"id":"cnn-34mil","titulo":"CNN Brasil — 34 mil eleitores votaram após as 17h no 2º turno, mostram dados do TSE","url":"https://www.cnnbrasil.com.br/eleicoes/dados-tse-votacao-apos-prorrogacao/","acesso":"2026-10-29"},
 {"id":"timesbrasil-pausa","titulo":"Times Brasil — TSE pausa apuração do segundo turno após prorrogação da votação","url":"https://timesbrasil.com.br/brasil/decisao-2026-tse-pausa-apuracao-do-segundo-turno-apos-prorrogacao-da-votacao/","acesso":"2026-10-29"},
 {"id":"correio-retomada","titulo":"Correio da Manhã — TSE retoma contagem dos votos às 19h após suspensão provocada por decisão de Zanin","url":"https://www.correiodamanha.com.br/politica/2026/10/329719-tse-retoma-contagem-dos-votos-as-19h-apos-suspensao-provocada-por-decisao-de-zanin.html","acesso":"2026-10-29"},
 {"id":"urnas-tardias","titulo":"Apolinario — repositório urnas-tardias","url":"https://github.com/apolinario/urnas-tardias","acesso":"2026-10-29"},
 {"id":"apuracao-aberta","titulo":"Apuração Aberta — Auditoria do segundo turno de 2026","url":"https://apuracaoaberta.com.br/auditoria/segundo-turno-2026/","acesso":"2026-10-29"}
]
```


Observação: as páginas do TSE devolveram 403 ao fetch automático. Os números atribuídos ao TSE vêm das matérias que o citam (O Liberal, CNN) e das alegações (R01, R15). Os ids `tse-34mil` e `apuracao-aberta` estão listados, mas não são citados no HTML; o integrador pode incluí-los ou não.
