/**
 * Capítulo 9 — Seções extremas.
 * Dados: public/data/ch09/*.json (gerados por analises/09_extremos.py).
 */
import { num, pct } from '../lib/formato.js';

const ELEICOES = ['2022 · 1º turno', '2022 · 2º turno', '2026 · 1º turno', '2026 · 2º turno'];

/** Observado (●) vs. esperado pelo nulo (barra = intervalo de 90%) — seções com 100% para um candidato. */
function obsEsp(limiar) {
  return (json, p, { largura }) => {
    const d = json.dados.filter((x) => x.limiar === limiar);
    const linhas = [];
    for (const e of ELEICOES) for (const c of ['lula', 'flavio']) {
      const x = d.find((y) => y.eleicao === e && y.candidato === c);
      if (x) linhas.push(x);
    }
    const nome = (x) => `${x.eleicao} · ${x.candidato === 'lula' ? 'Lula' : (x.eleicao.startsWith('2022') ? 'Bolsonaro' : 'Flávio')}`;
    const cor = (x) => (x.candidato === 'lula' ? p.lula : p.flavio);
    return {
      legend: { data: ['Observado', 'Esperado pelo nulo (90%)'] },
      grid: { left: largura < 560 ? 150 : 190, right: 24, top: 36, bottom: 46 },
      tooltip: {
        trigger: 'item',
        formatter: (it) => {
          const x = linhas[it.dataIndex];
          return `<b>${nome(x)}</b><br>Observado: <b>${num(x.observado)}</b> seções<br>`
            + `Esperado: ${num(x.esperado, 1)} (90%: ${num(x.p05)}–${num(x.p95)})<br>`
            + `Razão obs./esp.: ${num(x.observado / x.esperado, 2)}`;
        },
      },
      yAxis: { type: 'category', data: linhas.map(nome), inverse: true, axisLabel: { fontSize: largura < 560 ? 10 : 12 } },
      xAxis: { type: 'value', name: 'Seções com 100%/95% ou mais para o candidato (nº)'.replace(/ ou mais/, limiar === 1 ? '' : ' ou mais').replace('100%/95%', limiar === 1 ? '100%' : '95%'), nameLocation: 'middle', nameGap: 30 },
      series: [
        { name: 'Esperado pelo nulo (90%)', type: 'custom', itemStyle: { color: p.texto3 },
          renderItem: (params, api) => {
            const y = api.coord([0, api.value(0)])[1];
            const a = api.coord([api.value(1), 0])[0];
            const b = api.coord([api.value(2), 0])[0];
            return { type: 'rect', shape: { x: a, y: y - 5, width: Math.max(b - a, 2), height: 10, r: 3 },
              style: { fill: p.texto3, opacity: 0.45 } };
          },
          data: linhas.map((x, i) => [i, x.p05, x.p95]) },
        { name: 'Observado', type: 'scatter', symbolSize: 11, z: 5,
          itemStyle: { color: (it) => cor(linhas[it.dataIndex]), borderColor: p.sup0, borderWidth: 2 },
          data: linhas.map((x, i) => [x.observado, i]) },
      ],
    };
  };
}

