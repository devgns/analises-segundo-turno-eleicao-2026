/**
 * Carregamento de dados (JSON em public/data/) e exportação CSV.
 *
 * Convenção de arquivo (recomendada, não obrigatória):
 *   { "meta": { "titulo", "fonte", "descricao", "gerado_em", "demo": bool, "script": "scripts/…" },
 *     "dados": [ { ...linha plana... }, ... ] }
 *
 * @example
 * const j = await carregarJSON('data/demo.json');
 * const csv = paraCSV(j.dados);
 */

/** Repositório público com o código que gera cada arquivo de dados. */
export const REPOSITORIO = 'https://github.com/devgns/analises-segundo-turno-eleicao-2026';

/** Link para um arquivo do repositório no GitHub (ex.: 'analises/01_conta_nacional.py'). */
export function urlRepositorio(caminho) {
  return `${REPOSITORIO}/blob/main/${caminho}`;
}

const cache = new Map();

/** Resolve caminho relativo ao documento (funciona sob qualquer subcaminho do GitHub Pages). */
export function urlDados(caminho) {
  return new URL(caminho, document.baseURI).href;
}

/**
 * Busca JSON com cache em memória (a mesma URL é baixada uma vez).
 * @param {string} caminho ex.: 'data/demo.json'
 * @returns {Promise<any>}
 */
export function carregarJSON(caminho) {
  const url = urlDados(caminho);
  if (!cache.has(url)) {
    const p = fetch(url).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status} ao buscar ${caminho}`);
      return r.json();
    });
    p.catch(() => cache.delete(url));
    cache.set(url, p);
  }
  return cache.get(url);
}

/** Extrai as linhas tabulares de um JSON no formato da convenção (ou um array cru). */
export function linhasDe(json) {
  if (Array.isArray(json)) return json;
  if (json && Array.isArray(json.dados)) return json.dados;
  return null;
}

/**
 * Converte array de objetos planos em CSV (separador ',' e ponto decimal —
 * formato de máquina, para reprodutibilidade; abre em R/Python/planilhas).
 * @param {object[]} linhas
 * @returns {string}
 */
export function paraCSV(linhas) {
  if (!linhas?.length) return '';
  const cols = [...new Set(linhas.flatMap((l) => Object.keys(l)))];
  const esc = (v) => {
    if (v === null || v === undefined) return '';
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.join(','), ...linhas.map((l) => cols.map((c) => esc(l[c])).join(','))].join('\n');
}

/** Dispara download de um texto como arquivo. */
export function baixarTexto(texto, nome, tipo = 'text/csv;charset=utf-8') {
  const blob = new Blob([texto], { type: tipo });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = nome;
  document.body.append(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
}
