# Achados: capítulo 05, os detectores conseguem ver uma alteração uniforme? (testes de poder)

**Script:** `analises/05_poder_detectores.py`. Leva de 10 a 20 minutos e usa cerca de 2 GB.
- Para refazer só as assinaturas: `--so-assinaturas`.
- Números completos: `analises/achados/05-poder-detectores.numeros.json`.

**Dados do site:**
- `cap05-poder.json`: curvas de poder.
- `cap05-assinaturas.json`.
- `cap05-municipios.json` (835 KB) e `cap05-secoes.json` (1,3 MB): base do simulador. É uma amostra aleatória de 30 mil seções em formato colunar e passa um pouco do alvo de 1 MB.

**Simulador:** usa o worker próprio `site/src/workers/alteracao.worker.js`, chamado pela opção `criarWorker`. Testado em Node: os resultados batem com os do Python. Por exemplo, FDR com 10% dos municípios e k = 1% vai de 8 para cerca de 125 municípios sinalizados nos dois. Cada execução leva cerca de 1,4 s com 30 réplicas.

## Veredito proposto: `sustentada`

O veredito vale **para a tese metodológica**: "sem outliers" não equivale a "sem alteração uniforme". A suspeita de fraude em si não é testada aqui.

Para o placar, uma frase sugerida:

> "Confirmado: a regressão com FDR não detecta alteração uniforme nem com 8% dos votos de Flávio (mais que o dobro do necessário para virar), embora veja fraudes concentradas de 1–6%; as pegadas de nível dão sinais mistos."

Se o integrador preferir que o veredito descreva a suspeita de fraude, o adequado seria `inconclusiva`.

## Desenho

**Mundo limpo:** os dados reais de 2026. São 497.897 seções pareadas, sem o exterior. Cada réplica re-sorteia a divisão L/F de toda seção pela binomial.

**Fraude:** k = fração dos votos nacionais de Flávio transferida a Lula, com k ∈ {0,5; 1; 2; 3; 4; 6; 8}%. O valor que vira o resultado é **k = 3,69%** (2,21 mi de votos). Seis formatos, todos com o mesmo total:
1. uniforme;
2. proporcional à fatia de Flávio na seção;
3. 10% das seções sorteadas;
4. 10% dos municípios sorteados;
5. só urnas UE2020;
6. só seções encerradas a partir de 17h05.

**Detectores:**
- D1: outliers |z robusto| > 4 da Δ fatia de Lula por seção.
- D2: número de municípios com q < 0,05 (BH) numa regressão congelada no 1º turno, com resíduo de variância a + b/n.
- D3: DP do resíduo.
- D4: χ² de Benford do 2º dígito.
- D5: χ² do último dígito.
- D6: seções com F2 ≤ 0,8·F1.
- D7: inclinação de sL2 sobre o comparecimento.
- D8: DP(y 2026)/DP(y 2022).
- D9: KS entre fatias padronizadas de Flávio no 1º e no 2º turno.
- S1: retenção de F por regressão ecológica.

**Calibração:** 80 réplicas sem fraude e 20 por célula. O alarme dispara fora do intervalo central de 95% das réplicas sem fraude. Isso é um **detector oráculo**, porque conhece os dados limpos, e por isso o poder medido é um limite superior.

## Números-chave

**1. Regressão + FDR, o método das alegações.** Detecção da alteração uniforme por tamanho:

| k | 0,5% | 1% | 2% | 3% | 4% | 6% | 8% |
|---|---|---|---|---|---|---|---|
| Detecção | 0% | 5% | 0% | 0% | 5% | 5% | 0% |

- O número de municípios sinalizados fica em cerca de 8 com ou sem fraude.
- Na fraude proporcional, a detecção chega no máximo a 10%.

**2. Fraudes concentradas vistas pelo FDR:**
- **10% dos municípios:** 45% de detecção com k = 0,5% e 95% com k = 1%. Os sinalizados vão de cerca de 8 para 125. A localização é boa: 95% dos sinalizados eram mesmo manipulados.
- **Seções tardias:** 100% de detecção a partir de 2%.
- **10% das seções:** 25% com 3%, 40% com 4% e 100% com 6%.
- **UE2020:** o oráculo "detecta" a partir de 2%, porque os sinalizados *caem* de cerca de 8 para 0. O analista real veria menos anomalias.

**3. Último dígito:** de 0% a 30% em todos os formatos, sem relação com k. É cego.

**4. Detectores oráculo:** D1, D3, D4, D6, D7, D8, D9 e S1 detectam a alteração uniforme entre 0,5% e 3%. Mas eles dependem de saber o valor limpo, que nenhum analista conhece. Valores nos dados reais:
- **D4:** χ² de Benford = 6.757. Benford já é violado sem fraude.
- **D8:** a dispersão de 2026 já é 1,23 vez a de 2022.
- **D6:** 1.123 seções extremas.
- **D1:** outliers *diminuem* sob a alteração uniforme (de cerca de 160 para 109 com k = 4%), porque o MAD cresce.

