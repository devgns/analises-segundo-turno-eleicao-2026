# Capítulo 08 — Os logs das urnas: modelos, alertas, substituições

**Veredito proposto: `refutada`** (para "votos sem rastro / urnas ou modelos que favorecem um lado").
Alternativa se o integrador preferir destacar o caso ES sem explicação: `parcial` — mas a anomalia residual é de 7 seções e < 60 votos líquidos, e não tem direção partidária.

> Placar: "Logs com menos votos que o BU (1.435 seções, −157.290) e substituições de urna escondem votos sem rastro; algum modelo de urna favorece um lado." — Resultado: os votos faltantes estão nos logs das urnas substituídas, dentro do mesmo pacote: 1.425 de 1.432 seções fecham voto a voto com o BU. Modelo de urna, alertas e substituições não têm relação com a variação de Lula (experimento natural dentro do mesmo local: ≤ 0,06 p.p.).

## Reprodução
1. `uv run python analises/logs_eleitor_agregado.py` (passada nos logs por eleitor; compartilhado com o cap. 07)
2. `uv run python analises/08_substituicoes.py` — **rede**: baixa de novo `aux.json` + `log.jez` de 1.432 seções com déficit (BR) + 400 de controle de resultados.tse.jus.br e lê TODOS os `logd.dat` (inclusive `.jez` internos). ~10 min. Saída `data/processed/base/substituicoes_logs.parquet`.
3. `uv run python analises/08_logs.py` → `site/public/data/ch08/*.json`, `data/processed/base/cap08_resultados.json`.

## Achado metodológico importante (afeta a base comum)
O coletor `scripts/baixar_logs_urna.py` lê só o `logd.dat` do topo do `log.jez`, que é o log da **última** urna usada. Quando há substituição, o pacote contém, como `.jez` internos, o log da(s) urna(s) anterior(es). Por isso `n_votos_log` (e os logs por eleitor em `data/processed/logs_urna/eleitores/`) **omitem os votos anteriores à troca** em ~1.435 seções. Para análises por eleitor que precisem de completude, filtrar `n_votos_log == comp_2` ou usar a reconciliação deste capítulo.

## Números-chave

### Substituições / déficit log < BU
- 1.435 seções, −157.290 votos (16 com log principal zerado). 1.432 no Brasil foram rebaixadas (3 são ZZ).
- Somando todos os logs do pacote (cada urna uma vez): **1.425/1.432 fecham exatamente**, 1.429 com |dif| ≤ 2; 1.413 têm duas urnas com votos no dia. Logs internos somam 157.388 votos.
- `nr_urna_2` do bweb = urna do log principal em 1.429/1.432; nessas seções o nº de urna mudou entre turnos em 1.424 (controle: 1 de 400).
- Controle (400 seções sem déficit): 400/400 fecham; nenhum log interno com voto.
- Hora da troca (urna pronta, Brasília): pico 9h (326), 10h (260); espalhada até 17h–18h.
- Δ Lula das substituídas vs município (controles 1º turno, EF município): −0,04 p.p. (IC −0,14 a +0,06; p = 0,44).
- **7 que não fecham**: BA 34711/0021/0178, PI 11533/0003/0216, PB 21750/0002/0254 (−1 voto cada, uma urna, sem troca); BA 35653/0173/0235 (−13) e MA 08893/0047/0609 (−36): log interno da urna original sem votos do dia; RS 89060/0017/0191 (15+75 = 90 vs 92, −2); **ES 57932/0009/0085**: log principal (contingência) com 0 votos e dois logs internos de urnas distintas (01750820: 304 votos; 01841837: 308 votos), ambos desde 8h; comparecimento 308. Sem explicação nos dados públicos — recomenda-se pedido de esclarecimento ao TRE-ES.
- Seções com urna pronta após 8h30 sem déficit: 368 (99 após 9h). Nenhuma urna pronta antes das 8h (Brasília).

### Modelo de urna (seções pareadas, BR)
| Modelo | Seções | Lula 1º | Lula 2º | Δ |
|---|---|---|---|---|
| UE2013 | 11.434 | 47,18% | 53,94% | +6,75 p.p. |
| UE2015 | 87.212 | 45,26% | 51,96% | +6,70 |
| UE2020 | 200.504 | 44,99% | 51,53% | +6,54 |
| UE2022 | 198.746 | 45,16% | 51,83% | +6,66 |

Diferença no Δ vs UE2013 (EP agrupado por município):
- bruto: +0,02 / −0,14 / −0,04 p.p. (todos p > 0,45);
- controles + EF UF: −0,22 / −0,20 / −0,19 p.p. (p = 0,003 / 0,01 / 0,05 — pequeno, contra Lula nas urnas novas); EF município: −0,08 / −0,04 / +0,07 (p > 0,11);
- **experimento natural, EF local de votação (8.497 locais mistos, 71.005 seções)**: UE2015 −0,06 p.p. (p = 0,045), UE2020 −0,04 (p = 0,77), UE2022 −0,04 (p = 0,77). O único p < 0,05 não sobrevive a correção (Holm sobre 12 testes).
- Placebo: nos mesmos locais, seções UE2020/2022 tinham Lula 0,75–0,80 p.p. menor já no 1º turno (alocação não é perfeitamente aleatória dentro do local), mas o Δ não difere.

