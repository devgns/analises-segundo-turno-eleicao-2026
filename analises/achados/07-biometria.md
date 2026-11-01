# Capítulo 07: Biometria, eleitores habilitados sem digital

**Veredito proposto: `refutada`**

> Placar: "Votos sem digital teriam sido inseridos por mesários a favor de Lula." Nenhum dos 5 testes mostra a assinatura esperada. Onde a habilitação sem biometria subiu, Lula não cresceu mais: o efeito é +0,01 p.p. por +10 p.p. de taxa dentro do mesmo local, com p = 0,49. As 43 rajadas encontradas têm cara de leitor biométrico com defeito e pendem levemente para Flávio.

## Como reproduzir

Os scripts rodam nesta ordem:

1. `uv run python analises/logs_eleitor_agregado.py`. Faz uma passada única, arquivo a arquivo, pelos 128 milhões de registros e grava o cache em `data/processed/base/log_*.parquet`. Leva uns 6 min na passada e mais uns 2 min no p exato.
2. `uv run python analises/07_biometria.py`. Gera `site/public/data/ch07/*.json` e grava os números em `data/processed/base/cap07_resultados.json`.

Módulo auxiliar: `analises/estat_fe.py`, com OLS com efeitos fixos, erro-padrão agrupado e BH.

## Pista

Segundo o relatório que circulou nas redes, houve 8.632.488 habilitações sem biometria. A Apuração Aberta conta 8.619.842. A suspeita é que mesários tenham liberado eleitores ausentes e que esses votos tenham favorecido Lula.

## Números-chave

### Totais e conferência

| Item | Valor |
|---|---|
| `biom_sh` (`QT_ELEI_BIOM_SEM_HABILITACAO`), 1º turno | 8.342.249 (6,66% do comparecimento) |
| `biom_sh`, 2º turno | **8.632.488** (6,73%), igual ao da conta que circulou |
| Diferença para a Apuração Aberta | 12.646, exatamente o total de RR no 2º turno |
| Variação líquida entre turnos | +290.239 |

- A diferença para a Apuração Aberta indica que essa base provavelmente omitiu Roraima. É uma inferência, não verificada. O exterior (ZZ) tem 0.
- **O que o bweb mede.** O log reproduz o número do bweb: são os eleitores sem habilitação biométrica que tiveram pelo menos 1 tentativa de captura de digital.
  - No log, esse grupo (NT) soma 8.424.781.
  - Seção a seção, nas seções com log completo, a correlação com o bweb é r = 0,996. As contagens são iguais em 75,8% das seções e diferem em até 2 em 96,8%.
- **Grupo que o bweb não conta.** No log há ainda 7.813.905 eleitores habilitados sem nenhuma tentativa de digital (N0), em geral sem biometria cadastrada.
  - Total sem digital: **16.238.686 de 128.077.685 votos no log (12,7%)**.
  - No grupo NT, 6,40 milhões tiveram 4 tentativas e 1,13 milhão tiveram 5.

### Por modelo de urna (modelo do 2º turno)

| Modelo | Taxa sem biometria, 2º turno |
|---|---|
| UE2013 | 9,83% |
| UE2015 | 9,56% |
| UE2020 | 6,02% |
| UE2022 | 5,99% |

Dentro do mesmo local de votação (efeito fixo de local), a UE2020 tem −4,19 p.p. e a UE2022 −4,16 p.p. em relação à UE2013. Os leitores novos falham menos.

### Por UF

- A taxa vai de 4,1% (RR) a 9,0% (PI).
- RS tem 8,5% e SC 7,5%, estados onde Lula teve 42% e 31%.
- Correlação de Spearman entre taxa e fatia de Lula nas UFs: 0,30 (p = 0,13).

### (a) Regressões por seção

Base: 497.896 seções pareadas, sem exterior. Erro-padrão agrupado por município. Os coeficientes estão convertidos para o efeito de +10 p.p. na taxa.

