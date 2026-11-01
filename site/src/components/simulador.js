/**
 * simulador.js — painel com controles deslizantes + gráfico que se atualiza ao vivo.
 * O cálculo roda num Web Worker (src/workers/simulacao.worker.js); se o usuário mexe
 * de novo antes de terminar, o worker antigo é encerrado (sem fila de cálculos velhos).
 *
 * @example
 * import { criarSimulador } from '../components/simulador.js';
 * criarSimulador(document.querySelector('#sim-fraude'), {
 *   titulo: 'Injete uma fraude',
 *   tarefa: 'fraude',                         // nome em TAREFAS do worker
 *   controles: [
 *     { id: 'delta', rotulo: 'Tamanho do desvio', min: 0, max: 0.05, passo: 0.001, valor: 0.01, formato: 'pp' },
 *     { id: 'frac',  rotulo: 'Municípios afetados', min: 0.01, max: 1, passo: 0.01, valor: 0.05, formato: 'pct1' },
 *   ],
 *   parametros: (v) => ({ ...v, n: 5570, mu: 0.03, sigma: 0.025, reps: 200 }),
 *   opcao: (r, v, p) => ({ ...opção ECharts usando r (resultado do worker)... }),
 *   resumo: (r, v) => `Poder do detector: ${pct(r.poder)}`,
 *   fonte: 'Simulação própria',
 *   demo: true,
 * });
 */
import { criarGrafico } from './grafico.js';
import { formatador } from '../lib/formato.js';

/**
 * @typedef {object} Controle
 * @property {string} id
 * @property {string} rotulo
 * @property {number} min
 * @property {number} max
 * @property {number} [passo]
 * @property {number} valor
 * @property {string|Function} [formato] ver lib/formato.js#formatador
 * @property {string} [ajuda] texto curto abaixo do controle
 */

/**
 * @param {HTMLElement} alvo
 * @param {{ titulo?:string, tarefa:string, controles:Controle[],
 *           parametros?:(valores:object)=>object,
 *           opcao:(resultado:any|null, valores:object, p:object)=>object,
 *           resumo?:(resultado:any, valores:object)=>string,
 *           altura?:number, subtitulo?:string, fonte?:string, demo?:boolean, espera?:number,
 *           criarWorker?:()=>Worker }} op
 * @returns {{ valores():object, definir(id:string, v:number):void, destruir():void }}
 */
export function criarSimulador(alvo, op) {
  alvo.classList.add('simulador');
  alvo.innerHTML = '';
  if (op.titulo) {
    const h = document.createElement('h3');
    h.className = 'simulador__titulo';
    h.textContent = op.titulo;
    alvo.append(h);
  }
  const painel = document.createElement('div');
  painel.className = 'simulador__controles';
  const saida = document.createElement('div');
  saida.className = 'simulador__saida';
  alvo.append(painel, saida);

  const valores = {};
  const entradas = {};
  const uid = Math.random().toString(36).slice(2, 8);
  for (const c of op.controles) {
    valores[c.id] = c.valor;
    const fmt = formatador(c.formato ?? 'num2');
    const wrap = document.createElement('div');
    wrap.className = 'controle';
    const idIn = `sim-${uid}-${c.id}`;
    wrap.innerHTML = `<label for="${idIn}"><span></span><output for="${idIn}"></output></label>
      <input type="range" id="${idIn}" min="${c.min}" max="${c.max}" step="${c.passo ?? (c.max - c.min) / 100}" value="${c.valor}">
      ${c.ajuda ? '<p class="controle__ajuda"></p>' : ''}`;
    wrap.querySelector('label span').textContent = c.rotulo;
    if (c.ajuda) wrap.querySelector('.controle__ajuda').textContent = c.ajuda;
    const out = wrap.querySelector('output');
    const inp = wrap.querySelector('input');
    out.textContent = fmt(c.valor);
    inp.addEventListener('input', () => {
      valores[c.id] = Number(inp.value);
      out.textContent = fmt(valores[c.id]);
      agendar();
    });
    entradas[c.id] = { inp, out, fmt };
    painel.append(wrap);
  }
  const status = document.createElement('p');
  status.className = 'simulador__status';
  status.setAttribute('aria-live', 'polite');
  painel.append(status);

  const fig = document.createElement('figure');
  fig.style.margin = '0';
  saida.append(fig);
  const resumo = document.createElement('p');
  resumo.className = 'simulador__resumo';
  resumo.setAttribute('aria-live', 'polite');
  saida.append(resumo);

  let ultimo = null;
  const grafico = criarGrafico(fig, {
    dados: null,
    altura: op.altura ?? 340,
    subtitulo: op.subtitulo,
    fonte: op.fonte,
    demo: op.demo,
    tabela: false,
    csv: false,
    opcao: (r, p) => (r ? op.opcao(r, { ...valores }, p) : null),
  });

  const novoWorker = op.criarWorker
    ?? (() => new Worker(new URL('../workers/simulacao.worker.js', import.meta.url), { type: 'module' }));
  let worker = null;
  let ocupado = false;
  let seq = 0;
  let timer = null;

  function rodar() {
    if (ocupado && worker) { worker.terminate(); worker = null; }
    worker ??= novoWorker();
    const id = ++seq;
    ocupado = true;
    status.textContent = 'calculando…';
    worker.onmessage = (ev) => {
      if (ev.data.id !== id) return;
      ocupado = false;
      if (!ev.data.ok) { status.textContent = `erro: ${ev.data.erro}`; return; }
      ultimo = ev.data.resultado;
      status.textContent = `calculado em ${ev.data.resultado.ms ?? '?'} ms`;
      grafico.atualizar(ultimo);
      if (op.resumo) resumo.textContent = op.resumo(ultimo, { ...valores });
    };
    worker.onerror = (e) => { ocupado = false; status.textContent = `erro no worker: ${e.message}`; };
    const params = op.parametros ? op.parametros({ ...valores }) : { ...valores };
    worker.postMessage({ id, tarefa: op.tarefa, params });
  }
  function agendar() {
    clearTimeout(timer);
    timer = setTimeout(rodar, op.espera ?? 120);
  }

  // só calcula quando o painel fica visível
  const io = new IntersectionObserver((ents) => {
    if (ents.some((e) => e.isIntersecting)) { io.disconnect(); rodar(); }
  }, { rootMargin: '200px 0px' });
  io.observe(alvo);

  return {
    valores: () => ({ ...valores }),
    definir(id, v) {
      const e = entradas[id];
      if (!e) return;
      e.inp.value = v;
      valores[id] = Number(v);
      e.out.textContent = e.fmt(valores[id]);
      agendar();
    },
    destruir() { io.disconnect(); worker?.terminate(); grafico.destruir(); },
  };
}
