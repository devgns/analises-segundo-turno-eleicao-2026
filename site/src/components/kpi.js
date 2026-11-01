/**
 * kpi.js — blocos de "número grande".
 * Valor em sans semibold, rótulo em caixa de frase, sem dois-pontos.
 * A cor (opcional) vai numa marca lateral, nunca no texto.
 *
 * @example
 * import { criarKpis } from '../components/kpi.js';
 * criarKpis(document.querySelector('#kpis-ch01'), [
 *   { rotulo: 'Votos de Lula no 2º turno', valor: 60345999, formato: 'compacto', detalhe: '+10,4 mi vs 1º turno', cor: 'lula' },
 *   { rotulo: 'Diferença final', valor: 0.0358, formato: 'pp' },
 *   { rotulo: 'Seções analisadas', valor: 472075, formato: 'num' },
 * ]);
 *
 * Declarativo (JSON inline ou arquivo):
 *   <div data-kpis='[{"rotulo":"Seções","valor":472075,"formato":"num"}]'></div>
 *   <div data-kpis-src="data/ch01/kpis.json"></div>   (arquivo = array ou {dados:[…]})
 */
import { formatador } from '../lib/formato.js';
import { carregarJSON, linhasDe } from '../lib/dados.js';

/**
 * @typedef {object} Kpi
 * @property {string} rotulo
 * @property {number|string} valor
 * @property {string|Function} [formato='num'] ver lib/formato.js#formatador
 * @property {string} [detalhe]   linha menor abaixo (comparação, período, ressalva)
 * @property {'lula'|'flavio'|'brancos'|'nulos'|string} [cor] token CSS (sem `--`) para a marca lateral
 */

/**
 * @param {HTMLElement} alvo
 * @param {Kpi[]} itens
 */
export function criarKpis(alvo, itens) {
  alvo.classList.add('kpis');
  alvo.replaceChildren(...itens.map((k) => {
    const d = document.createElement('div');
    d.className = 'kpi';
    const valor = typeof k.valor === 'number' ? formatador(k.formato ?? 'num')(k.valor) : k.valor;
    d.innerHTML = `${k.cor ? `<span class="kpi__marca" style="background:var(--${k.cor})"></span>` : ''}
      <p class="kpi__rotulo"></p><div class="kpi__valor"></div>${k.detalhe ? '<div class="kpi__detalhe"></div>' : ''}`;
    d.querySelector('.kpi__rotulo').textContent = k.rotulo;
    d.querySelector('.kpi__valor').textContent = valor;
    if (k.detalhe) d.querySelector('.kpi__detalhe').textContent = k.detalhe;
    return d;
  }));
}

/** Hidrata todos os [data-kpis] / [data-kpis-src] dentro de `raiz`. */
export function hidratarKpis(raiz = document) {
  raiz.querySelectorAll('[data-kpis]').forEach((el) => {
    try { criarKpis(el, JSON.parse(el.dataset.kpis)); } catch (e) { console.error('[kpi]', e); }
  });
  raiz.querySelectorAll('[data-kpis-src]').forEach(async (el) => {
    try { criarKpis(el, linhasDe(await carregarJSON(el.dataset.kpisSrc)) ?? []); } catch (e) { console.error('[kpi]', e); }
  });
}