| Especificação | Efeito | IC 95% | p |
|---|---|---|---|
| Nível no 2º turno, só efeito fixo de UF e modelo | +2,10 p.p. | 1,27 a 2,93 | <0,001 |
| Nível no 2º turno + controles do 1º turno, EF de UF | −0,47 p.p. | −0,58 a −0,37 | <0,001 |
| Nível no 2º turno + controles do 1º turno, EF de município | −0,34 p.p. | −0,46 a −0,23 | <0,001 |
| Placebo no 1º turno (nível, EF de município) | +0,46 p.p. | −0,09 a 1,02 | 0,10 |
| Δ Lula ~ Δ taxa, EF de UF | −0,30 p.p. | −0,37 a −0,24 | <0,001 |
| Δ Lula ~ Δ taxa, EF de município | −0,22 p.p. | −0,29 a −0,16 | <0,001 |
| **Δ Lula ~ Δ taxa, EF de local de votação** | **+0,01 p.p.** | −0,02 a +0,04 | 0,49 |

- Correlações simples:
  - Pearson entre taxa e fatia de Lula no 2º turno: 0,068. No 1º turno: 0,063.
  - Entre as variações (Δ): Pearson −0,013 e Spearman −0,016.
- Usando a fração sem digital medida no log (NT+N0), o efeito de +10 p.p. sobre Δ Lula é +0,10 p.p. (p < 0,001). O efeito existe, mas é minúsculo.

### (b) Efeito implícito

- **Teto bruto.** Se todos os 8.632.488 votos sem biometria fossem de Lula, seriam 195% da margem de 4.430.191.
- **Aumento entre turnos.** Somando só os aumentos, seção a seção, chega-se a 1.166.376 (26% da margem). O aumento líquido é de 290.239 (6,6%).
- **Diferença ecológica.** É quanto a fatia de Lula entre os sem biometria supera a dos com biometria, estimada dentro do município.
  - 2º turno: **2,8 p.p.** (IC −4,0 a 9,6).
  - 1º turno: **8,1 p.p.** (IC 1,8 a 14,5).
  - A diferença não cresceu no 2º turno. Como os intervalos de 1º e 2º turno se sobrepõem, não dá para afirmar que a diferença tenha diminuído. A estimativa é ecológica e não tem tradução causal em votos.

### (c) Rajadas

Nulo exato de permutação da ordem dentro da seção. A maior sequência é calculada por combinatória exata e foi validada contra simulação. As janelas usam a distribuição hipergeométrica.

**Calibração.** A tabela mostra a fração de seções com p ≤ limiar.

| Limiar | Rajada | Última meia hora | Após ociosidade (≥15 min) |
|---|---|---|---|
| 0,05 | 2,48% | 1,87% | 0,55% |
| 0,01 | 0,55% | 0,34% | 0,08% |
| 0,001 | 0,069% | 0,034% | 0,002% |
| 0,0001 | 0,015% | 0,004% | 0 |

O único excesso sobre o nulo aparece na cauda extrema da rajada: 1,5 vez o esperado a p ≤ 0,0001.

**Sinalizadas (BH, q < 0,05):**
- 43 seções por rajada;
- **0** por concentração na última meia hora;
- **0** por concentração após ociosidade.

**Composição das 43 rajadas:**
- 1.807 eleitores;
- 89,0% com ≥4 tentativas de digital e 8,8% sem tentativa;
- 7 rajadas vão até o fim da votação;
- a taxa do bweb nessas seções já era de 28,2% no 1º turno e foi de 33,7% no 2º.

Essa é a assinatura de leitor biométrico que parou de funcionar.

**Δ Lula das sinalizadas em relação ao município:**
- −0,48 p.p. (IC −1,13 a +0,16; p = 0,15);
- na regressão com controles e EF de município, +0,31 p.p. (p = 0,40);
- teste simétrico: 2,3% delas na cauda pró-Lula e 14,0% na cauda pró-Flávio, quando o esperado é 10% em cada.

**Ao longo do dia:**
- A fração sem digital fica entre 12% e 13% o dia todo.
- A fração NT cai de 8,0% às 8h para 5,3% às 16h30.
- A partir das 17h a fração sem digital é de 16,4%, sobre 30.132 votos. Isso coincide com filas e prorrogação (ver cap. 6).

### (d) Tempo de cabine (habilitação até voto computado)

| Grupo | Mediana | Até 5 s | Até 2 s | Negativos |
|---|---|---|---|---|
| Biometria | 10 s | 3,02% | 0,002% | 0 |
| Sem digital | 13 s | 3,00% | 0,003% | 0 |

A fração de votos-relâmpago sem digital não prediz Δ Lula (p = 0,75).

### (e) Saltos entre turnos

