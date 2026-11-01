/**
 * capitulos.js — monta os capítulos a partir de src/capitulos/NN-slug.html (+ NN-slug.js opcional).
 *
 * - Descobre arquivos por glob (não há lista para editar: criar o arquivo basta).
 * - Ordena por NN. O HTML vira string (?raw) e é inserido em #capitulos.
 * - O JS do capítulo só é baixado quando o capítulo chega perto da tela, e então
 *   hidrata os slots declarativos dentro da seção:
 *      [data-grafico="id"]    → export const graficos   = { id: OpcoesGrafico }   (components/grafico.js)
 *      [data-tabela="id"]     → export const tabelas    = { id: OpcoesTabela }    (components/tabela.js)
 *                               (em <figure>, data-tabela="false" é opção do gráfico e é ignorado aqui)
 *      [data-simulador="id"]  → export const simuladores= { id: OpcoesSimulador } (components/simulador.js)
 *      export function montar(secao) { … }  → qualquer coisa a mais (chamada por último)
 *   KPIs ([data-kpis], [data-kpis-src]) e selos ([data-veredito]) não precisam de JS.
 *
 * @example
 * import { inserirCapitulos } from './components/capitulos.js';
 * const lista = inserirCapitulos(document.querySelector('#capitulos'));
 * // lista: [{ numero: 1, id: 'conta-nacional', titulo: '…', curto: '…', secao: HTMLElement }]
 */
import { criarGrafico } from './grafico.js';
import { criarTabela } from './tabela.js';
import { criarSimulador } from './simulador.js';
import { hidratarKpis } from './kpi.js';
import { hidratarVereditos } from './veredito.js';

const htmls = import.meta.glob('../capitulos/*.html', { query: '?raw', import: 'default', eager: true });
const modulos = import.meta.glob('../capitulos/*.js');

const base = (caminho) => caminho.split('/').pop().replace(/\.(html|js)$/, '');

/**
 * Insere todos os capítulos em `alvo` e agenda a hidratação preguiçosa.
 * @param {HTMLElement} alvo
 * @returns {{numero:number|string, id:string, titulo:string, curto:string, secao:HTMLElement}[]}
 */
export function inserirCapitulos(alvo) {
  const arquivos = Object.keys(htmls).sort();
  const lista = [];
  for (const caminho of arquivos) {
    const nome = base(caminho);
    const m = nome.match(/^(\d+)([a-z]?)-/); // sufixo opcional: 08b-… = capítulo complementar "8b"
    if (!m) continue;
    const tpl = document.createElement('template');
    tpl.innerHTML = htmls[caminho].trim();
    const secao = tpl.content.querySelector('section.capitulo');
    if (!secao) {
      console.error(`[capitulos] ${nome}.html precisa de <section class="capitulo" id="…">`);
      continue;
    }
    secao.dataset.arquivo = nome;
    alvo.append(tpl.content);
    const h2 = secao.querySelector('h2');
    lista.push({
      numero: m[2] ? `${Number(m[1])}${m[2]}` : Number(m[1]),
      id: secao.id,
      titulo: h2?.textContent.trim() ?? nome,
      curto: secao.dataset.tituloCurto || h2?.textContent.trim() || nome,
      secao,
    });
    hidratarKpis(secao);
    hidratarVereditos(secao);
    agendarModulo(secao, nome);
  }
  return lista;
}

function agendarModulo(secao, nome) {
  const chave = Object.keys(modulos).find((k) => base(k) === nome);
  const temSlots = secao.querySelector('[data-grafico],[data-tabela]:not(figure),[data-simulador]');
  if (!chave) {
    if (temSlots) console.warn(`[capitulos] ${nome}: há slots mas não existe ${nome}.js`);
    return;
  }
  const io = new IntersectionObserver((ents) => {
    if (!ents.some((e) => e.isIntersecting)) return;
    io.disconnect();
    modulos[chave]()
      .then((mod) => hidratar(secao, mod, nome))
      .catch((e) => console.error(`[capitulos] erro ao carregar ${nome}.js`, e));
  }, { rootMargin: '1200px 0px' });
  io.observe(secao);
}

function hidratar(secao, mod, nome) {
  const falta = (tipo, id) => console.warn(`[capitulos] ${nome}.js não exporta ${tipo}["${id}"]`);
  secao.querySelectorAll('[data-grafico]').forEach((el) => {
    const cfg = mod.graficos?.[el.dataset.grafico];
    if (!cfg) return falta('graficos', el.dataset.grafico);
    criarGrafico(el, typeof cfg === 'function' ? { opcao: cfg } : cfg);
  });
  // <figure data-tabela="false"> é opção do gráfico (esconde "ver dados em tabela"), não slot
  secao.querySelectorAll('[data-tabela]:not(figure)').forEach((el) => {
    const cfg = mod.tabelas?.[el.dataset.tabela];
    if (!cfg) return falta('tabelas', el.dataset.tabela);
    criarTabela(el, cfg);
  });
  secao.querySelectorAll('[data-simulador]').forEach((el) => {
    const cfg = mod.simuladores?.[el.dataset.simulador];
    if (!cfg) return falta('simuladores', el.dataset.simulador);
    criarSimulador(el, cfg);
  });
  if (typeof mod.montar === 'function') mod.montar(secao);
}
