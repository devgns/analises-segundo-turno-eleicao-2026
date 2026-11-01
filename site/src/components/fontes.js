/**
 * fontes.js — sistema de notas/referências.
 *
 * 1. Registre a fonte em public/data/fontes.json:
 *      { "fontes": [ { "id": "tse-bu-2t", "tipo": "dado oficial",
 *                      "texto": "TSE. Boletins de urna — 2º turno 2026.",
 *                      "url": "https://dadosabertos.tse.jus.br/…", "acesso": "2026-10-28" } ] }
 * 2. Cite no HTML do capítulo:   …segundo os boletins<sup class="ref" data-ref="tse-bu-2t"></sup>.
 *    (vários: data-ref="tse-bu-2t tse-logs")
 * 3. O capítulo "Fontes e referências" contém <ol class="lista-fontes" data-lista-fontes></ol>.
 *
 * A numeração [n] segue a ordem da primeira citação na página. Fontes registradas e
 * não citadas aparecem no fim da lista (numeração contínua). Cada item tem "↩" de volta
 * para a primeira citação. Uma `data-ref` sem registro aparece como [?] e gera console.warn.
 *
 * @example
 * import { iniciarFontes } from '../components/fontes.js';
 * await iniciarFontes(document, 'data/fontes.json');
 */
import { carregarJSON } from '../lib/dados.js';

const slug = (id) => `fonte-${String(id).replace(/[^a-z0-9_-]/gi, '-')}`;

/**
 * Numera as citações e preenche a lista de fontes.
 * @param {ParentNode} raiz
 * @param {string} [src='data/fontes.json']
 * @returns {Promise<Map<string, number>>} id → número
 */
export async function iniciarFontes(raiz = document, src = 'data/fontes.json') {
  let registro = [];
  try {
    const j = await carregarJSON(src);
    registro = Array.isArray(j) ? j : j.fontes ?? [];
  } catch (e) {
    console.warn('[fontes] não foi possível carregar', src, e);
  }
  const porId = new Map(registro.map((f) => [f.id, f]));
  const numeros = new Map();
  const primeiraCitacao = new Map();
  let n = 0;

  raiz.querySelectorAll('.ref[data-ref]').forEach((sup, idx) => {
    const ids = sup.dataset.ref.split(/[\s,]+/).filter(Boolean);
    sup.replaceChildren();
    ids.forEach((id, j) => {
      if (!porId.has(id)) console.warn(`[fontes] referência sem registro: "${id}"`);
      if (!numeros.has(id)) numeros.set(id, ++n);
      const ancora = `cit-${idx}-${j}`;
      if (!primeiraCitacao.has(id)) primeiraCitacao.set(id, ancora);
      const a = document.createElement('a');
      a.id = ancora;
      a.href = `#${slug(id)}`;
      a.textContent = porId.has(id) ? `[${numeros.get(id)}]` : '[?]';
      a.title = porId.get(id)?.texto ?? `Fonte "${id}" não registrada`;
      if (j) sup.append(' ');
      sup.append(a);
    });
  });

  for (const f of registro) if (!numeros.has(f.id)) numeros.set(f.id, ++n);

  raiz.querySelectorAll('[data-lista-fontes]').forEach((ol) => {
    const itens = [...numeros.entries()]
      .filter(([id]) => porId.has(id))
      .sort((a, b) => a[1] - b[1])
      .map(([id, num]) => {
        const f = porId.get(id);
        const li = document.createElement('li');
        li.id = slug(id);
        li.value = num;
        if (f.tipo) {
          const t = document.createElement('span');
          t.className = 'lista-fontes__tipo';
          t.textContent = f.tipo;
          li.append(t);
        }
        li.append(f.texto ?? id);
        if (f.url) {
          li.append(' ');
          const a = document.createElement('a');
          a.href = f.url;
          a.rel = 'noopener';
          a.target = '_blank';
          a.textContent = 'link';
          li.append(a);
        }
        if (f.acesso) li.append(` (acesso em ${f.acesso.split('-').reverse().join('/')})`);
        if (primeiraCitacao.has(id)) {
          const v = document.createElement('a');
          v.href = `#${primeiraCitacao.get(id)}`;
          v.className = 'lista-fontes__voltar';
          v.setAttribute('aria-label', 'voltar à citação');
          v.textContent = '↩';
          li.append(v);
        }
        return li;
      });
    ol.classList.add('lista-fontes');
    ol.replaceChildren(...itens);
  });
  return numeros;
}
