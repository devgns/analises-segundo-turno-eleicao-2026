/**
 * placar.js — "Placar das pistas": grade de cartões com veredito, lida de data/placar.json.
 * placar.json é a FONTE ÚNICA dos vereditos: cada `pistas[i].id` deve ser o id de uma
 * <section class="capitulo">; o selo é aplicado também nos `[data-veredito-capitulo]` do capítulo.
 *
 * Formato:
 *   { "pistas": [ { "id": "conta-nacional", "veredito": "parcial",
 *                   "pista": "frase curta da suspeita", "resumo": "uma frase do resultado" } ] }
 *   Pista avulsa (sem capítulo próprio): acrescente "capitulo": "<id do capítulo que a trata>",
 *   "titulo": "…" e, opcionalmente, "ancora": "<id de um elemento>" para o link.
 *   Para exibir o selo de uma pista avulsa no texto, use [data-veredito-pista="id"].
 *
 * @example
 * import { montarPlacar } from './components/placar.js';
 * await montarPlacar(document.querySelector('#placar-grade'), capitulos);
 */
import { carregarJSON } from '../lib/dados.js';
import { seloVeredito, normalizarVeredito, VEREDITOS } from './veredito.js';

/**
 * @param {HTMLElement} alvo
 * @param {{numero:number, id:string, titulo:string, secao:HTMLElement}[]} capitulos
 * @param {string} [src='data/placar.json']
 * @returns {Promise<Map<string,string>>} id → veredito normalizado
 */
export async function montarPlacar(alvo, capitulos, src = 'data/placar.json') {
  const porId = new Map(capitulos.map((c) => [c.id, c]));
  const vereditos = new Map();
  let pistas = [];
  try {
    pistas = (await carregarJSON(src)).pistas ?? [];
  } catch (e) {
    alvo.innerHTML = `<p class="em-producao">Placar indisponível (${e.message}).</p>`;
    return vereditos;
  }

  const contagem = {};
  const cartoes = pistas.map((pi) => {
    const v = normalizarVeredito(pi.veredito);
    vereditos.set(pi.id, v);
    contagem[v] = (contagem[v] ?? 0) + 1;
    // `capitulo` (opcional): pista avulsa tratada dentro de outro capítulo; não carimba o selo dele.
    const cap = porId.get(pi.capitulo ?? pi.id);
    if (!cap) console.warn(`[placar] id sem capítulo: ${pi.capitulo ?? pi.id}`);
    if (!pi.capitulo) cap?.secao.querySelectorAll('[data-veredito-capitulo]').forEach((el) => seloVeredito(v, el));
    document.querySelectorAll('[data-veredito-pista]').forEach((el) => {
      if (el.dataset.vereditoPista === pi.id) seloVeredito(v, el);
    });

    const a = document.createElement('a');
    a.className = 'placar__item';
    a.href = `#${pi.ancora ?? pi.capitulo ?? pi.id}`;
    a.innerHTML = '<span class="placar__n"></span><span class="placar__titulo"></span><p class="placar__resumo"></p><span></span>';
    a.querySelector('.placar__n').textContent = cap ? `Capítulo ${cap.numero}` : 'Capítulo';
    a.querySelector('.placar__titulo').textContent = pi.titulo ?? cap?.titulo ?? pi.id;
    a.querySelector('.placar__resumo').textContent = pi.pista ?? '';
    if (pi.resumo) {
      const r = document.createElement('p');
      r.className = 'placar__resumo';
      r.innerHTML = '<strong>Resultado:</strong> ';
      r.append(pi.resumo);
      a.querySelector('span:last-child').before(r);
    }
    seloVeredito(v, a.querySelector('span:last-child'));
    return a;
  });

  const resumo = document.createElement('div');
  resumo.className = 'placar__contagem';
  for (const k of Object.keys(VEREDITOS)) {
    if (!contagem[k]) continue;
    const s = seloVeredito(k);
    s.querySelector('span').textContent += ` · ${contagem[k]}`;
    resumo.append(s);
  }
  const grade = document.createElement('div');
  grade.className = 'placar';
  grade.append(...cartoes);
  alvo.replaceChildren(resumo, grade);
  return vereditos;
}
