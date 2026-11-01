# Achados: capítulo 04, Região dos Lagos e Silva Jardim (casos do RJ)

- **Script:** `analises/04_casos_rj.py`, rodado com `uv run python analises/04_casos_rj.py` (alguns minutos). Os números completos ficam em `analises/achados/04-casos-rj.numeros.json`.
- **Dados do site:** `site/public/data/cap04-*.json`.
- **Fontes externas:** baixadas e guardadas em cache em `data/raw/externo/`. São a API de localidades do IBGE (Região Imediata e Microrregião) e as coordenadas municipais do repositório kelvins.

## Veredito proposto: `parcial`

A anomalia existe:
- os casos estão na cauda nacional em números brutos;
- como aglomerado, a região se distingue do país mesmo com controles do 1º turno.

Mas ela é **do estado do RJ inteiro**, que é a UF mais desviada a favor de Lula. Individualmente, nenhum caso sobrevive ao FDR, e todos são típicos dentro do RJ. O efeito estadual pode ser comportamento eleitoral ou outra coisa, e o dado não distingue as duas.

Silva Jardim, isoladamente, ficaria entre `refutada` e `inconclusiva`:
- o +1 é uma soma de compensações;
- a dispersão por seção é normal;
- o Monte Carlo com os dados do RJ dá 39%.

A pendência (resíduo do CSV) está **refutada** nos dados oficiais.

## Pistas e testes

### o arquivo municipal não fecha
- **Teste:** comparecimento − (válidos + brancos + nulos), nos dados oficiais por seção agregados.
- **Resultado:** o resíduo é **0** nos nove municípios, nos dois turnos. Os +98 (Cabo Frio) e −10 (Iguaba) eram defeitos do CSV derivado.
- **Veredito:** refutada.

### nove municípios com ganho assimétrico
- **Recálculo:** Δ Lula e Δ Flávio conferem exatamente com as alegações nos nove municípios. A oscilação de Flávio entre os finalistas confere com 3 casas.
- **Métrica pré-fixada:** oscilação da fatia de Flávio entre os finalistas (y).
  - Nacional agregado: −2,80 p.p.
  - Mediana municipal: −2,37 p.p.

**Percentis brutos no país (5.571 municípios):**

| Município | Percentil |
|---|---|
| Campos | 0,11 |
| Saquarema | 0,43 |
| Búzios | 1,31 |
| Araruama | 1,76 |
| Cabo Frio | 2,55 |
| Silva Jardim | 2,67 |
| São Pedro da Aldeia | 3,91 |
| Iguaba Grande | 9,69 |
| Arraial do Cabo | 21,6 |

Sete dos nove estão abaixo do 4º percentil e oito abaixo do 10º.

**Gêmeos.** São os 50 vizinhos mais próximos por Mahalanobis, usando as covariáveis do 1º turno:
- porte, fatia de Flávio, peso dos eliminados;
- composição Cury/Renan/Caiado/Zema;
- brancos/nulos e comparecimento.

Campos, Saquarema e Búzios ficaram **abaixo de todos os 50 gêmeos** (percentil 0). Araruama ficou no percentil 8 e Silva Jardim no 12.

**Regressão congelada no 1º turno:**
- Covariáveis:
  - polinômio na fatia de Flávio;
  - peso dos eliminados e interação;
  - composição dos eliminados;
  - brancos/nulos, comparecimento, biometria, porte e capital;
  - efeitos de região, ou de UF na segunda versão.
- Previsão fora da amostra em 10 dobras.
- Variância do resíduo modelada como a + b/n.
- BH sobre os 5.571 municípios.

Resultados:
- **Modelo com região:** R² = 0,642, desvio residual de 0,86 p.p.
  - z dos casos: de −3,16 (Campos, 15º mais desviado para Lula entre 5.571) a +0,29.
  - **Nenhum caso tem q < 0,05.** O mínimo é q = 0,23 (Campos).
  - No país, 16 municípios têm q < 0,05: 9 pró-Lula e 7 pró-Flávio, nenhum no RJ.
- **Modelo com UF:** R² = 0,717.
  - z dos casos: de −2,45 a +1,56; q ≥ 0,76.

**O RJ é a UF com maior resíduo médio pró-Lula:**
- resíduo médio de −0,72 p.p., ponderado, com o modelo sem UF;
- maior oscilação bruta do país (−4,25 p.p.);
- seguem AL (−0,47), RN (−0,43), RR e AP.

