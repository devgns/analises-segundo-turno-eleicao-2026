/**
 * Capítulo 2 — O mapa da virada. Dados: analises/02_mapa_virada.py → public/data/ch02/*.json
 */
import { num, pct, pp } from '../lib/formato.js';
import { registrarMapa } from '../components/mapa.js';

const titulo = (s) => String(s ?? '').toLowerCase().replace(/(^|[\s(-])(\p{L})/gu, (m, a, b) => a + b.toUpperCase())
  .replace(/ (D[aeo]s?|E) /g, (m) => m.toLowerCase());

/** Coroplético de Δfatia; `campo` = 'd26' | 'd22'. */
function mapa(campo, ano) {
  return {
    tabela: false,
    opcao: async (json, p, { largura }) => {
      await registrarMapa('br-municipios');
      const estreito = largura < 560;
      return {
        tooltip: {
          trigger: 'item',
          formatter: (x) => (x.data
            ? `${titulo(x.data.municipio)} (${x.data.uf})<br>Δfatia de Lula ${ano}: <b>${pp(x.data.valor)}</b>`
            : ''),
        },
        visualMap: {
          type: 'continuous', min: -0.06, max: 0.06, calculable: false, orient: 'horizontal',
          left: 'center', bottom: 0, itemWidth: 12, itemHeight: estreito ? 110 : 240,
          text: [estreito ? 'Lula' : 'a favor de Lula', estreito ? 'Direita' : 'a favor do candidato da direita'],
          textStyle: { color: p.texto2, fontSize: 11 },
          inRange: { color: p.divergente },
          formatter: (v) => pp(v, 0),
        },
        series: [{
          type: 'map', map: 'br-municipios', nameProperty: 'codigo_ibge', roam: true,
          aspectScale: 0.95, top: 8, bottom: 56, scaleLimit: { min: 1, max: 30 },
          itemStyle: { borderWidth: 0, areaColor: p.grade },
          emphasis: { label: { show: false }, itemStyle: { areaColor: p.texto1 } },
          select: { disabled: true },
          data: json.dados.map((d) => ({
            name: d.codigo_ibge, value: Math.max(-0.06, Math.min(0.06, d[campo] ?? 0)),
            valor: d[campo], municipio: d.municipio, uf: d.uf,
          })),
        }],
      };
    },
  };
}

export const graficos = {
  'ch02-mapa-2026': mapa('d26', 2026),
  'ch02-mapa-2022': mapa('d22', 2022),

  /** Distribuições sobrepostas do deslocamento a favor de quem estava atrás. */
  'ch02-hist': (json, p, { largura }) => {
    const d = json.dados;
    const serie = (ano, nome, cor) => {
      const s = d.filter((x) => x.ano === ano);
      const tot = s.reduce((a, x) => a + x.municipios, 0);
      return {
        name: nome, type: 'line', symbol: 'none', lineStyle: { width: 2, color: cor }, itemStyle: { color: cor },
        areaStyle: { color: cor, opacity: 0.1 }, data: s.map((x) => [x.faixa, x.municipios / tot]),
      };
    };
    return {
      legend: { data: ['2026: a favor de Lula', '2022: a favor de Bolsonaro'] },
      grid: { top: 48, left: 64, right: 16, bottom: 48 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'line' }, valueFormatter: (v) => pct(v, 1) + ' dos municípios' },
      xAxis: {
        type: 'value', min: -0.04, max: 0.08, name: largura < 560 ? 'Δ fatia (p.p.)' : 'Variação da fatia a favor de quem estava atrás (p.p.)',
        nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pp(v, 0) },
      },
      yAxis: { type: 'value', name: 'Municípios (% do total)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
      series: [
        { ...serie(2026, '2026: a favor de Lula', p.lula),
          markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed', width: 1 },
            label: { show: false }, data: [{ xAxis: 0 }] } },
        serie(2022, '2022: a favor de Bolsonaro', p.flavio),
      ],
    };
  },

  /** Interceptos (magnitude a favor de quem estava atrás) com IC 95%. */
  'ch02-intercepto': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const cats = [
        { rot: 'Brasil (municípios)', f: (r) => r.modelo === `municipio ${r.ano}` },
        { rot: 'Brasil (seções)', f: (r) => r.modelo === `secao ${r.ano}` },
        ...['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul'].map((g) => ({
          rot: g, f: (r) => r.nivel === 'municipio-regiao' && r.regiao === g,
        })),
      ];
      const pega = (ano, c) => d.find((r) => r.ano === ano && c.f(r));
      const anos = [
        { ano: 2026, nome: '2026: a favor de Lula', cor: p.lula, sinal: 1 },
        { ano: 2022, nome: '2022: a favor de Bolsonaro', cor: p.flavio, sinal: -1 },
      ];
      const nomes = cats.map((c) => c.rot).reverse();
      const series = [];
      anos.forEach((a, i) => {
        const pts = cats.map((c) => {
          const r = pega(a.ano, c);
          const lo = Math.min(a.sinal * r.ic95_inf, a.sinal * r.ic95_sup);
          const hi = Math.max(a.sinal * r.ic95_inf, a.sinal * r.ic95_sup);
          return { rot: c.rot, v: a.sinal * r.intercepto, lo, hi, n: r.n };
        });
        const off = i === 0 ? -0.18 : 0.18;
        series.push({
          name: a.nome, type: 'scatter', symbolSize: 10, itemStyle: { color: a.cor, borderColor: p.sup0, borderWidth: 2 },
          data: pts.map((x) => ({ value: [x.v, nomes.indexOf(x.rot) + off], ...x })),
          z: 3,
        });
        series.push({
          name: a.nome, type: 'custom', silent: true, z: 2,
          renderItem: (params, api) => {
            const y = api.value(2);
            const a0 = api.coord([api.value(0), y]);
            const a1 = api.coord([api.value(1), y]);
            return { type: 'line', shape: { x1: a0[0], y1: a0[1], x2: a1[0], y2: a1[1] }, style: { stroke: a.cor, lineWidth: 2 } };
          },
          encode: { x: [0, 1], y: 2 },
          data: pts.map((x) => [x.lo, x.hi, nomes.indexOf(x.rot) + off]),
        });
      });
      return {
        legend: { data: anos.map((a) => a.nome) },
        grid: { top: 48, left: largura < 560 ? 112 : 140, right: 24, bottom: 40 },
        tooltip: {
          trigger: 'item',
          formatter: (x) => (x.seriesType === 'scatter'
            ? `${x.data.rot} · ${x.seriesName}<br>Intercepto: <b>${pp(x.data.v)}</b><br>IC 95%: ${pp(x.data.lo)} a ${pp(x.data.hi)}<br>${num(x.data.n)} unidades`
            : ''),
        },
        xAxis: { type: 'value', min: 0, max: 0.05, name: largura < 560 ? 'Intercepto (p.p.)' : 'Deslocamento comum não explicado (p.p. da fatia entre finalistas)', nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pp(v, 0).replace('+', '') } },
        yAxis: { type: 'value', min: -1, max: nomes.length, interval: 1, splitLine: { show: false },
          axisLabel: { formatter: (v) => nomes[v] ?? '' } },
        series,
      };
    },
  },

  /** Dispersão: fatia de Lula no 1º turno × Δfatia (municípios, 2026). */
  'ch02-dispersao': { tabela: false, opcao: (json, p, { largura }) => {
    const d = json.dados;
    return {
      grid: { top: 24, left: 72, right: 16, bottom: 52 },
      tooltip: {
        trigger: 'item',
        formatter: (x) => `${titulo(x.data.m)} (${x.data.uf})<br>Fatia de Lula no 1º turno: ${pct(x.data.value[0], 1)}<br>Δfatia: <b>${pp(x.data.value[1])}</b><br>${num(x.data.e)} eleitores`,
      },
      xAxis: { type: 'value', min: 0, max: 1, name: largura < 560 ? 'Fatia de Lula no 1º turno (%)' : 'Fatia de Lula entre os finalistas, 1º turno (%)', nameLocation: 'middle', nameGap: 32, axisLabel: { formatter: (v) => pct(v, 0) } },
      yAxis: { type: 'value', min: -0.1, max: 0.12, name: largura < 560 ? 'Variação (p.p.)' : 'Variação da fatia de Lula entre turnos (p.p.)', nameLocation: 'middle', nameGap: 48, axisLabel: { formatter: (v) => pp(v, 0) } },
      series: [{
        type: 'scatter', symbolSize: (v, x) => Math.max(4, Math.min(16, Math.sqrt(x.data.e) / 40)),
        large: false, itemStyle: { color: p.lula, opacity: 0.45, borderColor: p.sup0, borderWidth: 0.5 },
        emphasis: { itemStyle: { opacity: 1, borderColor: p.texto1, borderWidth: 1.5 } },
        data: d.map((r) => ({ value: [r.s1, r.d_fatia], m: r.municipio, uf: r.uf, e: r.eleitores })),
        markLine: {
          silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed', width: 1 },
          label: { color: p.texto2, formatter: 'Brasil +2,80 p.p.', position: 'insideEndTop' },
          data: [{ yAxis: 0.027967 }],
        },
      }],
    };
  } },
};

