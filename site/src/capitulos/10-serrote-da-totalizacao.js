/**
 * Capítulo 6b — O "serrote" da totalização.
 * Dados: public/data/ch06b/*.json (gerados por analises/06c_serrote_totalizacao.py).
 * Percentuais em fração; resíduos de fase em p.p.
 */
import { pct, pp, num, compacto } from '../lib/formato.js';

const linha = (name, data, cor, extra = {}) => ({
  name, type: 'line', showSymbol: false, data, lineStyle: { width: 2, color: cor, ...(extra.lineStyle || {}) },
  itemStyle: { color: cor }, ...extra,
});

/** Placebo: variação do acumulado desde o início da janela, 2T × 1T das mesmas seções. */
function placebo(ano) {
  const nome = ano === '2022' ? 'Bolsonaro' : 'Flávio';
  return {
    opcao: (json, p, { largura }) => {
      const d = json.dados[ano];
      return {
        legend: { data: [`${nome}, votos do 2º turno`, `${nome}, votos do 1º turno (mesmas seções)`] },
        grid: { left: 26, bottom: 46 },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pp(v, 3) },
        xAxis: { type: 'value', min: 65000, max: 90000, name: 'Seções recebidas (nº)', nameLocation: 'middle', nameGap: 30,
          axisLabel: { formatter: (v) => compacto(v) } },
        yAxis: { type: 'value', name: largura < 560 ? 'Variação do acumulado (p.p.)' : 'Variação do % acumulado desde 65 mil seções (p.p.)', nameLocation: 'middle', nameGap: 80, axisLabel: { formatter: (v) => pp(v, 2) } },
        series: [
          linha(`${nome}, votos do 2º turno`, d.map((x) => [x.secoes, x.t2]), p.flavio),
          linha(`${nome}, votos do 1º turno (mesmas seções)`, d.map((x) => [x.secoes, x.t1]), p.texto2, { lineStyle: { type: 'dashed' } }),
        ],
      };
    },
  };
}

