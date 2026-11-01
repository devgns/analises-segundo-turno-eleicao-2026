# Capítulo 08b — Modelos de urna: o padrão de 2022 voltou em 2026?

**Veredito proposto: `refutada`** (para "urnas antigas UE2009–2015 inflaram Lula no N/NE; possível manipulação algorítmica").
A anomalia bruta de 2022 existe e é grande. Mas ela vem da alocação geográfica das urnas, some em 2026 e não acompanha a urna quando a urna é trocada. Os testes justos excluem efeitos acima de ~0,14 p.p. no Brasil e de ~1 p.p. no N+NE, contra os ~10 p.p. alegados.

> Placar: ver entrada `modelos-de-urna` em `site/public/data/placar.json` (inserida logo após `logs-das-urnas`).

## Pista
- pedronauck/eleicoes2022 (README, nov/2022): nas UE2009/2010/2011/2013/2015, a votação de Lula seria "muito diferente" da registrada nas UE2020. O efeito apareceria só no Norte/Nordeste e cresceria nas cidades menores ("mais de 3x o número de votos"). Conclusão do autor: "possível manipulação algorítmica".
- PL/Instituto Voto Legal ao TSE (nov/2022): o pedido era invalidar os votos do 2º turno nesses 5 modelos (59,18% das urnas). Segundo o relatório, só com as UE2020 Bolsonaro teria 51,05%. O argumento técnico era o identificador fixo "67305985" nos logs dos modelos antigos.
- Resposta do TSE: em 23/11/2022, Moraes indeferiu o pedido, disse que as urnas são rastreáveis por patrimônio e código de carga, e aplicou multa de R$ 22.991.544,60 por litigância de má-fé. O plenário confirmou a multa em 15/12/2022.

## Reprodução
1. `uv run --with py7zr python analises/08b_baixar_logs_2022.py --n-estrato 60` (amostra estratificada de 540) e `... --simples 400` (amostra aleatória simples de 400).
   - Os comandos leem o diretório central de cada ZIP por UF do CDN do TSE (`arqurnatot/bu_imgbu_logjez_rdv_vscmr_2022_2t_UF.zip`, até 20 GB) via HTTP Range e baixam só os `.logjez` sorteados para `data/raw/logs_urna_2022_amostra/`.
   - O `.logjez` de 2022 é 7z, por isso o `py7zr` é usado via `uv run --with`, sem tocar no projeto.
   - `--do-disco` reprocessa os arquivos já baixados.
   - Obs.: `resultados.tse.jus.br/oficial/ele2022/arquivo-urna/407/` não existe mais (404). O CDN `arqurnatot` é a fonte que funciona.
2. `uv run python analises/08b_modelos_urna.py` gera `site/public/data/ch08b/*.json` e `data/processed/base/cap08b_resultados.json`. Leva cerca de 3 min.

## Inferência do modelo pelo nº de série (validação)
- Faixas (início inclusivo): UE2009 1.000.000; UE2010 1.215.000; UE2011 1.360.000 (inclui o bloco 1.368–1.370 mil e o bloco 1.600–1.650 mil); UE2013 1.650.000; UE2015 1.750.000; UE2020 2.000.000; UE2022 2.250.000–2.600.000. Os limites vêm dos vãos da distribuição de série, conferidos com os logs.
- **2022, amostra estratificada (540 seções, 23 UFs, inclusive as faixas de fronteira): 540/540 corretas.**
- **2022, amostra aleatória simples (400 seções, 26 UFs): 400/400; IC 95% de Clopper-Pearson de 99,08% a 100%.**
- 2026: a regra aplicada a `nr_urna_2` acerta 497.896/497.896 seções contra o modelo do log.
- As 258.273 urnas de 2022 que reaparecem em 2026 (mesmo nº de série) têm em 2026 o modelo que a regra de 2022 prevê: 100%.
- Contagem de 2022 (2º turno, sem ZZ): UE2009 47.412; UE2010 93.726; UE2011 26.889; UE2013 24.672; UE2015 85.620; UE2020 192.691.
- Identificador do log ("67305985"): aparece em **719/719** logs de UE2009–2015 (3ª coluna de todas as linhas). Nos **221/221** logs de UE2020, essa coluna é o nº de série da urna. O fato técnico apontado pelo IVL está correto. Ele não afeta a identificação do modelo (gravado em linha própria) nem o vínculo log↔seção (o arquivo é publicado por seção).

## Números-chave

