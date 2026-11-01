/**
 * sumario.js — sumário (TOC) fixo: barra lateral no desktop, recolhível no celular,
 * com destaque da seção atual (scrollspy via IntersectionObserver).
 *
 * @example
 * import { montarSumario } from './components/sumario.js';
 * montarSumario([document.querySelector('#sumario-lateral ol'), document.querySelector('#sumario-movel ol')],
 *   [{ id: 'como-ler', rotulo: 'Como ler', n: '' }, { id: 'conta-nacional', rotulo: 'A conta nacional', n: '1' }]);
 */

/**
 * @param {HTMLOListElement[]} listas listas <ol> a preencher (todas recebem os mesmos itens)
 * @param {{id:string, rotulo:string, n?:string|number}[]} itens
 * @param {HTMLDetailsElement} [movel] o <details> do sumário móvel (fecha ao clicar)
 */
export function montarSumario(listas, itens, movel) {
  for (const ol of listas) {
    ol.replaceChildren(...itens.map((it) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = `#${it.id}`;
      a.dataset.alvo = it.id;
      a.innerHTML = '<span class="sumario__n"></span><span></span>';
      a.firstChild.textContent = it.n ?? '';
      a.lastChild.textContent = it.rotulo;
      li.append(a);
      return li;
    }));
  }
  movel?.addEventListener('click', (e) => { if (e.target.closest('a')) movel.open = false; });

  const links = listas.flatMap((ol) => [...ol.querySelectorAll('a')]);
  const visiveis = new Map();
  const io = new IntersectionObserver((ents) => {
    for (const e of ents) visiveis.set(e.target.id, e.isIntersecting ? e.boundingClientRect.top : null);
    // seção atual = a primeira (na ordem do documento) visível na faixa de leitura
    const atual = itens.find((it) => visiveis.get(it.id) != null)?.id;
    if (!atual) return;
    for (const a of links) a.setAttribute('aria-current', String(a.dataset.alvo === atual));
  }, { rootMargin: '-15% 0px -70% 0px' });
  itens.forEach((it) => { const s = document.getElementById(it.id); if (s) io.observe(s); });
}