Teste de duas proporções unilateral com BH.
- 85 seções com aumento significativo, somando +6.998 habilitações.
- 181 seções com queda significativa.
- Δ Lula nas que subiram, em relação ao município: −0,30 p.p. (p = 0,24).

## Casos mais suspeitos (top por rajada)

| UF | Município | Zona/Seção | Votos | Sem digital | Maior rajada | Horário (Brasília) | Δ Lula vs município |
|---|---|---|---|---|---|---|---|
| PR | Ibiporã | 0080/0083 | 291 | 129 | 101 | 12:23–16:50 | +0,4 p.p. |
| PB | João Pessoa | 0077/0078 | 314 | 61 | 42 | 13:53–15:38 | +1,3 p.p. |
| SP | São Paulo | 0392/0040 | 210 | 145 | 107 | 08:18–12:13 | −2,3 p.p. |
| BA | Coribe | 0061/0007 | 200 | 120 | 83 | 10:13–12:54 | −3,7 p.p. |
| SP | Guarulhos | 0394/0417 | 317 | 91 | 41 | 15:24–16:56 | +3,2 p.p. |
| MA | Paço do Lumiar | 0093/0055 | 247 | 63 | 35 | 14:28–16:19 | +1,5 p.p. |
| BA | Terra Nova | 0128/0179 | 234 | 178 | 111 | 11:30–16:41 | −2,3 p.p. |

A lista completa está em `site/public/data/ch07/sinalizadas.json`, com 1.000 seções, das quais 43 têm q < 0,05.

## Justificativa do veredito

A suspeita faz previsões específicas, e nenhuma se confirma:
- correlação positiva entre o aumento da taxa sem biometria e o aumento de Lula;
- rajadas no fim do dia ou após ociosidade;
- votos rápidos;
- seções sinalizadas pró-Lula.

O teste limpo, dentro do mesmo local de votação, dá um efeito nulo com intervalo estreito. Dentro do município, o efeito tem o sinal oposto ao da suspeita. Por isso o veredito é `refutada`, com os limites abaixo.

## Limites

- Não detecta inserções pequenas e espalhadas, de poucas unidades por seção intercaladas com eleitores reais.
- Não detecta um deslocamento uniforme que não dependa da taxa (ver cap. 5).
- Não temos idade por seção. Ela é o principal fator inocente e entra só indiretamente.
- Não temos os logs do 1º turno.
- O log não identifica de quem é o dedo nas tentativas de digital. Tentativas encenadas são indistinguíveis de falhas reais sem o caderno de votação.

## Fontes

```json
[
 {"id": "tse-boletins", "titulo": "TSE — Boletins de urna por seção (bweb), 2026, 1º e 2º turnos", "url": "https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna", "acesso": "2026-10-29"},
 {"id": "tse-logs", "titulo": "TSE — Arquivos de log das urnas, 2º turno 2026 (pleito 3221)", "url": "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/", "acesso": "2026-10-29"},
 {"id": "apuracao-aberta-2t", "titulo": "Apuração Aberta — Auditoria do segundo turno de 2026 (citada pelas alegações; não acessada diretamente)", "url": "https://apuracaoaberta.com.br/auditoria/segundo-turno-2026/", "acesso": "2026-10-29"},
 {"id": "tse-manual-biometria", "titulo": "TSE — Manual do eleitor: entenda como vai funcionar a biometria nas eleições 2026 (URL conforme as alegações, truncada no PDF)", "url": "https://www.tse.jus.br/comunicacao/noticias/2026/Julho/manual-do-eleitor-entenda-como-vai-funcionar-a-biometria-nas-eleicoes-2026", "acesso": "2026-10-29"},
 {"id": "tse-res-23751", "titulo": "TSE — Resolução 23.751/2026 (atos gerais do processo eleitoral), texto compilado", "url": "https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-751-de-26-de-fevereiro-de-2026", "acesso": "2026-10-29"}
]
```

As URLs de notícias e resoluções do TSE vêm da lista de referências das alegações. Não as abrimos.

## Pedidos ao integrador

- Registrar as fontes acima em `fontes.json`. As ids `tse-boletins` e `tse-logs` já existem.
- A URL de `tse-logs` em `fontes.json` aponta para dadosabertos. Sugerimos acrescentar ou trocar pela URL `arquivo-urna/3221`.
