# Como contribuir com um capítulo (para agentes)

Site estático: Vite + JS puro, uma página longa. Cada capítulo = 1 arquivo HTML + 1 JS opcional + JSONs de dados. Edite **só os arquivos do seu capítulo** e as entradas dele em `public/data/placar.json` / `public/data/fontes.json`.

## 1. Arquivos

| O quê | Onde |
|---|---|
| Texto/estrutura | `src/capitulos/NN-slug.html` (já existe um placeholder) |
| Gráficos, tabelas, simuladores | `src/capitulos/NN-slug.js` (crie se precisar; mesmo nome-base do HTML) |
| Dados | `public/data/chNN/*.json` (servidos como `data/chNN/...`) |
| Veredito + resumo no placar | `public/data/placar.json` (entrada com `id` = id da `<section>`) |
| Fontes citadas | `public/data/fontes.json` |
| GeoJSON | `public/data/geo/*.json` |

Descoberta é automática (glob): **não há lista para registrar**. Ordem = `NN`. Não renomeie arquivos nem o `id` da `<section>` (links e placar dependem dele).

## 2. Estrutura obrigatória do HTML

```html
<section class="capitulo" id="slug" data-titulo-curto="Rótulo curto do sumário">
  <header class="capitulo__cabecalho">
    <div class="capitulo__numero">Capítulo N <span data-veredito-capitulo></span></div>
    <h2>Título completo</h2>
  </header>
  <aside class="caixa caixa--pista">
    <div class="caixa__rotulo">O que circula <span class="caixa__fonte">Redes sociais, após o 2º turno</span></div>
    <p>A alegação, na versão mais forte e justa, atribuída de forma verdadeira. Nunca afirme fraude na voz do relatório.</p>
  </aside>
  <div class="capitulo__corpo"> …texto… </div>
  <aside class="caixa caixa--teste"><div class="caixa__rotulo">O teste</div> … </aside>
  <div class="capitulo__corpo graficos"> …slots… </div>
  <aside class="caixa caixa--resultado"><div class="caixa__rotulo">Resultado <span data-veredito-capitulo></span></div> … </aside>
  <aside class="caixa caixa--limites"><div class="caixa__rotulo">O que isso não exclui</div> … </aside>
</section>
```

- Pode intercalar mais `capitulo__corpo`, `<h3>`, gráficos etc. entre as caixas, mas mantenha a ordem Pista → teste → Resultado → limites.
- Filhos diretos ficam na largura de leitura (~70 caracteres). Para algo mais largo (gráfico, tabela, simulador), adicione a classe `largo`.
- `[data-veredito-capitulo]` é preenchido a partir de `placar.json` — **não** escreva o veredito à mão no HTML.
- Selo avulso: `<span data-veredito="refutada"></span>`.
- Placeholder: `<p class="em-producao">Conteúdo em produção.</p>` — remova quando escrever.
- Caixa de demonstração/aviso: `<div class="caixa caixa--demo">…`.
- HTML é inserido como está (sem sanitização, sem scripts inline). Nada de `<script>` no HTML; use o JS do capítulo.

## 3. Vereditos (`public/data/placar.json`)

```json
{ "id": "mapa-da-virada", "veredito": "parcial",
  "pista": "Frase curta da suspeita.", "resumo": "Uma frase do resultado." }
```
Valores: `sustentada` (evidência apoia), `parcial` (anomalia existe, explicação inocente plausível), `inconclusiva` (dados não decidem), `refutada` (teste contradiz), `nao-testavel` (faltam dados), `pendente`. Capítulos 15–17 (conclusões, metodologia, fontes) não entram no placar.

## 4. Slots declarativos + JS do capítulo

No HTML:
```html
<figure class="grafico largo" data-grafico="ch02-mapa" data-src="data/ch02/deslocamento.json"
        data-titulo="…" data-subtitulo="…" data-fonte="TSE — boletins de urna, 1º e 2º turnos 2026"
        data-altura="420" data-csv="data/ch02/deslocamento.csv"></figure>
<div class="largo" data-tabela="ch02-tabela"></div>
<div class="largo" data-simulador="ch02-sim"></div>
<div class="largo" data-kpis-src="data/ch02/kpis.json"></div>      <!-- sem JS -->
<div data-kpis='[{"rotulo":"Municípios","valor":5570,"formato":"num"}]'></div>
```
Atributos de `<figure>`: `data-src`, `data-titulo`, `data-subtitulo`, `data-fonte`, `data-altura` (px), `data-csv` (caminho de CSV pronto, ou `false`), `data-demo` (selo DEMONSTRAÇÃO), `data-tabela="false"` (esconde "ver dados em tabela"; numa `<figure>` é opção do gráfico, não slot de tabela — `capitulos.js` ignora `figure[data-tabela]`). Tudo isso também pode ir no objeto JS.

