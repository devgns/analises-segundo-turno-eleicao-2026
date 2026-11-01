/**
 * Tema claro/escuro + paleta lida dos tokens CSS (src/styles/tokens.css).
 *
 * - `iniciarTema(botao)`: liga o botão de alternância (auto → claro → escuro).
 * - `paleta()`: objeto com as cores atuais (resolvidas do CSS) para usar nos gráficos.
 * - `aoMudarTema(fn)`: callback quando o tema efetivo muda (toggle ou SO).
 * - `baseGrafico(p)`: opção ECharts base (tipografia, eixos recessivos, tooltip) —
 *   faça merge com a opção do seu gráfico; `grafico.js` já faz isso por você.
 *
 * @example
 * const p = paleta();
 * series: [{ type: 'bar', itemStyle: { color: p.lula } }]
 */

const CHAVE = 'tema-relatorio';
const NUM = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
const ouvintes = new Set();
const mq = window.matchMedia('(prefers-color-scheme: dark)');

const TOKENS = {
  lula: '--lula', lulaClaro: '--lula-claro', flavio: '--flavio', flavioClaro: '--flavio-claro',
  brancos: '--brancos', nulos: '--nulos', abstencao: '--abstencao', neutroMeio: '--neutro-meio',
  texto1: '--texto-1', texto2: '--texto-2', texto3: '--texto-3',
  sup0: '--sup-0', sup1: '--sup-1', sup2: '--sup-2', borda: '--borda', grade: '--grade',
  sustentada: '--v-sustentada', parcial: '--v-parcial', inconclusiva: '--v-inconclusiva',
  refutada: '--v-refutada', naoTestavel: '--v-nao-testavel',
  fonteUi: '--fonte-ui', fonteTexto: '--fonte-texto',
};

/** Preferência salva: 'auto' | 'light' | 'dark'. */
function lerPreferencia() {
  try { return localStorage.getItem(CHAVE) || 'auto'; } catch { return 'auto'; }
}
function salvarPreferencia(v) {
  try { localStorage.setItem(CHAVE, v); } catch { /* modo privado */ }
}

/** Tema efetivo agora: 'light' | 'dark'. */
export function temaAtual() {
  const pref = document.documentElement.dataset.theme;
  if (pref === 'light' || pref === 'dark') return pref;
  return mq.matches ? 'dark' : 'light';
}

/** Cores atuais resolvidas dos tokens CSS. */
export function paleta() {
  const cs = getComputedStyle(document.documentElement);
  const p = { modo: temaAtual() };
  for (const [k, v] of Object.entries(TOKENS)) p[k] = cs.getPropertyValue(v).trim();
  /* rampa divergente Flávio ← neutro → Lula (para mapas de deslocamento) */
  p.divergente = [p.flavio, p.flavioClaro, p.neutroMeio, p.lulaClaro, p.lula];
  /* rampa sequencial (uma matiz) — azul neutro de magnitude, não partidária */
  p.sequencial = p.modo === 'dark'
    ? ['#1d2a3f', '#23406b', '#2d5a9a', '#4f86d4', '#9ec5f4']
    : ['#e6eefa', '#b7d3f6', '#6da7ec', '#2a78d6', '#104281'];
  return p;
}

function emitir() {
  const p = paleta();
  ouvintes.forEach((fn) => fn(p));
}

/** Registra callback chamado com a nova paleta a cada troca de tema. Retorna função para cancelar. */
export function aoMudarTema(fn) {
  ouvintes.add(fn);
  return () => ouvintes.delete(fn);
}

const ROTULOS = { auto: 'Tema: automático', light: 'Tema: claro', dark: 'Tema: escuro' };
const ICONES = { auto: '◐', light: '☀', dark: '☾' };

/** Liga o botão de tema. Ciclo: auto → claro → escuro → auto. */
export function iniciarTema(botao) {
  const aplicar = (pref) => {
    if (pref === 'auto') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = pref;
    if (botao) {
      botao.innerHTML = `<span aria-hidden="true">${ICONES[pref]}</span><span class="sr-only">${ROTULOS[pref]}</span>`;
      botao.title = ROTULOS[pref] + ' (clique para alternar)';
    }
    emitir();
  };
  aplicar(lerPreferencia());
  botao?.addEventListener('click', () => {
    const ordem = ['auto', 'light', 'dark'];
    const prox = ordem[(ordem.indexOf(lerPreferencia()) + 1) % ordem.length];
    salvarPreferencia(prox);
    aplicar(prox);
  });
  mq.addEventListener('change', () => { if (lerPreferencia() === 'auto') emitir(); });
}

/**
 * Opção ECharts base: tipografia UI, eixos/grades recessivos (hairline sólida),
 * tooltip com superfície do tema. Mescle com a sua (`grafico.js` faz isso).
 * @param {ReturnType<typeof paleta>} p
 */
export function baseGrafico(p) {
  const eixo = {
    axisLine: { lineStyle: { color: p.borda, width: 1 } },
    axisTick: { show: false },
    axisLabel: {
      color: p.texto2, fontFamily: p.fonteUi, fontSize: 12,
      formatter: (v) => (typeof v === 'number' ? NUM.format(v) : v), // pt-BR por padrão
    },
    splitLine: { lineStyle: { color: p.grade, width: 1, type: 'solid' } },
    nameTextStyle: { color: p.texto2, fontFamily: p.fonteUi, fontSize: 12 },
  };
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: p.fonteUi, color: p.texto1 },
    animationDuration: 500,
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    legend: {
      top: 0, left: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 12,
      textStyle: { color: p.texto2, fontFamily: p.fonteUi, fontSize: 12 },
    },
    tooltip: {
      backgroundColor: p.sup1, borderColor: p.borda, borderWidth: 1,
      textStyle: { color: p.texto1, fontFamily: p.fonteUi, fontSize: 12 },
      valueFormatter: (v) => (typeof v === 'number' ? NUM.format(v) : v),
      extraCssText: 'box-shadow:0 4px 16px rgba(0,0,0,.12);border-radius:6px;',
    },
    xAxis: eixo,
    yAxis: eixo,
    aria: { enabled: true },
  };
}
