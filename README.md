# Análises independentes da eleição presidencial de 2026

Relatório estatístico sobre dados públicos do primeiro e do segundo turno, com comparações históricas com 2022. As análises apresentam seus métodos, hipóteses e limitações. Padrões atípicos e diferenças entre resultados e modelos podem ter várias causas e não demonstram, por si, irregularidade.

**[Ler o relatório](https://devgns.github.io/analises-segundo-turno-eleicao-2026/)** · [Simulador do 2º turno](https://devgns.github.io/analises-segundo-turno-eleicao-2026/simulador/) · [Fontes e limitações](https://devgns.github.io/analises-segundo-turno-eleicao-2026/#fontes)

O projeto é independente e não representa o TSE ou os institutos de pesquisa citados. Análises tiveram apoio de ferramentas de IA. Contribuições e correções fundamentadas são bem-vindas.

## Conteúdo e dados

- `site/`: site estático em Vite e ECharts com duas abas: o relatório (capítulos, gráficos e fontes) e o simulador do 2º turno (`site/simulador/`).
- `site/public/data/`: dados derivados, pré-calculados e necessários ao funcionamento do site. São incluídos no repositório para que o site possa ser publicado e consultado sem baixar as bases completas.
- `scripts/`: coleta e processamento inicial das fontes públicas.
- `analises/`: scripts estatísticos e documentação dos resultados em `analises/achados/`.

No site, cada gráfico traz embaixo os links para baixar os dados (CSV ou JSON) e para o script de `analises/` que os gerou, aqui no repositório.

**As bases brutas e os caches de processamento não são publicados:** ficam em `data/`, ignorado pelo Git. A cópia local utilizada no desenvolvimento ocupa aproximadamente 4,9 GB; o volume, o tempo de download e os recursos necessários variam conforme as fontes e etapas escolhidas. Os dados derivados do site ocupam aproximadamente 11 MB. Não é necessário baixar as bases para visualizar o relatório.

## Simulador do 2º turno

**[Abrir o simulador](https://devgns.github.io/analises-segundo-turno-eleicao-2026/simulador/)**

Uma ferramenta à parte do relatório: você escolhe como os eleitores de cada candidato do 1º turno (e quem não votou em candidato) se dividem entre Lula e Flávio Bolsonaro no 2º turno, e o placar é recalculado na hora e comparado com o resultado oficial. Os totais de cada turno são os oficiais do TSE; as transferências entre grupos são hipóteses de quem usa. Como o voto é secreto, nenhum cenário mostra como as pessoas de fato votaram, e muitas combinações diferentes chegam ao mesmo placar. Cada cenário pode ser compartilhado por link.

O simulador é gerado a partir de `site/simulador/template.html` com os dados do painel do TSE:

```bash
uv run scripts/gerar_simulador.py   # gera site/simulador/index.html
```

A página entra no build do site junto com o relatório (`npm run build` em `site/`).

## Executar o site localmente

Requisitos: Git e Node.js 22.12 ou superior, com npm.

```bash
git clone https://github.com/devgns/analises-segundo-turno-eleicao-2026.git
cd analises-segundo-turno-eleicao-2026/site
npm ci
npm run dev
```

Abra o endereço exibido pelo Vite. Para testar a versão de produção, execute `npm run build` e `npm run preview`. O build usa caminhos relativos, inclusive nos dados, para funcionar no subdiretório do GitHub Pages.

## Baixar dados e reproduzir análises

Requisitos adicionais: Python 3.11 ou superior e [uv](https://docs.astral.sh/uv/). Na raiz do repositório, instale as dependências com `uv sync`. A reprodução completa demanda acesso à internet, espaço em disco adicional, memória e tempo de processamento; a disponibilidade e as versões dos dados dependem das fontes externas. Os scripts mantêm arquivos intermediários em `data/`. Veja os cabeçalhos dos scripts e `analises/achados/` para detalhes, parâmetros e limitações de cada análise.

1. Baixe os totais do painel e os boletins por seção dos dois turnos de 2022 e 2026:

   ```bash
   uv run python scripts/baixar_2turno.py
   uv run python scripts/baixar_bweb.py --ano 2022 --turno 1
   uv run python scripts/baixar_bweb.py --ano 2022 --turno 2
   uv run python scripts/baixar_bweb.py --ano 2026 --turno 1
   uv run python scripts/baixar_bweb.py --ano 2026 --turno 2
   ```

   O coletor consulta o catálogo do TSE e verifica o SHA-512 quando o arquivo de hash está disponível; o próprio programa informa quando não há hash. Mudanças na fonte ou falhas de rede podem impedir a coleta.

2. Para análises que usam logs e boletins binários de 2026, baixe e processe os arquivos das urnas:

   ```bash
   uv run python scripts/baixar_logs_urna.py
   uv run python scripts/decodificar_bu.py
   uv run python analises/comum.py
   ```

   Essa etapa pode demorar horas. `--uf ac` restringe o download a uma UF; análises nacionais exigem a cobertura correspondente. `--completar` tenta recuperar seções faltantes e relatórios de falhas ficam em `data/processed/logs_urna/`. O processamento de logs usa horário de Brasília estimado a partir do fuso; o exterior e municípios com fuso divergente exigem atenção. Os registros não revelam o voto individual de cada eleitor.

3. Execute a análise desejada a partir da raiz, por exemplo:

   ```bash
   uv run python analises/16_votos_zerados.py
   uv run python analises/17_maues_zero.py
   ```

   Esses scripts geram dados derivados do site. Algumas análises exigem etapas anteriores adicionais: `07_biometria.py` e `08_logs.py` usam `uv run python analises/logs_eleitor_agregado.py`; `08_logs.py` também requer `08_substituicoes.py`. Para `08b_modelos_urna.py`, gere as duas amostras de logs de 2022 conforme o cabeçalho de `08b_baixar_logs_2022.py` (usa `uv run --with py7zr`). Para `06_horarios.py`, execute `uv run python analises/06b_bweb2022_recebido.py --turno 2` e gere o cache de faixas de horário com `uv run python analises/votos_por_faixa.py`. Outros scripts dependem de saídas de análises anteriores; confira seus cabeçalhos antes de executá-los.

As pesquisas no capítulo correspondente incluem coleta e conferência editorial; consulte as fontes indicadas no relatório e os próprios scripts. O repositório não garante que fontes externas permaneçam disponíveis ou imutáveis, nem que todos os resultados possam ser regenerados sem etapas adicionais de conferência. Consulte [o registro de revisão](docs/registro-de-revisao.md) para alterações e ressalvas conhecidas.

## Publicação

O workflow `.github/workflows/pages.yml` instala as dependências do site, compila e publica no GitHub Pages quando há alterações em `site/` na branch `main`; também pode ser executado manualmente em Actions. Em **Settings → Pages**, a fonte deve ser **GitHub Actions**.

## Licença

O código é distribuído sob a [licença MIT](LICENSE). Os dados e fontes de terceiros mantêm suas respectivas condições de uso e atribuição.