### Bruto (reprodução da suspeita)
- N+NE, 2022, 2º turno: UE2009–2015 com 100.240 seções, 15,89 mi de votos em Lula e **69,6%**; UE2020 com 71.313 seções, 11,24 mi de votos e **59,0%**. Diferença: **+10,5 p.p.**
- Nordeste 2022, Lula por modelo: UE2009 72,5%, UE2010 76,4%, UE2011 74,8%, UE2013 72,9%, UE2015 74,0%, UE2020 62,9%. A replicação Codex dá os mesmos números.
- **2026 não repete o padrão**: no Nordeste, Lula fica em UE2013 70,4%, UE2015 69,3%, UE2020 68,8% e UE2022 69,9%. No N+NE, antigas (UE2013–15) 65,9% e novas (UE2020–22) 64,9%, diferença de +1,0 p.p.
- "3×": nas cidades do N+NE com menos de 50 mil votantes havia 82.563 seções antigas e 21.349 UE2020 (razão 3,87). A razão dos votos de Lula é 3,95, ou seja, contagem de urnas. Nessa faixa, a fatia é 72,3% contra 69,2% (+3,2 p.p.).
- Simpson: nas cidades do N+NE com 500 mil votantes ou mais havia 23.227 seções UE2020 e 599 antigas. Lula teve 56,2% nas UE2020 dessa faixa.

### Comparação dentro do local / município (EF, WLS por válidos, EP agrupado por município)
- **Identificação.** Urna antiga e nova no mesmo local: 2022, 163 locais em 70 municípios (Brasil) e **6 locais em 3 municípios (N+NE)**; 2026, 123 locais em 47 municípios (Brasil) e **3 locais em 1 município (N+NE)**.
  - Contrastes antiga×nova com menos de 10 municípios-ponte são marcados como "não identificados" (sem EP/IC/p).
  - **Isso vale para todos os coeficientes N+NE "dentro do local", em 2022 e em 2026.**
  - Divergência com a replicação Codex: ela reporta N+NE 2022 com IC (−0,52 a −0,60). Nossas estimativas pontuais são iguais (−0,51 a −0,61), mas o contraste com a UE2020 depende de 3 municípios.
- **Brasil, EF local, ref. UE2020:**
  - 2022, 1º turno: +0,43 a +0,57 p.p.;
  - 2022, 2º turno: +0,25 a +0,37 p.p. (todos com IC tocando ou cruzando 0);
  - 2026, 1º turno: UE2013 +0,77 [0,13; 1,41], UE2015 +0,60, UE2022 −0,05;
  - 2026, 2º turno: UE2013 **+0,76 [0,15; 1,38], p = 0,015**, UE2015 +0,57 (p = 0,045), UE2022 −0,04.
  - Holm sobre os 34 testes identificados da família (EF local, ref. UE2020): menor p ajustado = 0,51 (UE2013 2026, 2º turno). Nenhum sobrevive.
- **O sinal UE2013 +0,76 (2026), conforme pedido pelo integrador:**
  1. Holm: p ajustado 0,51.
  2. Já existe no 1º turno: +0,77.
  3. Δ 1º→2º turno dentro do local: UE2013 +0,04 [−0,32; 0,40], UE2015 −0,03 [−0,38; 0,33], UE2022 +0,004.
  4. 2022 tem o mesmo desenho de nível (antigas um pouco acima nos dois turnos).
  - Robustez:
    - ref. UE2022: +0,80 (2º turno) / +0,82 (1º turno);
    - sem peso: +0,90;
    - só locais com 6 ou mais seções: +0,77;
    - ≥ 2 seções de cada modelo no local: +0,58 (p = 0,10).
  - Leitura: diferença de nível estável, compatível com a composição das seções. Não há assinatura de manipulação no 2º turno.
- **Brasil, EF município:**
  - 2022, 2º turno: antigas +0,77 a +1,63 p.p.; 1º turno: +1,09 a +2,12 (maior no 1º turno);
  - 2022 N+NE: −0,6 a +1,8, n.s.;
  - 2026: UE2013 −0,44, UE2015 −0,05 (n.s.).

### Δ entre turnos por modelo (seções com o mesmo modelo nos dois turnos)
- 2022 bruto: Lula +1,9 a +2,2 p.p. nas antigas e **+3,0 nas UE2020**.
- 2022 EF município: −0,34 a −0,45 p.p. (todos p < 0,001); EF local: −0,12 a −0,17 (n.s.). **Lula cresceu menos nas urnas antigas**, o contrário do que a tese prevê.
- 2026 EF local: −0,03 a +0,04 (n.s.); EF município: UE2013 +0,19 (p = 0,013), UE2015 +0,04, UE2022 +0,09.

### Experimento natural: troca de urnas 2022 → 2026
- Painel: 460.290 seções com a mesma chave nos dois anos, das quais 443.132 no mesmo local.
  - 157.385 seções tinham UE2009–2011 em 2022 (todas trocadas): 132.384 receberam UE2020/22 e 25.001 receberam UE2013/15.
  - 208.004 seções passaram de antiga para nova; 35.899, de UE2020 para UE2013–15.
- **Seções que perderam a UE2009–2011, variação 2026−2022 da fatia de Lula relativa ao município (EF município):**
  - Brasil, 2º turno: **−0,08 p.p. [−0,14; −0,02]**; 1º turno: −0,73 [−0,94; −0,51];
  - N+NE, 2º turno: −0,13 [−1,00; 0,74];
  - N+NE com menos de 50 mil votantes, 2º turno: −0,61 [−1,75; 0,52];
  - S+SE+CO, 2º turno: −0,08 [−0,13; −0,03].
  - A queda maior no 1º turno indica tendência das próprias seções, não efeito de 2º turno.
