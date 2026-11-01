/**
 * Worker do capítulo 5 — "injete uma fraude" sobre os dados REAIS de 2026.
 * Protocolo igual ao de simulacao.worker.js: recebe { id, tarefa, params } e responde
 * { id, ok, resultado } | { id, ok: false, erro }.
 *
 * params = {
 *   urlMun, urlSec,          URLs absolutas de cap05-municipios.json e cap05-secoes.json
 *   tipo: 0..5,              uniforme | proporcional | seções | municípios | urna UE2020 | tardias
 *   k,                       fração dos votos NACIONAIS de Flávio transferida para Lula
 *   frac,                    fração de seções/municípios atingidos (tipos 2 e 3)
 *   reps, semente
 * }
 * Para cada réplica, re-sorteia a divisão Lula/Flávio (ruído binomial) e aplica a manipulação.
 * Detector "dispara" se a estatística sai da faixa [mín, máx] das réplicas sem manipulação
 * (≈ intervalo de 95% com 30 réplicas) — um detector "oráculo", que conhece a versão limpa.
 */

let MUN = null;
let SEC = null;
let PREP = null;

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function normal(rng) {
  let u = 0;
  while (u === 0) u = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
}
/** Binomial: exata para n pequeno, aproximação normal (arredondada e truncada) para n grande. */
function binom(n, p, rng) {
  if (n <= 0 || p <= 0) return 0;
  if (p >= 1) return n;
  if (n < 40) {
    let c = 0;
    for (let i = 0; i < n; i++) if (rng() < p) c++;
    return c;
  }
  const x = Math.round(n * p + Math.sqrt(n * p * (1 - p)) * normal(rng));
  return x < 0 ? 0 : x > n ? n : x;
}
function normSf(z) {
  // cauda superior da normal padrão (Abramowitz–Stegun 7.1.26 via erfc)
  const x = Math.abs(z) / Math.SQRT2;
  const t = 1 / (1 + 0.3275911 * x);
  const y = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))) * Math.exp(-x * x);
  const sf = 0.5 * y;
  return z >= 0 ? sf : 1 - sf;
}
function mediana(a) {
  const s = Float64Array.from(a).sort();
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
function dp(a) {
  let m = 0;
  for (const x of a) m += x;
  m /= a.length;
  let v = 0;
  for (const x of a) v += (x - m) ** 2;
  return Math.sqrt(v / a.length);
}

/* ---------- preparação: regressão congelada (X fixo) ---------- */
function inverter(A) {
  const n = A.length;
  const M = A.map((r, i) => [...r, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  for (let c = 0; c < n; c++) {
    let piv = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
    [M[c], M[piv]] = [M[piv], M[c]];
    const d = M[c][c] || 1e-12;
    for (let j = 0; j < 2 * n; j++) M[c][j] /= d;
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = M[r][c];
      if (f) for (let j = 0; j < 2 * n; j++) M[r][j] -= f * M[c][j];
    }
  }
  return M.map((r) => r.slice(n));
}
function preparar() {
  const X = MUN.X;
  const n = X.length;
  const p = X[0].length;
  const XtX = Array.from({ length: p }, () => new Array(p).fill(0));
  for (const r of X) for (let i = 0; i < p; i++) for (let j = 0; j < p; j++) XtX[i][j] += r[i] * r[j];
  const inv = inverter(XtX);
  // P = (X'X)^-1 X'  (p × n)
  const P = Array.from({ length: p }, () => new Float64Array(n));
  for (let k = 0; k < n; k++) {
    for (let i = 0; i < p; i++) {
      let s = 0;
      for (let j = 0; j < p; j++) s += inv[i][j] * X[k][j];
      P[i][k] = s;
    }
  }
  const c = MUN.colunas;
  const sf1 = Float64Array.from(c.f1, (f, i) => f / Math.max(f + c.l1[i], 1));
  const s = SEC.colunas;
  const ns = s.l1.length;
  const okS = new Uint8Array(ns);
  const sl1 = new Float64Array(ns);
  for (let i = 0; i < ns; i++) {
    okS[i] = s.l1[i] + s.f1[i] >= 100 && s.l2[i] + s.f2[i] >= 100 ? 1 : 0;
    sl1[i] = s.l1[i] / Math.max(s.l1[i] + s.f1[i], 1);
  }
  PREP = { P, p, n, sf1, okS, sl1, ns };
}

/* ---------- detectores ---------- */
function detMunicipal(l2, f2) {
  const { P, p, n, sf1 } = PREP;
  const X = MUN.X;
  const y = new Float64Array(n);
  const nf = new Float64Array(n);
  for (let i = 0; i < n; i++) { nf[i] = Math.max(l2[i] + f2[i], 1); y[i] = f2[i] / nf[i] - sf1[i]; }
  const b = new Float64Array(p);
  for (let j = 0; j < p; j++) { let s = 0; const Pj = P[j]; for (let i = 0; i < n; i++) s += Pj[i] * y[i]; b[j] = s; }
  const r = new Float64Array(n);
  for (let i = 0; i < n; i++) { let s = 0; const xi = X[i]; for (let j = 0; j < p; j++) s += xi[j] * b[j]; r[i] = y[i] - s; }
  // variância a + b/n por mínimos quadrados de r² sobre [1, 1/n]
  let s11 = 0; let s12 = 0; let s22 = 0; let t1 = 0; let t2 = 0;
  for (let i = 0; i < n; i++) { const u = 1 / nf[i]; const r2 = r[i] * r[i]; s11 += 1; s12 += u; s22 += u * u; t1 += r2; t2 += u * r2; }
  const det = s11 * s22 - s12 * s12;
  const a = (t1 * s22 - t2 * s12) / det;
  const bb = (s11 * t2 - s12 * t1) / det;
  const pv = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const v = Math.max(a + bb / nf[i], 1e-8);
    pv[i] = 2 * normSf(Math.abs(r[i]) / Math.sqrt(v));
  }
  const ord = Array.from(pv.keys()).sort((u, v) => pv[u] - pv[v]);
  let nflag = 0;
  for (let i = 0; i < n; i++) if (pv[ord[i]] <= 0.05 * (i + 1) / n) nflag = i + 1;
  return { fdr: nflag, dispRes: dp(r), dispVs22: dp(y) / MUN.sd22, y };
}
function detSecoes(l2, f2) {
  const s = SEC.colunas;
  const { okS, sl1, ns } = PREP;
  const dsh = [];
  const a1 = [];
  const a2 = [];
  let extremos = 0;
  const dig = new Array(10).fill(0);
  for (let i = 0; i < ns; i++) {
    if (s.f1[i] >= 50 && f2[i] <= 0.8 * s.f1[i]) extremos++;
    if (l2[i] >= 10) dig[l2[i] % 10]++;
    if (!okS[i]) continue;
    const sl2 = l2[i] / (l2[i] + f2[i]);
    dsh.push(sl2 - sl1[i]);
    a1.push(1 - sl1[i]);
    a2.push(1 - sl2);
  }
  const med = mediana(dsh);
  const mad = 1.4826 * mediana(dsh.map((x) => Math.abs(x - med)));
  let out = 0;
  for (const x of dsh) if (Math.abs((x - med) / mad) > 4) out++;
  const tot = dig.reduce((u, v) => u + v, 0);
  let chi = 0;
  for (const d of dig) chi += (d - tot / 10) ** 2 / (tot / 10);
  return { outliers: out, ultimoDigito: chi, extremos, forma: ksPadronizado(a1, a2) };
}
function ksPadronizado(a, b) {
  const pad = (v) => { let m = 0; for (const x of v) m += x; m /= v.length; const s = dp(v) || 1; return Float64Array.from(v, (x) => (x - m) / s).sort(); };
  const A = pad(a);
  const B = pad(b);
  let i = 0; let j = 0; let d = 0;
  while (i < A.length && j < B.length) {
    if (A[i] <= B[j]) i++; else j++;
    d = Math.max(d, Math.abs(i / A.length - j / B.length));
  }
  return d;
}

/* ---------- manipulação ---------- */
function municipiosEscolhidos(frac, rng) {
  const n = MUN.colunas.l1.length;
  const e = new Uint8Array(n);
  for (let i = 0; i < n; i++) e[i] = rng() < frac ? 1 : 0;
  return e;
}
/** Taxa por município (para os detectores municipais) — valor esperado da manipulação. */
function taxasMun(tipo, k, frac, escolhidos) {
  const c = MUN.colunas;
  const n = c.l1.length;
  const F = c.f2.reduce((u, v) => u + v, 0);
  const t = new Float64Array(n);
  if (k === 0) return t;
  let peso;
  if (tipo === 0 || tipo === 2) peso = c.f2;                // uniforme; seções sorteadas ≈ uniforme no agregado municipal
  else if (tipo === 1) peso = c.f2q;                         // proporcional à força de Flávio
  else if (tipo === 3) peso = c.f2.map((f, i) => f * escolhidos[i]);
  else if (tipo === 4) peso = c.f2_ue2020;
  else peso = c.f2_tardia;
  const S = peso.reduce((u, v) => u + v, 0) || 1;
  for (let i = 0; i < n; i++) t[i] = Math.min(0.95, (k * F * peso[i] / S) / Math.max(c.f2[i], 1));
  return t;
}
function taxasSec(tipo, k, frac, escolhidos, rng) {
  const s = SEC.colunas;
  const n = s.l1.length;
  const t = new Float64Array(n);
  if (k === 0) return t;
  let F = 0;
  let S = 0;
  const w = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const sf = s.f2[i] / Math.max(s.l2[i] + s.f2[i], 1);
    w[i] = tipo === 0 ? 1 : tipo === 1 ? sf : tipo === 2 ? (rng() < frac ? 1 : 0) : tipo === 3 ? escolhidos[s.mun[i]] : tipo === 4 ? s.ue2020[i] : s.tardia[i];
    F += s.f2[i];
    S += w[i] * s.f2[i];
  }
  for (let i = 0; i < n; i++) t[i] = S > 0 ? Math.min(0.95, w[i] * k * F / S) : 0;
  return t;
}