**5. Assinaturas de nível nos dados reais.**

**(a) Retenção ecológica municipal (NNLS)**, com IC 95% por bootstrap de 300 réplicas:

| Candidato | 2022 | 2026 |
|---|---|---|
| Direita (Bolsonaro / Flávio) | 105,4% [103,4–106,8] | **97,4% [94,7–100,3]** |
| Lula | 99,6% [96,2–102,1] | 104,7% [102,7–106,3] |

A queda de cerca de 8 p.p. está na direção da tese e é maior que os 3,7 p.p. necessários para virar o resultado. Mas a mesma regressão por seção em 2026 dá retenção de F de 100,1% e de L de 102,1%, e valores acima de 100% mostram o viés do estimador. Uma alternativa inocente é que eleitores de Bolsonaro em 2022 não sejam eleitores de Flávio; a Quaest mediu retenção de F de 94%.

**(b) Redutos de Flávio** (mais de 60%), quase sem eliminados (menos de 2%) e com comparecimento em queda. São 631 seções:

| | Valor |
|---|---|
| Δ Lula | +1.006 |
| Δ Flávio | −4.558 |
| Eliminados no 1º turno | 1.587 |
| Brancos/nulos no 1º turno | 3.437 |
| Δ Lula se uma fraude de 3,69% fosse removida | **−2.013** |
| Seções com perda de Lula, observado → sem a fraude | 31% → 71% |
| Fraude máxima compatível com ΔL ≥ 0 no mundo limpo | 1,2% |

**(c) Todos os redutos com F > 70%** (70.791 seções):
- Hoje, Lula perde votos em 1,2% delas e Flávio em 8,7%.
- Removida uma fraude de 3,69%, Lula perderia em 11,5%, mais que o próprio Flávio.

**(d) Lula acima do estoque** (eliminados + inválidos + aumento de comparecimento):
- 0,48% das seções com F > 70%;
- 3,4% das seções com F < 30%.

O padrão é de troca maior onde Lula já é forte, o oposto do que uma transferência proporcional aos votos de F produziria.

**(e) Seções com menos de 2% de eliminados e comparecimento em queda** (7.010 seções):
- ΔL = +10.986 e ΔF = −23.207;
- Δ comparecimento = −54.926 e Δ inválidos = −26.092.

A queda de F acompanha a abstenção, não um ganho equivalente de L.

## Casos mais "suspeitos" (sinais a favor da tese)
1. A retenção municipal da direita caiu de 105,4% (2022) para 97,4% (2026), enquanto a de Lula subiu de 99,6% para 104,7%.
2. A dispersão municipal da oscilação em 2026 é 23% maior que em 2022.
3. O detector padrão (FDR) é cego à alteração uniforme. Isso não é um sinal de fraude, mas confirma o ponto cego alegado.

## Sinais contrários
- Nos redutos de Flávio sem eliminados, o ganho de Lula cabe no estoque. Uma alteração uniforme do tamanho decisivo implicaria perda de Lula em 71% dessas seções.
- O ganho acima do estoque se concentra onde Lula já é forte.
- A retenção ecológica por seção não mostra perda líquida de F.

## O que não exclui
- Um movimento eleitoral uniforme real produz o mesmo dado que uma alteração uniforme. Só evidência externa distingue os dois: auditoria física, hashes e assinaturas, teste de integridade, pesquisas.
- Os testes usam o dado real como mundo limpo, então uma fraude já embutida nele não é testada.
- O oráculo superestima o poder.
- A regressão ecológica é instável.
- O simulador web aproxima, no nível municipal, a fraude por seção pelo valor esperado.

## Pendências e sugestões
- `cap05-secoes.json` tem 1,3 MB. Dá para reduzir para 20 mil seções se o integrador quiser.
- O veredito de cada detector no simulador é exibido num `<div data-ch05-vereditos>` preenchido pelo próprio JS do capítulo. Pode virar um recurso do componente `simulador.js`, como um callback `aoResultado`; não editei o componente.
- O capítulo 10 (Benford) deve citar que Benford do 2º dígito já falha sem fraude (χ² = 6.757 nas seções reais).

## Fontes

```json
[
  {"id": "tse-boletins", "titulo": "já registrada"},
  {"id": "quaest-2026-10-22", "tipo": "pesquisa", "titulo": "Genial/Quaest — pesquisa presidencial de 22/10/2026 (retenção 95% Lula / 94% Flávio; eliminados 43% F / 37% L), conforme citada no alegações que circulam", "url": "https://www.quaest.com.br/", "acesso": "2026-10-29"}
]
```

Entrada sugerida para `placar.json`:

```json
{ "id": "poder-dos-detectores", "veredito": "sustentada", "pista": "Os testes usuais não enxergariam uma alteração uniforme.", "resumo": "Confirmado: regressão + FDR detecta no máximo 5% das alterações uniformes, mesmo com 8% dos votos de Flávio desviados, mas vê fraudes concentradas de 1–6%; as pegadas de nível dão sinais mistos e não decidem." }
```
