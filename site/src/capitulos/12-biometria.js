/**
 * Capítulo 7 — Biometria: eleitores habilitados sem digital.
 * Dados: public/data/ch07/*.json (gerados por analises/07_biometria.py).
 */
import { pct, pp, num } from '../lib/formato.js';

const rotHora = (estreito) => (estreito ? 11 : 5);

export const graficos = {
  /** Taxa por UF, 1º vs 2º turno (barras horizontais). */
  'ch07-uf': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.filter((x) => x.sg_uf !== 'ZZ').slice().sort((a, b) => a.taxa_2 - b.taxa_2);
      return {
        legend: { data: ['1º turno', '2º turno'] },
        grid: { left: 36, right: 16, top: 36, bottom: 46 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => pct(v) },
        yAxis: { type: 'category', data: d.map((x) => x.sg_uf), axisLabel: { fontSize: largura < 560 ? 10 : 12 } },
        xAxis: { type: 'value', name: largura < 560 ? 'Habilitados sem digital (%)' : 'Habilitados sem biometria (% do comparecimento)', nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [
          { name: '1º turno', type: 'bar', barMaxWidth: 10, itemStyle: { color: p.sequencial[2], borderRadius: [0, 4, 4, 0] },
            data: d.map((x) => x.taxa_1) },
          { name: '2º turno', type: 'bar', barMaxWidth: 10, itemStyle: { color: p.sequencial[4], borderRadius: [0, 4, 4, 0] },
            data: d.map((x) => x.taxa_2) },
        ],
      };
    },
  },

  /** Binscatter: nível bruto. */
  'ch07-bin-nivel': {
    opcao: (json, p) => binsc(json, p, 'bruto', 'Taxa sem biometria, 2º turno (%)', 'Fatia de Lula, 2º turno (%)', false),
  },
  /** Binscatter: variação dentro do município. */
  'ch07-bin-delta': {
    opcao: (json, p) => binsc(json, p, 'delta', 'Δ taxa sem biometria (p.p.)', 'Δ fatia de Lula (p.p.)', true),
  },

  /** Coeficientes das regressões (efeito de +10 p.p. na taxa). */
  'ch07-coef': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.slice().reverse();
      const k = 0.1;
      const curto = (s) => (largura < 560 ? s.replace(/\s*\(.*\)/, '').slice(0, 28) : s);
      return {
        grid: { left: 8, right: 24, top: 16, bottom: 46 },
        tooltip: {
          trigger: 'item',
          formatter: (it) => {
            const x = d[it.dataIndex];
            return `${x.modelo}<br>Efeito de +10 p.p. na taxa: <b>${pp(x.coef * k)}</b><br>IC 95%: ${pp(x.ic_inf * k)} a ${pp(x.ic_sup * k)}<br>n = ${num(x.n)}`;
          },
        },
        yAxis: { type: 'category', data: d.map((x) => curto(x.modelo)), axisLabel: { fontSize: 11, width: largura < 560 ? 140 : 320, overflow: 'truncate' } },
        xAxis: { type: 'value', axisLabel: { formatter: (v) => pp(v, 1) }, name: largura < 560 ? 'Efeito na fatia de Lula (p.p.)' : 'Efeito na fatia de Lula de +10 p.p. na taxa sem biometria (p.p.)',
          nameLocation: 'middle', nameGap: 30 },
        series: [
          { type: 'custom', encode: { x: [1, 2], y: 0 }, renderItem: (params, api) => {
            const y = api.coord([0, api.value(0)])[1];
            const a = api.coord([api.value(1), 0])[0];
            const b = api.coord([api.value(2), 0])[0];
            return { type: 'line', shape: { x1: a, y1: y, x2: b, y2: y }, style: { stroke: p.texto2, lineWidth: 2 } };
          }, data: d.map((x, i) => [i, x.ic_inf * k, x.ic_sup * k]), z: 1 },
          { type: 'scatter', symbolSize: 10, itemStyle: { color: p.texto1 }, data: d.map((x, i) => [x.coef * k, i]), z: 2,
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, data: [{ xAxis: 0 }], label: { show: false } } },
        ],
      };
    },
  },

  /** Fração sem digital por faixa de 10 min. */
  'ch07-hora': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      return {
        legend: { data: ['Todos sem digital', 'Após tentativa de digital (≈ bweb)'] },
        grid: { left: 20, bottom: 46 },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v) },
        xAxis: { type: 'category', data: d.map((x) => x.faixa), name: largura < 560 ? 'Horário do voto (Brasília)' : 'Horário do voto, faixas de 10 min (Brasília)', nameLocation: 'middle', nameGap: 30, axisLabel: { interval: rotHora(largura < 560) } },
        yAxis: { type: 'value', name: largura < 560 ? 'Sem digital (%)' : 'Votos habilitados sem digital (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) }, min: 0 },
        series: [
          { name: 'Todos sem digital', type: 'line', symbol: 'none', lineStyle: { width: 2, color: p.sequencial[4] },
            itemStyle: { color: p.sequencial[4] }, data: d.map((x) => x.frac_sem_digital) },
          { name: 'Após tentativa de digital (≈ bweb)', type: 'line', symbol: 'none', lineStyle: { width: 2, color: p.texto3 },
            itemStyle: { color: p.texto3 }, data: d.map((x) => x.frac_nt) },
        ],
      };
    },
  },

  /** Tempo de cabine: distribuição. */
  'ch07-cabine': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      return {
        legend: { data: ['Habilitado por biometria', 'Habilitado sem digital'] },
        grid: { left: 20, bottom: 46 },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v, 2) },
        xAxis: { type: 'category', data: d.map((x) => x.seg), name: largura < 560 ? 'Segundos até o voto' : 'Segundos entre a habilitação e o voto computado', nameLocation: 'middle', nameGap: 30, axisLabel: { interval: 9 } },
        yAxis: { type: 'value', name: largura < 560 ? 'Votos (%)' : 'Participação dos votos do grupo (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [
          { name: 'Habilitado por biometria', type: 'line', symbol: 'none', lineStyle: { width: 2, color: p.sequencial[2] },
            itemStyle: { color: p.sequencial[2] }, areaStyle: { color: p.sequencial[2], opacity: 0.1 }, data: d.map((x) => x.biometria) },
          { name: 'Habilitado sem digital', type: 'line', symbol: 'none', lineStyle: { width: 2, color: p.sequencial[4] },
            itemStyle: { color: p.sequencial[4] }, data: d.map((x) => x.sem_digital) },
        ],
      };
    },
  },

  /** Calibração dos p-valores. */
  'ch07-calib': {
    opcao: (json, p) => {
      const d = json.dados;
      const cat = d.map((x) => `p ≤ ${String(x.limiar).replace('.', ',')}`);
      const s = (nome, chave, cor) => ({ name: nome, type: 'bar', barMaxWidth: 24, itemStyle: { color: cor, borderRadius: [4, 4, 0, 0] },
        data: d.map((x) => x[chave] / x.limiar) });
      return {
        legend: { data: ['Maior rajada', 'Última meia hora', 'Após ociosidade'] },
        tooltip: { trigger: 'axis', valueFormatter: (v) => `${num(v, 2)} × o esperado` },
        grid: { left: 20, bottom: 46 },
        xAxis: { type: 'category', data: cat, name: 'Limiar de p-valor', nameLocation: 'middle', nameGap: 30 },
        yAxis: { type: 'value', name: 'Observado ÷ esperado (×)', nameLocation: 'middle', nameGap: 36 },
        series: [
          s('Maior rajada', 'rajada', p.sequencial[4]), s('Última meia hora', 'final', p.sequencial[3]), s('Após ociosidade', 'apos_ocio', p.sequencial[2]),
          { type: 'line', silent: true, data: [], markLine: { symbol: 'none', silent: true, lineStyle: { color: p.texto3, type: 'dashed' },
            label: { formatter: 'nulo', color: p.texto2 }, data: [{ yAxis: 1 }] } },
        ],
      };
    },
  },

  /** Δ Lula: sinalizadas vs demais. */
  'ch07-sinal-delta': {
    opcao: (json, p, { largura }) => {
      const nomes = { rajada: 'Maior rajada', ultima_meia_hora: 'Última meia hora', apos_ociosidade: 'Após ociosidade', qualquer: 'Qualquer um' };
      const d = json.dados.filter((x) => x.diferenca !== undefined && x.diferenca !== null);
      return {
        grid: { left: 130, right: 24, top: 16, bottom: 46 },
        tooltip: { trigger: 'item', formatter: (it) => {
          const x = d[it.dataIndex];
          return `${nomes[x.teste]} (${num(x.secoes)} seções)<br>Diferença no Δ de Lula: <b>${pp(x.diferenca)}</b><br>IC 95%: ${pp(x.ic_inf)} a ${pp(x.ic_sup)}<br>`
            + `Na cauda de Lula: ${pct(x.cauda_lula, 1)} · na de Flávio: ${pct(x.cauda_flavio, 1)} (esperado 10% cada)`;
        } },
        yAxis: { type: 'category', data: d.map((x) => `${nomes[x.teste]} (${num(x.secoes)})`) },
        xAxis: { type: 'value', axisLabel: { formatter: (v) => pp(v, 1) }, name: largura < 560 ? 'Δ fatia de Lula (p.p.)' : 'Δ fatia de Lula: sinalizadas − demais, mesmo município (p.p.)',
          nameLocation: 'middle', nameGap: 30 },
        series: [
          { type: 'custom', encode: { x: [1, 2], y: 0 }, renderItem: (params, api) => {
            const y = api.coord([0, api.value(0)])[1];
            const a = api.coord([api.value(1), 0])[0];
            const b = api.coord([api.value(2), 0])[0];
            return { type: 'line', shape: { x1: a, y1: y, x2: b, y2: y }, style: { stroke: p.texto2, lineWidth: 2 } };
          }, data: d.map((x, i) => [i, x.ic_inf, x.ic_sup]) },
          { type: 'scatter', symbolSize: 10, itemStyle: { color: p.texto1 }, data: d.map((x, i) => [x.diferenca, i]),
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, data: [{ xAxis: 0 }], label: { show: false } } },
        ],
      };
    },
  },
};