export const graficos = {
  'ch09-obs-esp-100': { opcao: obsEsp(1) },
  'ch09-obs-esp-95': { opcao: obsEsp(0.95) },

  /** Distribuição simulada do nº de seções 100% Lula, 2026 2º turno vs. 2022 2º turno, com o observado. */
  'ch09-hist': {
    opcao: (json, p, ctx) => {
      const sel = ['2022 · 2º turno', '2026 · 2º turno'];
      const d = json.dados.filter((x) => x.candidato === 'lula' && sel.includes(x.eleicao));
      const min = Math.min(...d.map((x) => x.contagem)); const max = Math.max(...d.map((x) => x.contagem), 145);
      const xs = Array.from({ length: max - min + 1 }, (_, i) => min + i);
      const obs = ctx.el?.dataset?.obs ? JSON.parse(ctx.el.dataset.obs) : { '2026 · 2º turno': 106, '2022 · 2º turno': 141 };
      const cores = { '2026 · 2º turno': p.lula, '2022 · 2º turno': p.texto3 };
      return {
        legend: { data: sel.map((e) => `nulo ${e}`) },
        grid: { top: 40, left: 20, bottom: 46 },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v, 1) },
        xAxis: { type: 'category', data: xs, name: ctx.largura < 560 ? 'Seções 100% Lula (nº)' : 'Seções com 100% para Lula (nº)', nameLocation: 'middle', nameGap: 30,
          axisLabel: { interval: 9 } },
        yAxis: { type: 'value', name: ctx.largura < 560 ? 'Eleições simuladas (%)' : 'Frequência nas eleições simuladas (%)', nameLocation: 'middle', nameGap: ctx.largura < 560 ? 34 : 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: sel.map((e) => {
          const m = new Map(d.filter((x) => x.eleicao === e).map((x) => [x.contagem, x.freq]));
          return {
            name: `nulo ${e}`, type: 'bar', barGap: '-100%', barCategoryGap: '0%', itemStyle: { color: cores[e], opacity: 0.55 },
            data: xs.map((x) => m.get(x) ?? 0),
            markLine: { silent: true, symbol: 'none', lineStyle: { color: cores[e], width: 2 },
              label: { formatter: `${ctx.largura < 560 ? "obs. " : "observado "}${e.slice(0, 4)}: ${obs[e]}`, color: p.texto1, position: 'end', fontSize: 11 },
              data: [{ xAxis: String(obs[e]) }] },
          };
        }),
      };
    },
  },

  /** Persistência: seções ≥95% no 2º turno, pela fatia do mesmo candidato no 1º turno. */
  'ch09-persistencia': {
    opcao: (json, p, { largura }) => {
      const faixas = Array.from({ length: 20 }, (_, i) => +(i * 0.05).toFixed(2));
      const serie = (c, cor) => {
        const m = new Map(json.dados.filter((x) => x.candidato === c).map((x) => [x.faixa_1t, x.len]));
        return { name: c, type: 'bar', barMaxWidth: 24, itemStyle: { color: cor, borderRadius: [4, 4, 0, 0] }, data: faixas.map((f) => m.get(f) ?? null) };
      };
      return {
        legend: { data: ['Lula', 'Flávio'] },
        grid: { top: 60, left: 20, bottom: 46 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => `${num(v)} seções` },
        xAxis: { type: 'category', data: faixas.map((f) => pct(f, 0)), name: largura < 560 ? 'Fatia do candidato no 1º turno (%)' : 'Fatia do mesmo candidato no 1º turno, entre Lula e Flávio (%)',
          nameLocation: 'middle', nameGap: 30, axisLabel: { interval: largura < 560 ? 3 : 1 } },
        yAxis: { type: 'log', min: 0.5, name: 'Seções (nº, escala log)', nameLocation: 'middle', nameGap: 58, axisLabel: { formatter: (v) => (v < 1 ? '' : num(v)) } },
        series: [serie('Lula', p.lula), serie('Flávio', p.flavio)],
      };
    },
  },

  /** Desvio de cada seção em relação ao seu local (z), 2026 vs 2022. */
  'ch09-did-z': {
    opcao: (json, p, { largura }) => {
      const zs = [...new Set(json.dados.map((x) => x.z))].sort((a, b) => a - b);
      const serie = (e, cor) => {
        const m = new Map(json.dados.filter((x) => x.eleicao === e).map((x) => [x.z, x.secoes]));
        return { name: e === '2026' ? '2026 (1º → 2º turno)' : '2022 (1º → 2º turno)', type: 'line', step: 'middle', symbol: 'none',
          lineStyle: { color: cor, width: 2 }, itemStyle: { color: cor }, data: zs.map((z) => [z, Math.max(m.get(z) ?? 0, 0.5)]) };
      };
      return {
        legend: { data: ['2022 (1º → 2º turno)', '2026 (1º → 2º turno)'] },
        grid: { top: 60, left: 24, bottom: 46 },
        tooltip: { trigger: 'axis', valueFormatter: (v) => (v < 1 ? '0' : `${num(v)} seções`) },
        xAxis: { type: 'value', min: -8, max: 8, name: largura < 560 ? '← pró-Flávio     z     pró-Lula →' : '← mais pró-Flávio que o esperado     z (desvio da seção)     mais pró-Lula que o esperado →',
          nameLocation: 'middle', nameGap: 30, nameTextStyle: { fontSize: 11 } },
        yAxis: { type: 'log', min: 1, name: 'Seções (nº, escala log)', nameLocation: 'middle', nameGap: 62 },
        series: [serie('2022', p.texto3), serie('2026', p.lula)],
      };
    },
  },
};

const fmtCand = (v) => v;