function replica(l2, f2, taxa, rng) {
  const n = l2.length;
  const L = new Int32Array(n);
  const F = new Int32Array(n);
  for (let i = 0; i < n; i++) {
    const tot = l2[i] + f2[i];
    let f = binom(tot, f2[i] / Math.max(tot, 1), rng);
    const mv = taxa ? binom(f, taxa[i], rng) : 0;
    f -= mv;
    F[i] = f;
    L[i] = tot - f;
  }
  return [L, F];
}

const DET = [
  ['fdr', 'Municípios sinalizados por FDR (regressão congelada no 1º turno)', 'mun'],
  ['dispRes', 'Dispersão do resíduo municipal', 'mun'],
  ['dispVs22', 'Dispersão municipal comparada com 2022', 'mun'],
  ['outliers', 'Seções outliers (|z| robusto > 4)', 'sec'],
  ['extremos', 'Seções em que Flávio perde ≥ 20%', 'sec'],
  ['ultimoDigito', 'Último dígito (χ²)', 'sec'],
  ['forma', 'Forma da distribuição 1º × 2º turno (KS)', 'sec'],
];

async function fraude(p, rng) {
  if (!MUN) {
    const [m, s] = await Promise.all([fetch(p.urlMun).then((r) => r.json()), fetch(p.urlSec).then((r) => r.json())]);
    MUN = m; SEC = s;
    preparar();
  }
  const reps = p.reps ?? 30;
  const c = MUN.colunas;
  const s = SEC.colunas;
  const nulo = {};
  const alt = {};
  for (const [id] of DET) { nulo[id] = []; alt[id] = []; }
  let yReal = null;
  let yMan = null;
  let movidos = 0;
  for (let r = 0; r < reps; r++) {
    const esc = municipiosEscolhidos(p.frac, rng);
    const tm = taxasMun(p.tipo, p.k, p.frac, esc);
    const ts = taxasSec(p.tipo, p.k, p.frac, esc, rng);
    // sem manipulação
    const [L0, F0] = replica(c.l2, c.f2, null, rng);
    const [l0, f0] = replica(s.l2, s.f2, null, rng);
    const dm0 = detMunicipal(L0, F0);
    const ds0 = detSecoes(l0, f0);
    // com manipulação
    const [L1, F1] = replica(c.l2, c.f2, tm, rng);
    const [l1, f1] = replica(s.l2, s.f2, ts, rng);
    const dm1 = detMunicipal(L1, F1);
    const ds1 = detSecoes(l1, f1);
    for (const [id, , nivel] of DET) {
      nulo[id].push((nivel === 'mun' ? dm0 : ds0)[id]);
      alt[id].push((nivel === 'mun' ? dm1 : ds1)[id]);
    }
    if (r === 0) {
      yReal = dm0.y; yMan = dm1.y;
      for (let i = 0; i < c.f2.length; i++) movidos += F0[i] - F1[i];
    }
  }
  const detectores = DET.map(([id, nome]) => {
    const lo = Math.min(...nulo[id]);
    const hi = Math.max(...nulo[id]);
    const disparos = alt[id].filter((x) => x < lo || x > hi).length;
    return { id, nome, nulo_lo: lo, nulo_hi: hi, media_nulo: nulo[id].reduce((u, v) => u + v, 0) / reps,
      media_manip: alt[id].reduce((u, v) => u + v, 0) / reps, poder: disparos / reps };
  });
  // histogramas da oscilação municipal
  const bins = 60; const lo = -0.12; const hi = 0.06; const w = (hi - lo) / bins;
  const hist = (y) => { const h = new Array(bins).fill(0); for (const v of y) h[Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / w)))]++; return h; };
  const L = c.l2.reduce((u, v) => u + v, 0);
  const F = c.f2.reduce((u, v) => u + v, 0);
  const mov = p.k * F;
  return {
    x: Array.from({ length: bins }, (_, i) => lo + (i + 0.5) * w),
    histReal: hist(yReal), histMan: hist(yMan),
    mediaReal: yReal.reduce((u, v) => u + v, 0) / yReal.length,
    mediaMan: yMan.reduce((u, v) => u + v, 0) / yMan.length,
    sdReal: dp(yReal), sdMan: dp(yMan),
    lulaReal: L / (L + F), lulaManip: (L + mov) / (L + F), votosMovidos: mov,
    detectores, reps,
  };
}

const TAREFAS = { fraude };

self.onmessage = async (ev) => {
  const { id, tarefa, params } = ev.data;
  try {
    const fn = TAREFAS[tarefa];
    if (!fn) throw new Error(`tarefa desconhecida: ${tarefa}`);
    const t0 = performance.now();
    const resultado = await fn(params, mulberry32(params?.semente ?? 1));
    resultado.ms = Math.round(performance.now() - t0);
    self.postMessage({ id, ok: true, resultado });
  } catch (e) {
    self.postMessage({ id, ok: false, erro: String(e?.message ?? e) });
  }
};