function binsc(json, p, painel, nx, ny, centrado) {
  const d = json.dados.filter((x) => x.painel === painel);
  const fx = centrado ? (v) => pp(v, 1) : (v) => pct(v, 0);
  const fy = centrado ? (v) => pp(v, 2) : (v) => pct(v, 0);
  return {
    grid: { left: 28, right: 16, top: 32, bottom: 52 },
    tooltip: { trigger: 'item', formatter: (it) => `${nx}: ${fx(it.value[0])}<br>${ny}: <b>${fy(it.value[1])}</b><br>${num(it.value[2])} seções` },
    xAxis: { type: 'value', scale: true, name: nx, nameLocation: 'middle', nameGap: 32,
      axisLabel: { formatter: fx } },
    yAxis: { type: 'value', scale: true, name: ny, nameLocation: 'middle', nameGap: centrado ? 78 : 52, axisLabel: { formatter: fy } },
    series: [{ type: 'line', symbolSize: 9, lineStyle: { width: 2, color: p.sequencial[4] }, itemStyle: { color: p.sequencial[4] },
      data: d.map((x) => [x.x, x.y, x.n]) }],
  };
}

export const tabelas = {
  'ch07-tab-sinalizadas': {
    src: 'data/ch07/sinalizadas.json', porPagina: 25, filtro: true, ordem: { chave: 'q_min', direcao: 'asc' },
    legenda: 'Seções com rajada ou concentração de habilitações sem digital',
    colunas: [
      { chave: 'uf', rotulo: 'UF' }, { chave: 'municipio', rotulo: 'Município' }, { chave: 'zona', rotulo: 'Zona' },
      { chave: 'secao', rotulo: 'Seção' }, { chave: 'votos_log', rotulo: 'Votos', formato: 'num' },
      { chave: 'sem_digital', rotulo: 'Sem digital', formato: 'num' }, { chave: 'frac_sd', rotulo: '% sem digital', formato: 'pct1' },
      { chave: 'maior_rajada', rotulo: 'Maior rajada', formato: 'num' },
      { chave: 'rajada_inicio', rotulo: 'Início (Brasília)' }, { chave: 'rajada_fim', rotulo: 'Fim' },
      { chave: 'sinal_tipo', rotulo: 'Sinal' }, { chave: 'q_min', rotulo: 'q', formato: (v) => (v < 0.0001 ? '< 0,0001' : num(v, 4)) },
      { chave: 'lula1', rotulo: 'Lula 1º', formato: 'pct1' }, { chave: 'lula2', rotulo: 'Lula 2º', formato: 'pct1' },
      { chave: 'dlula_w', rotulo: 'Δ vs município', formato: 'pp1' },
    ],
  },
  'ch07-tab-saltos': {
    src: 'data/ch07/saltos.json', porPagina: 25, filtro: true, ordem: { chave: 'z', direcao: 'desc' },
    legenda: 'Seções em que a habilitação sem biometria saltou entre turnos',
    colunas: [
      { chave: 'uf', rotulo: 'UF' }, { chave: 'municipio', rotulo: 'Município' }, { chave: 'zona', rotulo: 'Zona' },
      { chave: 'secao', rotulo: 'Seção' },
      { chave: 'biom_sh_1', rotulo: 'Sem bio 1º', formato: 'num' }, { chave: 'biom_sh_2', rotulo: 'Sem bio 2º', formato: 'num' },
      { chave: 'tx1', rotulo: 'Taxa 1º', formato: 'pct1' }, { chave: 'tx2', rotulo: 'Taxa 2º', formato: 'pct1' },
      { chave: 'z', rotulo: 'z', formato: 'num1' },
      { chave: 'lula1', rotulo: 'Lula 1º', formato: 'pct1' }, { chave: 'lula2', rotulo: 'Lula 2º', formato: 'pct1' },
      { chave: 'dlula_w', rotulo: 'Δ vs município', formato: 'pp1' },
    ],
  },
  'ch07-tab-regs': {
    src: 'data/ch07/regressoes.json', porPagina: 0, filtro: false,
    legenda: 'Regressões da fatia de Lula na taxa sem biometria',
    colunas: [
      { chave: 'modelo', rotulo: 'Especificação' },
      { chave: 'coef', rotulo: 'Efeito de +10 p.p. na taxa', formato: (v) => pp(v * 0.1) },
      { chave: 'ic_inf', rotulo: 'IC 95% inf.', formato: (v) => pp(v * 0.1) },
      { chave: 'ic_sup', rotulo: 'IC 95% sup.', formato: (v) => pp(v * 0.1) },
      { chave: 'p', rotulo: 'p', formato: 'valorP' }, { chave: 'n', rotulo: 'Seções', formato: 'num' },
    ],
  },
};
