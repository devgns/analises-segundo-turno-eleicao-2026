/**
 * Formatação pt-BR de números, percentuais e pontos percentuais.
 * Todas as funções aceitam null/undefined/NaN e devolvem '—'.
 *
 * @example
 * import { num, pct, prob, pp, compacto, votos } from '../lib/formato.js';
 * num(10412345)          // '10.412.345'
 * num(3.14159, 2)        // '3,14'
 * pct(0.5179)            // '51,79%'   (fração por padrão)
 * pct(51.79, 2, { escala: 100 }) // '51,79%' (valor já em %)
 * pp(0.0123)             // '+1,23 p.p.' (fração → p.p.)
 * pp(-2.5, 1, { escala: 100 })  // '−2,5 p.p.'
 * compacto(10412345)     // '10,4 mi'
 * votos(10412345)        // '10.412.345 votos'
 */

const VAZIO = '—';
const MENOS = '−'; // sinal de menos tipográfico
const cache = new Map();

function nf(min, max, extra = {}) {
  const k = `${min}|${max}|${JSON.stringify(extra)}`;
  if (!cache.has(k)) {
    cache.set(k, new Intl.NumberFormat('pt-BR', { minimumFractionDigits: min, maximumFractionDigits: max, ...extra }));
  }
  return cache.get(k);
}

const invalido = (x) => x === null || x === undefined || x === '' || Number.isNaN(Number(x));
const comMenos = (s) => s.replace(/^-/, MENOS);

/** Número com separador de milhar. @param {number} x @param {number} [casas=0] @returns {string} */
export function num(x, casas = 0) {
  if (invalido(x)) return VAZIO;
  return comMenos(nf(casas, casas).format(Number(x)));
}

/**
 * Percentual. Por padrão `x` é fração (0,5179 → 51,79%).
 * @param {number} x
 * @param {number} [casas=2]
 * @param {{escala?: 1|100, sinal?: boolean}} [op] escala 100 se `x` já está em %
 */
export function pct(x, casas = 2, op = {}) {
  if (invalido(x)) return VAZIO;
  const v = Number(x) * (op.escala === 100 ? 1 : 100);
  const s = nf(casas, casas).format(v);
  const pre = op.sinal && v > 0 ? '+' : '';
  return comMenos(pre + s) + '%';
}

const SOBRESCRITO = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '-': '⁻' };

/**
 * Probabilidade (fração). Igual a `pct` a partir de 0,01%; abaixo disso, notação científica, para que eventos
 * raríssimos não apareçam como "0,00%".
 * @example prob(0.0618) // '6,18%' · prob(5.48e-16) // '5,5 × 10⁻¹⁶'
 * @param {number} x
 * @param {number} [casas=2]
 */
export function prob(x, casas = 2) {
  if (invalido(x)) return VAZIO;
  const v = Number(x);
  if (v === 0 || v >= 1e-4) return pct(v, casas);
  const [m, e] = v.toExponential(1).split('e');
  const exp = String(Number(e)).replace(/./g, (c) => SOBRESCRITO[c]);
  return `${m.replace('.', ',')} × 10${exp}`;
}

/**
 * Diferença em pontos percentuais, sempre com sinal. `x` é fração por padrão.
 * @param {number} x
 * @param {number} [casas=2]
 * @param {{escala?: 1|100}} [op]
 */
export function pp(x, casas = 2, op = {}) {
  if (invalido(x)) return VAZIO;
  const v = Number(x) * (op.escala === 100 ? 1 : 100);
  const s = nf(casas, casas).format(v);
  return comMenos((v > 0 ? '+' : '') + s) + ' p.p.';
}

/** Forma compacta: 1,2 mil · 10,4 mi · 1,1 bi. @param {number} x @param {number} [casas=1] */
export function compacto(x, casas = 1) {
  if (invalido(x)) return VAZIO;
  const v = Number(x);
  const a = Math.abs(v);
  const f = (d, suf) => comMenos(nf(0, casas).format(v / d)) + ' ' + suf;
  if (a >= 1e9) return f(1e9, 'bi');
  if (a >= 1e6) return f(1e6, 'mi');
  if (a >= 1e4) return f(1e3, 'mil');
  return num(v);
}

/** "10.412.345 votos" (singular para 1). */
export function votos(x) {
  if (invalido(x)) return VAZIO;
  return `${num(x)} ${Math.abs(Number(x)) === 1 ? 'voto' : 'votos'}`;
}

/** Valor-p legível: 'p < 0,001' ou 'p = 0,034'. */
export function valorP(p) {
  if (invalido(p)) return VAZIO;
  return p < 0.001 ? 'p < 0,001' : `p = ${nf(3, 3).format(p)}`;
}

/** Data ISO → '25/10/2026' (ou com hora se `comHora`). */
export function data(iso, comHora = false) {
  if (!iso) return VAZIO;
  const so = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso); // data pura: não converter fuso
  if (so) return `${so[3]}/${so[2]}/${so[1]}`;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString('pt-BR', comHora
    ? { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' }
    : { dateStyle: 'short', timeZone: 'America/Sao_Paulo' });
}

/**
 * Resolve um formatador por nome — usado por tabela/kpi/gráficos via atributos HTML.
 * Nomes: 'num', 'num1', 'num2', 'pct', 'pct1', 'pct100' (valor já em %), 'pp', 'pp1', 'compacto', 'votos', 'valorP', 'data', 'texto'.
 * @param {string|Function} nome
 * @returns {(x:any)=>string}
 */
export function formatador(nome) {
  if (typeof nome === 'function') return nome;
  switch (nome) {
    case 'num': return (x) => num(x);
    case 'num1': return (x) => num(x, 1);
    case 'num2': return (x) => num(x, 2);
    case 'pct': return (x) => pct(x, 2);
    case 'pct1': return (x) => pct(x, 1);
    case 'pct100': return (x) => pct(x, 2, { escala: 100 });
    case 'pp': return (x) => pp(x, 2);
    case 'pp1': return (x) => pp(x, 1);
    case 'compacto': return (x) => compacto(x);
    case 'votos': return votos;
    case 'valorP': return valorP;
    case 'data': return (x) => data(x);
    default: return (x) => (x === null || x === undefined ? VAZIO : String(x));
  }
}