### Aglomerado espacial
**Nulo:** os 5.571 aglomerados "município + 8 vizinhos mais próximos" e as 510 Regiões Imediatas do IBGE (p de permutação com grupos aleatórios do mesmo tamanho, depois BH).

Média dos nove casos contra os aglomerados:

| Medida | Média dos nove | Aglomerados mais extremos | Percentil |
|---|---|---|---|
| y bruto | −4,61 p.p. | 6 de 5.571 | 0,11 |
| z (modelo com região) | −1,31 | 78 | 1,4 |
| z (modelo com UF) | — | — | 24 |

Regiões Imediatas:
- **Cabo Frio** (seis casos):
  - y bruto: 9ª de 510, p = 0,0005, q = 0,006;
  - z: 47ª, p = 0,018, q = 0,12.
- **Campos dos Goytacazes:** z 6ª de 510, q = 0,017.
- **Rio Bonito** (onde fica Silva Jardim): z 18ª, q = 0,11.

### Silva Jardim (61 seções)
- **Flávio subiu em 36 seções (+161) e caiu em 22 (−160)**, com 3 seções em zero. O +1 é uma compensação, não uniformidade.
- **Desvio-padrão de ΔF:** 6,88 votos, contra 6,78 esperados em 2.000 sorteios de seções do resto do RJ com o mesmo perfil de porte (percentil 56).
- **Correlação entre ΔF e a variação de comparecimento da seção:** 0,61, igual à do resto do RJ (0,61). Lula cresceu nas 61 seções; no resto do RJ, só 0,14% das seções tiveram queda de Lula.
- **Dispersão acima do esperado em outros casos:** Campos (percentil 100; DP de 8,64 contra 6,97) e Araruama (percentil 99). Nos dois, ΔF acompanha mais a variação de comparecimento (r = 0,71 e 0,74). Descontado esse efeito, o DP cai para 6,05 e 5,73, dentro do normal. **Pendência:** auditar Campos por local de votação.
- **Por local de votação:** ver `cap04-silva-jardim-locais.json`. São 13 locais; a variação de Flávio por local vai de −36 a +26 votos.

### Logs e urnas
- **Modelo de urna:** 100% das 2.950 seções dos casos são UE2020 ou UE2022, contra 76,1% no resto do RJ e 80,0% no Brasil.
- **Regressão dentro do município** (efeito fixo municipal e controle da fatia de Flávio no 1º turno), com seções do RJ e erro agrupado por município:

| Variável | Efeito na fatia de Flávio | EP | p |
|---|---|---|---|
| UE2020/2022 | **+0,445 p.p.** (a favor de Flávio, contrário à suspeita) | 0,056 | < 10⁻¹⁴ |
| Alertas (por 10) | −0,096 p.p. (pequeno, na direção da suspeita) | — | 0,012, sem correção para 5 testes |
| Algum erro no log | −0,13 p.p. | — | 0,42 |
| Taxa sem biometria (por p.p.) | +0,022 p.p. | — | 0,07 |
| Encerramento após 17h05 | −0,06 p.p. | — | 0,10 |

- **Outras comparações:**
  - Alertas por seção: 15,0 nos casos contra 14,3 no resto do RJ.
  - Seções encerradas após 17h05: 8,4% nos casos contra 26,0% no resto do RJ.
  - Em Silva Jardim, a soma de votos no log é igual ao comparecimento.

### Monte Carlo de Silva Jardim (sorteio multinomial explícito, eleitor por eleitor)
**Estoques do 1º turno:** L 4.450, F 8.932, eliminados 897, brancos+nulos 630, ausentes 3.768 (incluindo os +3 aptos).

**Evento principal:** fatia de Flávio entre finalistas ≤ 62,18% (observada). Também reportamos P(F ≤ 8.933) sem e com condicionamento aos válidos (±100).

**Matriz "base das alegações":**
- Retenção F 94% e L 95%. As perdas vão metade direto para o adversário e metade para inválido ou abstenção.
- Eliminados: 43% F, 37% L.
- Reativação de 55% dos brancos/nulos e de 18% dos ausentes, divididos 40:36 entre L e F.