### Alertas / erros / habilitações sem voto
- Alertas: 7.039.759; mediana 13/seção; p90 24; p99 40; p99,9 59; máx 429. Spearman com biom_sh_2: 0,08.
- Erros: 533.002; 473.868 seções com exatamente 1 (rotina), 1.414 com 0, 16.369 com 2.
- Habilitações sem voto computado: 8.917 (bweb base, incl. ZZ) / 8.847 em 8.286 seções (BR); 7.853 seções com 1.
- Δ Lula vs município por decil de alertas/100 votos: −0,06 a +0,03 p.p. (sem monotonia). Regressão: log(1+alertas) +0,097 p.p. por unidade de log (p < 0,001; dobrar alertas ≈ +0,07 p.p.); erro extra (>1) +0,02 p.p. (p = 0,15); ter habilitação sem voto +0,03 p.p. (p = 0,28).

### Relógio e esquisitices (128.077.685 registros; BR)
| Item | Registros | Seções |
|---|---|---|
| Voto computado sem habilitação registrada | 0 | 0 |
| Voto computado antes da habilitação | 0 | 0 |
| Habilitação antes da digitação do título | 0 | 0 |
| Tempo de cabine negativo | 0 | 0 |
| Voto fora de ordem | 0 | 0 |
| Eleitor sobreposto ao anterior | 0 | 0 |
| Nº de ordem repetido | 0 | 0 |
| Eleitor identificado antes das 8h (Brasília) | 0 | 0 |
| Voto computado sem "Voto confirmado para [Presidente]" | 608 | 585 |
| Votos computados a partir das 17h (Brasília) | 34.330 | 29.854 |
| Habilitações sem voto | 8.847 | 8.286 |
| Seções sem log publicado | 1 (SP 64777/0395/0298, 268 votantes) + 28 ZZ | |

- Votos ≥17h: 34.330 no log principal vs **34.393 do TSE** (diferença 63 ≈ votos em logs de urnas substituídas, não somados aqui).
- Último voto após 18h (Brasília): 1.667 seções (RJ 742, SP 520, BA 245, PE 106, PB 38) — seções prorrogadas (cap. 6).
- Pausas: 4.546 seções com intervalo ≥ 1 h sem eleitor; 385 com ≥ 2 h; mediana da maior pausa 16 min.
- Observação: o coletor só lê linhas datadas de 25/10/2026, então timestamps fora do dia da eleição **não são observáveis** nesta base (limite).

### tipo_urna no bweb
1º turno: 499.206 "Apurada". 2º turno: 499.205 "Apurada" + 1 sem registro (ZZ 30686/0001/0443, sem votos no 2º turno). Nenhuma "contingência"/"voto manual" — o campo não informa as substituições.

## Justificativa
A hipótese de "votos sem rastro" é contrariada diretamente: os votos ausentes no log principal estão nos logs internos e fecham com o BU. Nenhum indicador técnico (modelo, alertas, erros, substituição) tem relação relevante com o Δ de Lula; nenhum evento impossível aparece. Resta um punhado de casos com divergências pequenas, sem direção partidária.

## Limites
- Coerência entre arquivos gerados pelo mesmo software não exclui adulteração do próprio software (ponto correto das alegações). Exclui manipulação posterior (planilhas, transmissão).
- Sem logs do 1º turno.
- As 1.551 substituições do TSE incluem trocas antes do primeiro voto (sem déficit); não reconciliadas exatamente.
- Interpretação dos 608 votos sem confirmação de Presidente (provável abandono de cabine) não verificada na documentação do log.

## Casos para destaque
ES 57932/0009/0085 (dois logs internos com votos completos); MA 08893/0047/0609 (36 votos pré-troca sem log); BA 35653/0173/0235 (13). Tabela completa: `site/public/data/ch08/substituicoes.json`.

## Fontes
```json
[
 {"id": "tse-arquivo-urna", "titulo": "TSE — Arquivos de urna (aux.json, log.jez) do 2º turno 2026, pleito 3221", "url": "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/", "acesso": "2026-10-29"},
 {"id": "tse-logs", "titulo": "TSE — Arquivos de log das urnas, 2º turno 2026", "url": "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/", "acesso": "2026-10-29"},
 {"id": "tse-balanco-2t", "titulo": "TSE — Presidente do TSE anuncia reeleição de Lula e faz balanço do 2º turno das Eleições 2026 (1.551 substituições; URL conforme alegações)", "url": "https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/presidente-do-tse-anuncia-reeleicao-de-lula-e-faz-balanco-do-2o-turno-das-eleicoes-2026", "acesso": "2026-10-29"},
 {"id": "tse-votos-apos-17h", "titulo": "TSE — Eleições 2026: mais de 34 mil votos foram registrados após as 17h no 2º turno (URL conforme alegações)", "url": "https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleicoes-2026-mais-de-34-mil-votos-foram-registrados-apos-as-17h-no-2o-turno", "acesso": "2026-10-29"},
]
```
(URLs de notícias do TSE vêm da lista de referências das alegações; não foram abertas por nós.)