export const tabelas = {
  'ch09-zeros-comparacao': {
    src: 'data/ch09/votos-zerados.json', porPagina: 20, filtro: true,
    legenda: 'Seções sem votos para Flávio no segundo turno de 2026 e seus resultados anteriores',
    colunas: [
      { chave: 'sg_uf', rotulo: 'UF' }, { chave: 'nm_municipio', rotulo: 'Município' },
      { chave: 'zona', rotulo: 'Zona' }, { chave: 'secao', rotulo: 'Seção' },
      { chave: 'flavio_1', rotulo: 'Flávio 2026 · 1º', formato: 'num' },
      { chave: 'flavio_2', rotulo: 'Flávio 2026 · 2º', formato: 'num' },
      { chave: 'lula_2', rotulo: 'Lula 2026 · 2º', formato: 'num' },
      { chave: 'flavio_2022_1', rotulo: 'Jair Bolsonaro 2022 · 1º', formato: 'num' },
      { chave: 'flavio_2022_2', rotulo: 'Jair Bolsonaro 2022 · 2º', formato: 'num' },
      { chave: 'lula_2022_2', rotulo: 'Lula 2022 · 2º', formato: 'num' },
    ],
  },
  'ch09-contagens': {
    src: 'data/ch09/contagens.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'eleicao', rotulo: 'Eleição' },
      { chave: 'candidato', rotulo: 'Candidato', formato: (v) => (v === 'lula' ? 'Lula' : 'Flávio/Bolsonaro') },
      { chave: 'limiar', rotulo: 'Limiar', formato: (v) => `≥ ${pct(v, 0)}` },
      { chave: 'observado', rotulo: 'Observado', formato: 'num' },
      { chave: 'esperado', rotulo: 'Esperado', formato: 'num1' },
      { chave: 'p05', rotulo: 'Nulo p5', formato: 'num' },
      { chave: 'p95', rotulo: 'Nulo p95', formato: 'num' },
      { chave: 'observado', rotulo: 'Obs./esp.', formato: (v, l) => num(v / l.esperado, 2) },
    ],
  },
  'ch09-secoes-100': {
    src: 'data/ch09/secoes-100.json', porPagina: 20, filtro: true,
    ordem: { chave: 'validos_2', direcao: 'desc' },
    colunas: [
      { chave: 'candidato', rotulo: '100% para', formato: fmtCand },
      { chave: 'sg_uf', rotulo: 'UF' },
      { chave: 'nm_municipio', rotulo: 'Município' },
      { chave: 'zona', rotulo: 'Zona' },
      { chave: 'secao', rotulo: 'Seção' },
      { chave: 'validos_2', rotulo: 'Válidos 2º t.', formato: 'num' },
      { chave: 'comparecimento_2', rotulo: 'Comparec.', formato: 'pct1' },
      { chave: 'p1', rotulo: 'Lula no 1º t. (entre os 2)', formato: 'pct1' },
      { chave: 'viz_p2', rotulo: 'Lula no resto do local (2º t.)', formato: 'pct1' },
    ],
  },
  'ch09-peso': {
    src: 'data/ch09/peso-margem.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'candidato', rotulo: 'Extremas para' },
      { chave: 'limiar', rotulo: 'Limiar', formato: (v) => `≥ ${pct(v, 0)}` },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'margem_lula_2t', rotulo: 'Margem de Lula no 2º t.', formato: 'num' },
      { chave: 'ganho_de_margem', rotulo: 'Ganho de margem vs. 1º t.', formato: 'num' },
      { chave: 'fracao_margem_nacional', rotulo: '% da margem nacional', formato: 'pct' },
    ],
  },
  'ch09-did-resumo': {
    src: 'data/ch09/did-resumo.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'eleicao', rotulo: 'Eleição' },
      { chave: 'fdr', rotulo: 'FDR', formato: (v) => pct(v, 0) },
      { chave: 'direcao', rotulo: 'Desvio a favor de', formato: (v, l) => (l.eleicao === '2022' && v === 'Flávio' ? 'Bolsonaro' : v) },
      { chave: 'secoes', rotulo: 'Seções sinalizadas', formato: 'num' },
      { chave: 'secoes_testadas', rotulo: 'Testadas', formato: 'num' },
      { chave: 'excesso_margem', rotulo: 'Efeito na margem de Lula (votos)', formato: 'num' },
    ],
  },
  'ch09-did-top': {
    src: 'data/ch09/did-top.json', porPagina: 25, filtro: true,
    colunas: [
      { chave: 'eleicao', rotulo: 'Eleição' },
      { chave: 'favorece', rotulo: 'Desvio a favor de' },
      { chave: 'sg_uf', rotulo: 'UF' },
      { chave: 'nm_municipio', rotulo: 'Município' },
      { chave: 'zona', rotulo: 'Zona' },
      { chave: 'secao', rotulo: 'Seção' },
      { chave: 'n2', rotulo: 'Válidos 2º t.', formato: 'num' },
      { chave: 'p1', rotulo: 'Lula 1º t. (seção)', formato: 'pct1' },
      { chave: 't1_p', rotulo: 'Lula 1º t. (local)', formato: 'pct1' },
      { chave: 'p2', rotulo: 'Lula 2º t. (seção)', formato: 'pct1' },
      { chave: 't2_p', rotulo: 'Lula 2º t. (local)', formato: 'pct1' },
      { chave: 'p_esperado', rotulo: 'Esperado', formato: 'pct1' },
      { chave: 'excesso_lula', rotulo: 'Votos de Lula acima do esperado', formato: 'num' },
      { chave: 'q', rotulo: 'q (FDR)', formato: (v) => (v < 0.001 ? '< 0,001' : num(v, 3)) },
    ],
  },
};