No JS (`src/capitulos/NN-slug.js`), exporte objetos com chaves = ids dos slots:
```js
import { pct, pp, num, compacto } from '../lib/formato.js';
import { registrarMapa } from '../components/mapa.js';

export const graficos = {
  'ch02-mapa': {
    // json = conteúdo de data-src; p = paleta do tema atual; ctx.largura = px da área
    opcao: (json, p, ctx) => ({ xAxis: {...}, yAxis: {...}, series: [...] }),
    // opcional: aoMontar(chart, echarts) { chart.on('click', …) }
  },
  // atalho: 'id': (json, p, ctx) => opção
};
export const tabelas = {
  'ch02-tabela': { src: 'data/ch02/municipios.json', porPagina: 50, filtro: true,
    ordem: { chave: 'delta', direcao: 'desc' },
    colunas: [ { chave: 'municipio', rotulo: 'Município' },
               { chave: 'delta', rotulo: 'Δ Lula', formato: 'pp' } ] },
};
export const simuladores = { 'ch02-sim': { /* ver seção 6 */ } };
export function montar(secao) { /* opcional: qualquer coisa extra; roda por último */ }
```
O JS só é baixado quando o capítulo se aproxima da tela; o ECharts só quando o primeiro gráfico aparece. O gráfico se redesenha sozinho ao trocar tema e ao redimensionar — por isso **leia cores sempre de `p`**, nunca hex fixo.

## 5. Regras de gráfico (siga — derivadas da skill dataviz)

- Cores: `p.lula`, `p.flavio`, `p.brancos`, `p.nulos`, `p.abstencao`; texto `p.texto1/2/3`; grade `p.grade`. Divergente (Flávio ← neutro → Lula): `p.divergente`. Magnitude: `p.sequencial` (uma matiz). Vereditos: `p.sustentada` etc. — **nunca** para séries.
- Um eixo y só (nunca eixo duplo). Escalas diferentes → dois gráficos.
- Barras: `barMaxWidth: 24`, `itemStyle.borderRadius: [4,4,0,0]`. Linhas: largura 2. Marcadores ≥ 8 px. Área: opacidade 0,1.
- ≥ 2 séries → legenda (a base já põe no topo). Rótulos diretos só seletivos (fim da linha, extremo). Texto nunca na cor da série.
- A base (`lib/tema.js#baseGrafico`) já define fonte, eixos recessivos, tooltip, números pt-BR. Formate valores com `lib/formato.js` (`pct` recebe **fração**; `pp` recebe fração e devolve "+1,23 p.p.").
- Celular: use `ctx.largura < 560` para reduzir rótulos. Nunca rolagem horizontal na página.
- Mapas: `await registrarMapa('br-municipios')` dentro de `opcao` (async é permitido); arquivo em `public/data/geo/br-municipios.json`, simplificado (< 3 MB), com `properties.codigo_ibge`. Use `nameProperty: 'codigo_ibge'`.
- Precisa de um tipo ECharts ainda não registrado? Acrescente em `src/lib/echarts.js`. Já registrados: bar, line, scatter, map, heatmap, boxplot, custom, pie, sankey.

## 6. Simuladores

```js
export const simuladores = { 'ch05-sim': {
  titulo: '…', subtitulo: '…', fonte: '…', demo: false,
  tarefa: 'fraude',                       // nome em TAREFAS de src/workers/simulacao.worker.js
  controles: [ { id: 'delta', rotulo: '…', min: 0, max: 0.05, passo: 0.001, valor: 0.01, formato: 'pp', ajuda: '…' } ],
  parametros: (v) => ({ ...v, n: 5570 }), // valores dos sliders → params do worker
  opcao: (resultado, v, p) => ({ … }),    // opção ECharts a partir do resultado
  resumo: (resultado, v) => 'frase ao vivo',
} };
```
Tarefa nova: escreva `function minha(params, rng)` no worker e registre em `TAREFAS`. Use só `rng()` (semente → reprodutível). Mantenha < ~1 s por execução.

## 7. Fontes / notas

1. Registre em `public/data/fontes.json`: `{ "id": "tse-bu-2t", "tipo": "dado oficial", "texto": "…", "url": "…", "acesso": "AAAA-MM-DD" }`.
2. Cite: `texto<sup class="ref" data-ref="tse-bu-2t"></sup>` (vários: `data-ref="a b"`). Numeração automática por ordem de aparição; lista no capítulo 14.
3. Ids únicos e estáveis; não apague fontes de outros capítulos.

## 8. Formato dos dados

```json
{ "meta": { "titulo": "…", "fonte": "TSE — …", "descricao": "…", "gerado_em": "2026-10-29",
            "script": "scripts/ch02_deslocamento.py", "demo": false },
  "dados": [ { "uf": "RJ", "municipio": "Silva Jardim", "codigo_ibge": 3305604, "delta": 0.031 } ] }
```
- `dados` = linhas planas → CSV e "ver dados em tabela" automáticos. Se precisar de outra forma, ponha o resto em chaves extras e forneça `data-csv`.
- Proporções como **fração** (0–1), não %. Chaves em `snake_case` sem acento. Arredonde (4–5 casas) para manter arquivos pequenos; mire < 1 MB por gráfico.
- Registre em `meta.script` o script que gerou o arquivo (reprodutibilidade).

## 9. Verificar

```bash
cd site && npm install && npm run build      # deve passar sem erros
npx vite preview --port 4173                 # em background; abra http://localhost:4173/#slug
```
Erros de slot ausente aparecem no console como `[capitulos] …`. `demo.json`, `demo-kpis.json` e os simuladores de demo (caps. 1, 3, 5) são DEMONSTRAÇÃO: substitua-os pelo conteúdo real do capítulo e apague o que não usar.