- **Persistência (mesmas seções, antigas que viraram novas × seções já UE2020, EF município):**
  - N+NE com menos de 50 mil: 2022 1º turno +8,1 / 2022 2º turno **+8,4** / 2026 1º turno +7,4 / 2026 2º turno **+7,7** p.p. (19 municípios-ponte). A diferença fica com o lugar.
  - Brasil: +1,86 / +1,39 / +0,97 / +1,24.
- **Mesma urna física (238 mil urnas).** Correlação do desvio da seção vs. local entre 2022 e 2026:
  - mesma seção: 0,73;
  - mesmo local, outra seção: −0,12 (mecânico);
  - mesmo município, outro local: −0,001;
  - outro município: 0,003 (UE2013–15: 0,004).
  - A urna não carrega viés próprio.

### Por região / porte (antigas × novas, 2022, 2º turno)
- Bruto Nordeste +11,7 p.p.; Norte +4,9; Sudeste +0,8; Centro-Oeste +1,3; Sul −1,6.
- N+NE com menos de 50 mil, EF município: +9,0 [5,5; 12,5] em 2022, 2º turno, e +8,9 no 1º turno. Esse é o número mais forte a favor da suspeita, mas é igual no 1º turno e persiste após a troca de urna (acima).

## Casos mais suspeitos
1. N+NE com menos de 50 mil votantes, 2022: seções com urna antiga +8,4 a +9,0 p.p. de Lula sobre as UE2020 do mesmo município. Explicado: é igual no 1º turno e se mantém (+7,7) em 2026, com UE2020/22 nas mesmas seções.
2. UE2013 em 2026: +0,76 p.p. dentro do local. É nível, igual no 1º turno; Δ +0,04; Holm 0,51.
3. Seções que perderam a urna antiga: −0,08 p.p. (p = 0,015) no 2º turno. Detectável, mas ~130× menor que o gap bruto, e menor que o −0,73 do 1º turno.

## Limites
- Manipulação idêntica em todos os modelos é invisível a este capítulo (ver caps. 2 e 5).
- N+NE dentro do mesmo local não é identificável (3–6 locais). A região se apoia em EF município e na troca de urnas, com IC de ~±1 p.p.
- Mesma chave de seção ≠ mesmo eleitorado (transferências, revisões).
- O identificador fixo dos logs antigos é questão de rastreabilidade física, não testável com dados públicos.

## Replicação independente
- `analises/replicacao_codex/`: nível dentro do local, ref. UE2020, pesos por válidos, EP por município.
  - 2022 Brasil: antigas +0,28 a +0,37 (IC incluem 0); 2026 Brasil: UE2013 +0,76 [0,08; 1,45].
  - Coincide com nossas estimativas pontuais. A diferença está só na sinalização de identificação do N+NE (acima).

## Mudança em componente compartilhado
- `site/src/components/capitulos.js`: o regex passou a aceitar sufixo de letra (`^(\d+)([a-z]?)-`) e `numero` vira "8b". Os demais capítulos não mudam (ordem por nome de arquivo: 08 < 08b < 09).

## Fontes
```json
[
 {"id": "pedronauck-eleicoes2022", "titulo": "pedronauck/eleicoes2022 — README 'Diferença entre modelos de urnas'", "url": "https://github.com/pedronauck/eleicoes2022", "acesso": "2026-10-30"},
 {"id": "comprova-pl-ivl-2022", "titulo": "Projeto Comprova/Metrópoles — Entenda pedido do PL para anular votos de eleição e a decisão do TSE (30/11/2022)", "url": "https://www.metropoles.com/projeto-comprova/entenda-pedido-do-pl-para-anular-votos-de-eleicao-e-a-decisao-do-tse", "acesso": "2026-10-30"},
 {"id": "migalhas-moraes-pl-2022", "titulo": "Migalhas — Moraes nega ação do PL que questiona urnas e aplica multa de R$ 22 mi (23/11/2022)", "url": "https://www.migalhas.com.br/quentes/377514/moraes-nega-acao-do-pl-que-questiona-urnas-e-aplica-multa-de-r-22-mi", "acesso": "2026-10-30"},
 {"id": "tse-multa-pl-2022", "titulo": "TSE — TSE confirma multa de R$ 22,9 milhões ao PL por litigância de má-fé (dez/2022)", "url": "https://www.tse.jus.br/comunicacao/noticias/2022/Dezembro/tse-confirma-multa-de-r-22-9-milhoes-ao-pl-por-litigancia-de-ma-fe", "acesso": "2026-10-30"},
 {"id": "tse-arquivo-urna-2022", "titulo": "TSE — arquivos de urna transmitidos para totalização, 2º turno 2022 (pleito 407), ZIP por UF", "url": "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2022/arqurnatot/", "acesso": "2026-10-30"}
]
```
Também são citadas as fontes já existentes `tse-boletins`, `tse-boletins-2022` e `tse-arquivo-urna`. A página do TSE (tse-multa-pl-2022) foi localizada por busca e não aberta. O relatório do IVL não foi obtido em fonte primária: o conteúdo vem da reportagem do Comprova.
