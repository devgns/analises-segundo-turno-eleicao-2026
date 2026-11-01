# Maués: reexame da seção 5/176

Reprodução: `OPENBLAS_NUM_THREADS=1 uv run python analises/17_maues_zero.py`. Saída: `site/public/data/ch09/maues-reexame.json`. As comparações e faixas foram escolhidas depois da identificação do caso, portanto são exploratórias.

## Resultado dos boletins

| Medida | 1º turno | 2º turno |
|---|---:|---:|
| Lula | 310 | 333 |
| Flávio | 16 | 0 |
| Outros candidatos | 3 (Caiado) | — |
| Brancos | 0 | 0 |
| Nulos | 2 | 4 |
| Comparecimento | 331 | 337 |
| Aptos | 382 | 382 |

É a maior queda para zero de Flávio entre as 106 seções com zero no segundo turno: a segunda maior foi 5→0. A urna registrada tem o mesmo número de série nos dois turnos. O BU binário local decodificado do 2º turno e o bweb concordam em 333 votos Lula, zero Flávio, quatro nulos e 337 votantes; o resumo do log conta 337 votos computados. O acordo é uma checagem útil de consistência entre arquivos, não comprovação independente das escolhas nas urnas. Não comparamos BU impresso, cadernos, RDV independente, assinatura nem os registros de ocorrências locais.

No código do local 1406 há outra seção, a 179: Flávio passou de 1 a 0 e Lula de 126 a 123. A queda de um voto não é comparável à de 16 votos na seção 176 e não explica o resultado dela. Uma consulta secundária que usa cadastro do TSE identifica o local como [E. M. Indígena Uniawasap'i](https://vototeca.com.br/locais-de-votacao/2026/am/maues/zona/5/local/1406); não verificamos diretamente o cadastro original do TRE-AM. Isso não autoriza inferências sobre o voto ou a origem de pessoas individuais.

Em Maués como um todo, o comparecimento caiu de 28.766 para 27.615, Flávio de 4.655 para 4.407 e Lula de 22.574 para 22.523. A seção 176, ao contrário do município, teve seis votantes a mais no saldo. Não sabemos quais eleitores saíram ou entraram. O [boletim do MPC-AM](https://mpc.am.gov.br/2026/10/boletim-de-11-de-outubro-risco-atmosferico-no-amazonas/) registra agravamento de incêndios e fumaça no estado no período, com medições citadas para Manaus e municípios próximos; não mede a exposição, a insatisfação ou as escolhas dos eleitores dessa seção.

## Modelos e sensibilidade

1. **Fração fixa, votos independentes.** Supondo que cada um dos 333 votos válidos do 2º turno tenha exatamente a probabilidade 16/329 de ir para Flávio, independentemente dos demais, a chance de zero é `(313/329)^333 = 6,17e-8`, cerca de 1 em 16,2 milhões. Essa conta trata a taxa de 1º turno como conhecida e imutável e não modela os mesmos eleitores, a mudança do comparecimento, o comportamento entre turnos ou correlações.
2. **Incerteza da taxa, com mesmas hipóteses de independência e estabilidade.** Com distribuição inicial Beta(1/2,1/2), a distribuição preditiva beta-binomial estima a chance de zero em 7,99e-6, cerca de 1 em 125 mil. É um cenário de sensibilidade, não uma distribuição calibrada para esta comunidade; a escolha da distribuição inicial e a independência afetam o resultado.
3. **Fisher unilateral.** Para `[[16,313],[0,333]]`, sob proporções iguais e amostras independentes, o p bruto é 1,1476e-5, cerca de 0,00115%. Esse p é uma medida de incompatibilidade com o modelo, não a chance de fraude. Pessoas votam nos dois turnos: a independência não foi demonstrada e o teste exato pode não estar calibrado para esses dados pareados.
4. **Busca nacional.** Repetindo esse mesmo cálculo unilateral em 499.205 seções pareadas com votos válidos em ambos os turnos, Maués aparece na 7ª posição. O ajuste de Holm dá 1,0 e BH dá 0,818; essas correções não tornam válida a hipótese de independência entre turnos. A escolha do caso após vasculhar muitas seções importa. Não passar um limiar corrigido não prova que a seção esteja correta.
5. **Comparação descritiva.** Entre 526 seções que tinham 10–22 votos em Flávio, 250–400 válidos e Lula ≥85% entre os dois finalistas no primeiro turno, uma zerou Flávio no segundo: Maués. No Amazonas foram 47 seções e uma zerada. As faixas foram definidas após observar Maués e não foram escolhidas aleatoriamente; 1/526 não é probabilidade de fraude, nem teste confirmatório.

A [Quaest](https://quaest.com.br/segundo-turno-2026-votos-brancos-nulos/) reportou 94% de retenção declarada para Flávio em uma pesquisa nacional. Essa informação apoia examinar uma queda de 16 a zero, mas não estima a retenção específica de uma seção e não estabelece independência entre os 16 comportamentos. Se se impusesse, apenas como hipótese ilustrativa, retenção individual independente de 94% para os 16 e nenhum voto novo para Flávio, a probabilidade de todos não o repetirem seria `0,06^16 ≈ 2,82e-20`; não há evidência que valide essas premissas locais.

Os totais não exigem que os 16 tenham migrado para Lula. Um exemplo **puramente contábil**, não uma reconstrução dos fatos: os 16 eleitores de Flávio deixam de comparecer, os outros 315 votantes do primeiro turno retornam, e 22 dos 51 que antes se abstiveram comparecem; um eleitor de Caiado e os 22 novos votam Lula, e os outros dois de Caiado mais os dois antes nulos votam nulo. Isso reproduz 333 Lula, zero Flávio, quatro nulos e 337 comparecimentos. Não sabemos se essa combinação ocorreu ou é plausível na comunidade; ela mostra que o saldo de +6 não identifica a rotatividade. Outras combinações, incluindo migração ou erro/irregularidade, não são excluídas pelos totais.

## Conclusão e próximos passos

A seção é um caso **fortemente atípico sob modelos simplificados** e é legítimo priorizá-la para conferência; a resposta anterior deu pouco peso ao contraste de 16→0. Os boletins e as contagens não determinam a causa, nem permitem calcular uma probabilidade confiável de fraude. A diferença entre 2022 e 2026 é contexto, não absolvição. Próximos passos: localizar a via impressa e sua procedência, conferir a assinatura/autenticidade dos arquivos e o BU publicado, obter atas e ocorrências, informações agregadas de presença nos dois turnos e esclarecer eventuais alterações de seção. Manter o sigilo do voto; nem log nem RDV, isoladamente, provam em quem um eleitor identificado votou.