export const graficos = {
  'ch06b-serie': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const pontos = [[23954, 0.529867], [72747, 0.516508]];
      return {
        legend: { data: ['Bolsonaro', 'Lula'] },
        tooltip: { trigger: 'axis', formatter: (it) => {
          const x = d[it[0].dataIndex];
          return `${num(x.secoes)} seções · ${x.hora}<br>Bolsonaro: <b>${pct(x.pe_b, 4)}</b><br>Lula: ${pct(x.pe_l, 4)}`;
        } },
        grid: { left: 20, bottom: 46 },
        xAxis: { type: 'value', max: 472075, name: 'Seções totalizadas (nº)', nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => compacto(v) } },
        yAxis: { type: 'value', min: 0.3, max: 0.7, name: largura < 560 ? 'Acumulado (%)' : 'Percentual acumulado dos votos válidos (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [
          linha('Bolsonaro', d.map((x) => [x.secoes, x.pe_b]), p.flavio, {
            markPoint: { symbol: 'circle', symbolSize: 8, itemStyle: { color: p.texto1 },
              label: { show: largura >= 560, position: 'right', color: p.texto2, fontSize: 11,
                formatter: (it) => `${num(it.value[0])}: ${num(it.value[1], 6)}` },
              data: pontos.map((v) => ({ coord: v, value: v })) },
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, label: { show: false }, data: [{ yAxis: 0.5 }] },
          }),
          linha('Lula', d.map((x) => [x.secoes, x.pe_l]), p.lula),
        ],
      };
    },
  },

  'ch06b-zoom': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const vale = (x) => x.inc_b < 0.35 && x.n >= 5;
      return {
        grid: [{ top: 24, height: '40%', left: 80, right: 24 }, { top: '60%', bottom: 56, left: 80, right: 24 }],
        tooltip: { trigger: 'item', formatter: (it) => {
          const x = d[it.dataIndex];
          return `${x.hora} · ${num(x.secoes)} seções<br>Acumulado de Bolsonaro: <b>${pct(x.pe_b, 4)}</b>`
            + `<br>Lote deste segundo: ${num(x.n)} seções, ${pct(x.inc_b, 1)} para Bolsonaro`;
        } },
        xAxis: [
          { gridIndex: 0, type: 'value', min: 65000, max: 90000, axisLabel: { show: false } },
          { gridIndex: 1, type: 'value', min: 65000, max: 90000, axisLabel: { formatter: (v) => compacto(v) },
            name: 'Seções totalizadas (nº)', nameLocation: 'middle', nameGap: 30 },
        ],
        yAxis: [
          { gridIndex: 0, type: 'value', scale: true, name: 'Acumulado (%)', nameLocation: 'middle', nameGap: 58, axisLabel: { formatter: (v) => pct(v, 2) } },
          { gridIndex: 1, type: 'value', min: 0, max: 1, name: 'Fatia do lote (%)', nameLocation: 'middle', nameGap: 46, axisLabel: { formatter: (v) => pct(v, 0) } },
        ],
        series: [
          { type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: d.map((x) => [x.secoes, x.pe_b]), showSymbol: true, symbolSize: 4,
            lineStyle: { width: 2, color: p.flavio }, itemStyle: { color: p.flavio } },
          { type: 'scatter', xAxisIndex: 1, yAxisIndex: 1,
            data: d.map((x) => [x.secoes, x.inc_b, x.n]),
            symbolSize: (v) => Math.max(4, Math.sqrt(v[2]) * 1.1),
            itemStyle: { color: (it) => (vale(d[it.dataIndex]) ? p.lula : p.texto3), opacity: 0.8 },
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' },
              label: { formatter: '35%', color: p.texto3 }, data: [{ yAxis: 0.35 }] } },
        ],
      };
    },
  },

  'ch06b-espectro': {
    opcao: (json, p) => ({
      legend: { data: ['2º turno 2022', '1º turno 2022'] },
      tooltip: { trigger: 'axis', formatter: (it) => `Período ${num(it[0].value[0], 1)} s<br>`
        + it.map((s) => `${s.seriesName}: ${num(s.value[1], 1)}×`).join('<br>') },
      grid: { left: 20, bottom: 46 },
      xAxis: { type: 'log', min: 10, max: 300, name: 'Período do ciclo (segundos, escala log)', nameLocation: 'middle', nameGap: 30,
        axisLabel: { formatter: (v) => num(v) } },
      yAxis: { type: 'value', name: 'Potência relativa à mediana (×)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => `${num(v)}×` } },
      series: [
        linha('2º turno 2022', json.dados.t2.map((x) => [x.periodo_s, x.potencia]), p.flavio, {
          markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' },
            label: { formatter: (it) => `${num(it.value)} s`, color: p.texto2 }, data: [{ xAxis: 22 }, { xAxis: 33 }, { xAxis: 66 }] } }),
        linha('1º turno 2022', json.dados.t1.map((x) => [x.periodo_s, x.potencia]), p.texto2, { lineStyle: { type: 'dashed' } }),
      ],
    }),
  },

  'ch06b-placebo-2022': placebo('2022'),
  'ch06b-placebo-2026': placebo('2026'),

  'ch06b-fase': {
    opcao: (json, p, { largura }) => {
      const s = (ano) => json.dados[ano].perfil.map((x) => [x.segundo, x.residuo_pp / 100]);
      return {
        legend: { data: ['2022 (Bolsonaro)', '2026 (Flávio)'] },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pp(v, 3) },
        grid: { left: 26, bottom: 46 },
        xAxis: { type: 'value', min: 0, max: 59, name: largura < 560 ? 'Segundo de chegada do boletim' : 'Segundo do minuto em que o boletim chegou', nameLocation: 'middle', nameGap: 30 },
        yAxis: { type: 'value', name: 'Resíduo da fatia (p.p.)', nameLocation: 'middle', nameGap: 80, axisLabel: { formatter: (v) => pp(v, 2) } },
        series: [
          linha('2022 (Bolsonaro)', s('2022'), p.texto2, { showSymbol: true, symbolSize: 8 }),
          linha('2026 (Flávio)', s('2026'), p.flavio, { showSymbol: true, symbolSize: 8,
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, label: { show: false }, data: [{ yAxis: 0 }] } }),
        ],
      };
    },
  },

  'ch06b-composicao': {
    opcao: (json, p, { largura }) => {
      const regs = ['Nordeste', 'Norte', 'Centro-Oeste', 'Sudeste', 'Sul'];
      const cores = [p.texto1, p.sequencial[1], p.sequencial[2], p.sequencial[3], p.sequencial[4]];
      return {
        legend: { data: regs },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v, 1) },
        grid: { left: 20, bottom: 46 },
        xAxis: { type: 'value', min: 0, max: 472028, axisLabel: { formatter: (v) => compacto(v) },
          name: 'Seções recebidas (nº)', nameLocation: 'middle', nameGap: 30 },
        yAxis: { type: 'value', min: 0, max: 0.45, name: largura < 560 ? 'Participação (%)' : 'Participação da região nas seções recebidas (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: regs.map((r, i) => linha(r, json.dados.map((x) => [x.secoes, x[r]]), cores[i])),
      };
    },
  },
};

export const tabelas = {
  'ch06b-tab-assinatura': {
    src: 'data/ch06b/assinatura.json',
    colunas: [
      { chave: 'tipo', rotulo: 'Tipo' },
      { chave: 'faixa', rotulo: 'Grupo' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'fatia_b', rotulo: 'Bolsonaro', formato: 'pct1' },
      { chave: 'comparecimento', rotulo: 'Compar.', formato: 'pct1' },
      { chave: 'brancos_nulos', rotulo: 'Br.+nulos', formato: 'pct1' },
      { chave: 'aptos_secao', rotulo: 'Aptos/seção', formato: 'num' },
    ],
  },
};