export const tabelas = {
  'ch02-uf': {
    src: 'data/ch02/dispersao-uf.json',
    legenda: 'Deslocamento por UF, 2026 e 2022',
    porPagina: 27,
    ordem: { chave: 'dp', direcao: 'desc' },
    colunas: [
      { chave: 'ano', rotulo: 'Ano', formato: 'texto' },
      { chave: 'uf', rotulo: 'UF' },
      { chave: 'regiao', rotulo: 'Região' },
      { chave: 'municipios', rotulo: 'Municípios', formato: 'num' },
      { chave: 'media', rotulo: 'Δfatia média', formato: 'pp' },
      { chave: 'dp', rotulo: 'Desvio-padrão', formato: (v) => pp(v).replace('+', '') },
      { chave: 'iqr', rotulo: 'IQR', formato: (v) => pp(v).replace('+', '') },
      { chave: 'frac_mesmo_sinal', rotulo: 'Na direção nacional', formato: 'pct1' },
    ],
  },
  'ch02-explorador': {
    src: 'data/ch02/municipios.json',
    legenda: 'Explorador de municípios, 2026',
    porPagina: 25,
    filtro: true,
    ordem: { chave: 'eleitores', direcao: 'desc' },
    colunas: [
      { chave: 'uf', rotulo: 'UF' },
      { chave: 'municipio', rotulo: 'Município', formato: titulo },
      { chave: 'eleitores', rotulo: 'Eleitores', formato: 'num' },
      { chave: 'l1', rotulo: 'Lula 1º', formato: 'num' },
      { chave: 'f1', rotulo: 'Flávio 1º', formato: 'num' },
      { chave: 'o1', rotulo: 'Eliminados', formato: 'num' },
      { chave: 'l2', rotulo: 'Lula 2º', formato: 'num' },
      { chave: 'f2', rotulo: 'Flávio 2º', formato: 'num' },
      { chave: 'd_lula', rotulo: 'Δ Lula', formato: 'num' },
      { chave: 'd_flavio', rotulo: 'Δ Flávio', formato: 'num' },
      { chave: 'd_fatia', rotulo: 'Δfatia', formato: 'pp' },
      { chave: 'pctl', rotulo: 'Percentil', formato: (v) => num(v * 100, 0) },
      { chave: 'residuo', rotulo: 'Resíduo do modelo', formato: 'pp' },
      { chave: 'd_fatia_2022', rotulo: 'Δfatia 2022', formato: 'pp' },
    ],
  },
};
