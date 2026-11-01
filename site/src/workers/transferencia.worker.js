/**
 * Worker do capítulo 3: Monte Carlo de transferência de votos 1º → 2º turno (2026).
 * Protocolo igual ao de simulacao.worker.js: recebe { id, tarefa, params } e responde
 * { id, ok, resultado } ou { id, ok: false, erro }.
 *
 * Modelo: cada grupo de eleitores do 1º turno (Lula, Flávio, cada eliminado, branco/nulo,
 * abstenção) tem um vetor médio de destinos (Lula, Flávio, fora = branco/nulo/abstenção).
 * Em cada iteração sorteia-se o vetor verdadeiro de cada grupo de uma Dirichlet centrada na
 * média, com concentração `k` (incerteza sobre as taxas; maior k = mais certeza), e somam-se os votos.
 *
 * params = {
 *   grupos: { lula, flavio, cury, renan, caiado, zema, menores, bn, abst },   votos do 1º turno
 *   medias: { <grupo>: [paraLula, paraFlavio, fora] },                       frações (somam 1)
 *   k: 300, iteracoes: 20000, semente: 2026,
 *   oficial: { lula, flavio, share_lula }
 * }
 */

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
function dirichlet(m, k, rng) {
  const g = m.map((mi) => (mi <= 0 ? 0 : gamma(Math.max(mi * k, 1e-3), rng)));
  const s = g.reduce((a, b) => a + b, 0) || 1;
  return g.map((x) => x / s);
}
function quantil(ord, q) {
  const i = (ord.length - 1) * q;
  const lo = Math.floor(i);
  const hi = Math.ceil(i);
  return ord[lo] + (ord[hi] - ord[lo]) * (i - lo);
}

function transferencia03(p, rng) {
  const it = p.iteracoes ?? 20000;
  const k = p.k ?? 300;
  const nomes = Object.keys(p.grupos);
  const shares = new Float64Array(it);
  const lulas = new Float64Array(it);
  const flavios = new Float64Array(it);
  let vitorias = 0;
  let acimaOficial = 0;
  for (let i = 0; i < it; i++) {
    let lula = 0;
    let flavio = 0;
    for (const g of nomes) {
      const v = p.grupos[g];
      const m = p.medias[g];
      const [a, b] = dirichlet(m, k, rng);
      lula += v * a;
      flavio += v * b;
    }
    const s = lula / (lula + flavio);
    shares[i] = s;
    lulas[i] = lula;
    flavios[i] = flavio;
    if (s > 0.5) vitorias++;
    if (s >= p.oficial.share_lula) acimaOficial++;
  }
  // resultado central (sem sorteio)
  let lula0 = 0;
  let flavio0 = 0;
  for (const g of nomes) {
    lula0 += p.grupos[g] * p.medias[g][0];
    flavio0 += p.grupos[g] * p.medias[g][1];
  }
  const ord = Array.from(shares).sort((a, b) => a - b);
  const lo = Math.min(ord[0], p.oficial.share_lula - 0.005);
  const hi = Math.max(ord[ord.length - 1], p.oficial.share_lula + 0.005);
  const bins = 70;
  const w = (hi - lo) / bins || 1;
  const cont = new Array(bins).fill(0);
  for (const v of ord) cont[Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / w)))]++;
  const mediana = (arr) => quantil(Array.from(arr).sort((a, b) => a - b), 0.5);
  return {
    iteracoes: it,
    p05: quantil(ord, 0.05),
    p50: quantil(ord, 0.5),
    p95: quantil(ord, 0.95),
    probLula: vitorias / it,
    probAcimaOficial: acimaOficial / it,
    central: { lula: lula0, flavio: flavio0, share: lula0 / (lula0 + flavio0) },
    medianaVotos: { lula: mediana(lulas), flavio: mediana(flavios) },
    oficial: p.oficial,
    histograma: cont.map((n, j) => ({ x: lo + (j + 0.5) * w, n })),
  };
}

const TAREFAS = { transferencia03 };

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
