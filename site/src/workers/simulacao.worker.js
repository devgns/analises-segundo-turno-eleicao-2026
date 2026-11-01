/**
 * Web Worker genérico de simulação. Recebe { id, tarefa, params } e responde
 * { id, ok: true, resultado } ou { id, ok: false, erro }.
 *
 * Para adicionar uma tarefa: escreva `function minhaTarefa(params, rng)` que devolva
 * um objeto serializável e registre em TAREFAS. Use sempre `rng()` (semente fixa →
 * resultados reprodutíveis), nunca Math.random().
 *
 * Tarefas atuais (DEMONSTRAÇÃO — modelos simplificados; os capítulos devem substituir
 * os parâmetros por valores estimados dos dados reais):
 *  - 'transferencia': Monte Carlo de transferência de votos do 1º para o 2º turno.
 *  - 'fraude':        poder de detecção de um teste de outliers contra fraude
 *                     localizada × fraude uniforme ("mover a média").
 */

/* ---------- RNG reprodutível ---------- */
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
/** Gamma(k, 1) — Marsaglia & Tsang. */
function gamma(k, rng) {
  if (k < 1) return gamma(k + 1, rng) * rng() ** (1 / k);
  const d = k - 1 / 3;
  const c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x;
    let v;
    do { x = normal(rng); v = 1 + c * x; } while (v <= 0);
    v = v * v * v;
    const u = rng();
    if (u < 1 - 0.0331 * x ** 4 || Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
  }
}
/** Dirichlet com média `m` (soma 1) e concentração `k`. */
function dirichlet(m, k, rng) {
  const g = m.map((mi) => gamma(Math.max(mi * k, 1e-3), rng));
  const s = g.reduce((a, b) => a + b, 0);
  return g.map((x) => x / s);
}
function quantil(ordenado, q) {
  const i = (ordenado.length - 1) * q;
  const lo = Math.floor(i);
  const hi = Math.ceil(i);
  return ordenado[lo] + (ordenado[hi] - ordenado[lo]) * (i - lo);
}
function histograma(valores, bins, min, max) {
  const lo = min ?? Math.min(...valores);
  const hi = max ?? Math.max(...valores);
  const w = (hi - lo) / bins || 1;
  const cont = new Array(bins).fill(0);
  for (const v of valores) cont[Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / w)))]++;
  return cont.map((n, i) => ({ x: lo + (i + 0.5) * w, n }));
}

/* ---------- (a) transferência de votos ---------- */
/**
 * params = {
 *   base: { lula, flavio },                      votos que já tinham no 1º turno
 *   grupos: [{ nome, votos, paraLula, paraFlavio }],  frações médias (resto = branco/nulo/abstenção)
 *   concentracao: 50,                            incerteza (maior = menos incerto)
 *   retencao: 0.98,                              fração da própria base que volta a votar igual
 *   iteracoes: 20000, semente: 1
 * }
 */
function transferencia(p, rng) {
  const it = p.iteracoes ?? 20000;
  const k = p.concentracao ?? 50;
  const ret = p.retencao ?? 1;
  const shares = new Float64Array(it);
  let vitorias = 0;
  for (let i = 0; i < it; i++) {
    let lula = p.base.lula * ret;
    let flavio = p.base.flavio * ret;
    for (const g of p.grupos) {
      const resto = Math.max(0, 1 - g.paraLula - g.paraFlavio);
      const [a, b] = dirichlet([g.paraLula, g.paraFlavio, resto], k, rng);
      lula += g.votos * a;
      flavio += g.votos * b;
    }
    const s = lula / (lula + flavio);
    shares[i] = s;
    if (s > 0.5) vitorias++;
  }
  const ord = Array.from(shares).sort((a, b) => a - b);
  return {
    iteracoes: it,
    p05: quantil(ord, 0.05),
    p50: quantil(ord, 0.5),
    p95: quantil(ord, 0.95),
    probLula: vitorias / it,
    histograma: histograma(ord, 60, ord[0], ord[ord.length - 1]),
  };
}

/* ---------- (b) "injete uma fraude": poder do detector ---------- */
/**
 * Modelo: N unidades (municípios) com deslocamento natural entre turnos ~ Normal(mu, sigma).
 * Fraude: soma `delta` ao deslocamento de uma fração `frac` das unidades (frac = 1 → uniforme).
 * Detector: z robusto (mediana/MAD) e conta |z| > 3; alarme se a contagem excede o
 * esperado sob H0 (calibrado por simulação sem fraude, 99º percentil).
 *
 * params = { n: 5570, mu: 0.03, sigma: 0.025, delta: 0.01, frac: 0.05, reps: 300, semente: 1 }
 */
function detectar(desl) {
  const ord = Float64Array.from(desl).sort();
  const med = quantil(ord, 0.5);
  const dev = Float64Array.from(desl, (x) => Math.abs(x - med)).sort();
  const mad = quantil(dev, 0.5) * 1.4826 || 1e-9;
  let c = 0;
  for (const x of desl) if (Math.abs((x - med) / mad) > 3) c++;
  return { contagem: c, mediana: med };
}
function amostra(p, rng, comFraude) {
  const d = new Float64Array(p.n);
  const corte = comFraude ? p.frac : 0;
  for (let i = 0; i < p.n; i++) {
    d[i] = p.mu + p.sigma * normal(rng) + (rng() < corte ? p.delta : 0);
  }
  return d;
}
function fraude(p, rng) {
  const reps = p.reps ?? 300;
  const nulas = [];
  for (let r = 0; r < reps; r++) nulas.push(detectar(amostra(p, rng, false)).contagem);
  nulas.sort((a, b) => a - b);
  const limiar = quantil(nulas, 0.99);
  let alarmes = 0;
  for (let r = 0; r < reps; r++) if (detectar(amostra(p, rng, true)).contagem > limiar) alarmes++;
  const exSem = Array.from(amostra(p, rng, false));
  const exCom = Array.from(amostra(p, rng, true));
  const lo = Math.min(...exSem, ...exCom);
  const hi = Math.max(...exSem, ...exCom);
  return {
    poder: alarmes / reps,
    limiar,
    reps,
    votosDeslocados: p.delta * p.frac, // deslocamento médio total introduzido (fração do eleitorado)
    histSem: histograma(exSem, 50, lo, hi),
    histCom: histograma(exCom, 50, lo, hi),
  };
}

const TAREFAS = { transferencia, fraude };

self.onmessage = (ev) => {
  const { id, tarefa, params } = ev.data;
  try {
    const fn = TAREFAS[tarefa];
    if (!fn) throw new Error(`tarefa desconhecida: ${tarefa}`);
    const t0 = performance.now();
    const resultado = fn(params, mulberry32(params?.semente ?? 1));
    resultado.ms = Math.round(performance.now() - t0);
    self.postMessage({ id, ok: true, resultado });
  } catch (e) {
    self.postMessage({ id, ok: false, erro: String(e?.message ?? e) });
  }
};