| Cenário | P(fatia ≤ obs.) | P(F ≤ 8.933) | Mediana F |
|---|---|---|---|
| Base, só multinomial (sem incerteza de parâmetro) | **0** (em 200 mil) | 0 | 9.378 |
| Base + Dirichlet 130/80/50 | 17,7% | 7,2% (alegações: 6,04%) | 9.394 |
| Eliminados 20% / 30% / 50% / 64,4% / 70% para F | 52% / 40% / 20% / 11% / 8,9% | | |
| Retenção F 90% / 92% / 94% / 96% / 98% | 52% / 34% / 17% / 6,6% / 1,4% | | |
| Concentração 20 / 50 / 80 / 200 / 1000 | 26% / 21% / 17% / 8,1% / 0,25% | | |
| Matriz do resto do RJ (NNLS por seção), só multinomial | 11% | 0,001% | 9.057 |
| Matriz do resto do RJ + variação municipal do RJ (τ = 0,63 p.p.) | **39%** | 9,8% | |

Contra a matriz do RJ, Silva Jardim tem z = −0,24 e é o 53º de 92 municípios do RJ (q BH = 0,69).

**Leitura:**
- A cauda pequena das alegações vem inteiramente da incerteza de parâmetro.
- Com taxas "conhecidas", o resultado seria impossível. Mas com as taxas e a variação que o próprio RJ exibiu, o resultado é comum.
- A diferença entre P(F ≤ 8.933) e P(fatia ≤ obs.) na matriz de dados vem do comparecimento previsto, que é maior que o observado. A métrica pela fatia é a adequada.

## Casos mais suspeitos (top)

1. **Campos dos Goytacazes:**
   - −5,94 p.p., percentil nacional 0,11, abaixo de todos os 50 gêmeos;
   - z = −3,16 (15º de 5.571, q = 0,23);
   - DP por seção no percentil 100;
   - Região Imediata 6ª do país (q = 0,017).
2. **Saquarema:** −5,15 p.p., percentil 0,43, abaixo de todos os gêmeos, z = −2,12.
3. **Armação dos Búzios:** −4,78 p.p., percentil 1,31, abaixo de todos os gêmeos, z = −1,86.
4. **Região Imediata de Cabo Frio (conjunto):** 9ª de 510 em oscilação bruta (q = 0,006).
5. **Silva Jardim:** percentil 2,67 bruto. Mas +161/−160 por seção, z = −1,36 (q ≈ 1), 53º de 92 no RJ.

**Fora do RJ, no mesmo modelo:**
- maiores desvios pró-Lula: Rafael Godeiro (RN, z = −7,8), Pracuúba (AP), São Tomé (RN), Paranhos (MS);
- maiores desvios pró-Flávio: Belo Monte (AL, z = +11,1), Santo Antônio de Lisboa (PI).

## O que não exclui
- **Efeito comum ao estado:** um deslocamento estadual do RJ, ou nacional, é absorvido pelos efeitos fixos. O teste mostra só que a alteração, se houve, não se concentrou nos nove.
- **Regressão ecológica:** a matriz "dos dados" é instável.
- **Comparação com 2022:** não foi feita por seção, porque as seções não casam.
- **Assinatura digital:** não foi validada.
- **Seleção:** os nove foram escolhidos depois de olhar os dados. Os testes de aglomerado mitigam, mas não eliminam, esse viés.

## Sugestões ao integrador
Os itens abaixo são para o integrador, não para componentes compartilhados:
- `tabela.js` poderia aceitar dados inline com cabeçalho HTML. Não é necessário.

## Fontes

```json
[
  {"id": "tse-boletins", "titulo": "TSE — Boletins de urna por seção, 2026 (já registrada)"},
  {"id": "ibge-localidades", "tipo": "dado oficial", "titulo": "IBGE — API de Localidades: municípios, Regiões Imediatas e Microrregiões", "url": "https://servicodados.ibge.gov.br/api/v1/localidades/municipios", "acesso": "2026-10-29"},
  {"id": "kelvins-coords", "tipo": "base auxiliar", "titulo": "kelvins/municipios-brasileiros — coordenadas das sedes municipais (CSV)", "url": "https://github.com/kelvins/municipios-brasileiros", "acesso": "2026-10-29"}
]
```

Entrada sugerida para `placar.json`:

```json
{ "id": "casos-rj", "veredito": "parcial", "pista": "Região dos Lagos e Silva Jardim têm resultados anômalos.", "resumo": "Os nove estão na cauda do país e formam um aglomerado anômalo, mas o desvio é do RJ inteiro: nenhum passa no FDR e todos são típicos dentro do estado; o +1 de Silva Jardim é soma de +161 e −160 por seção." }
```
