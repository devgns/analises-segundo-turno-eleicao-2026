/**
 * veredito.js — selo de veredito (ícone + rótulo + cor; nunca só cor).
 *
 * Valores aceitos: 'sustentada' | 'parcial' | 'inconclusiva' | 'refutada' | 'nao-testavel' | 'pendente'
 * (também aceita 'não testável' / 'nao testavel').
 *
 * @example
 * import { seloVeredito } from '../components/veredito.js';
 * el.append(seloVeredito('parcial'));
 * // Declarativo: <span class="veredito" data-veredito="refutada"></span> é hidratado por main.js
 */

export const VEREDITOS = {
  sustentada: {
    rotulo: 'Sustentada',
    descricao: 'O padrão ou a limitação apontada existe e não encontramos explicação inocente suficiente. O selo se refere à alegação testada, não à ocorrência de irregularidade.',
    icone: '<path d="M8 1.5 15 14H1z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M8 6v3.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="11.6" r=".9" fill="currentColor"/>',
  },
  parcial: {
    rotulo: 'Parcial',
    descricao: 'Há um sinal que sustenta parte da alegação ou merece investigação, mas os dados não estabelecem sua causa.',
    icone: '<circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 1.8a6.2 6.2 0 0 1 0 12.4z" fill="currentColor"/>',
  },
  inconclusiva: {
    rotulo: 'Inconclusiva',
    descricao: 'Os dados disponíveis não permitem decidir em nenhum sentido.',
    icone: '<circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M5 8h6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
  },
  refutada: {
    rotulo: 'Refutada',
    descricao: 'Os dados contradizem esta afirmação específica, nos testes realizados. Isso não prova que a eleição esteja livre de qualquer irregularidade nem exclui outras formas da hipótese.',
    icone: '<circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="m5 5 6 6m0-6-6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
  },
  'nao-testavel': {
    rotulo: 'Não testável',
    descricao: 'Testar exigiria dados que não são públicos ou que ainda não obtivemos.',
    icone: '<rect x="2" y="7" width="12" height="7.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M5 7V5a3 3 0 0 1 6 0v2" fill="none" stroke="currentColor" stroke-width="1.6"/>',
  },
  pendente: {
    rotulo: 'Em análise',
    descricao: 'Capítulo ainda em produção.',
    icone: '<circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="2 2"/>',
  },
};

/** Normaliza grafias ('não testável' → 'nao-testavel'). */
export function normalizarVeredito(v) {
  const k = String(v ?? 'pendente').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim().replace(/\s+/g, '-');
  return k in VEREDITOS ? k : 'pendente';
}

/**
 * @param {string} v veredito
 * @param {HTMLElement} [el] elemento a reaproveitar (hidratação)
 * @returns {HTMLElement}
 */
export function seloVeredito(v, el = document.createElement('span')) {
  const k = normalizarVeredito(v);
  const info = VEREDITOS[k];
  el.className = `veredito veredito--${k}`;
  el.title = info.descricao;
  el.innerHTML = `<svg viewBox="0 0 16 16" aria-hidden="true">${info.icone}</svg><span>${info.rotulo}</span>`;
  el.setAttribute('aria-label', `Veredito: ${info.rotulo}`);
  return el;
}

/** Hidrata todos os `[data-veredito]` que sejam <span>/<div> vazios. */
export function hidratarVereditos(raiz = document) {
  raiz.querySelectorAll('span[data-veredito], div[data-veredito]').forEach((el) => seloVeredito(el.dataset.veredito, el));
}
