/**
 * Capítulo 6c — O "serrote" nos casos do RJ.
 * Dados: public/data/ch06c/*.json (gerados por analises/06c_serrote_casos_rj.py).
 */
import { pct, num } from '../lib/formato.js';

const sinal = (x, casas = 0) => (x > 0 ? '+' : '') + num(x, casas);

/** ΔLula e ΔFlávio (votos, 2T − 1T) acumulados na ordem de chegada dos boletins. */
function deltaAcumulado(mun) {
  return {
    opcao: (json, p, { largura }) => {
      const d = json.dados[mun];
      return {
        legend: { data: ['Δ Lula acumulado', 'Δ Flávio acumulado'] },
        tooltip: { trigger: 'axis', formatter: (it) => {
          const x = d[it[0].dataIndex];
          return `${num(x.i)}ª seção a chegar (${x.hora})<br>Δ Lula acumulado: <b>${sinal(x.dl)}</b><br>Δ Flávio acumulado: <b>${sinal(x.df)}</b>`;
        } },
        grid: { left: 24, bottom: 46 },
        xAxis: { type: 'value', min: 1, max: d.length, name: 'Seções, na ordem de chegada do boletim (nº)', nameLocation: 'middle', nameGap: 30, axisLabel: { showMaxLabel: false } },
        yAxis: { type: 'value', name: largura < 560 ? 'Δ acumulado (votos)' : 'Variação acumulada, 2º − 1º turno (votos)', nameLocation: 'middle', nameGap: 62, axisLabel: { formatter: (v) => num(v) } },
        series: [
          { name: 'Δ Lula acumulado', type: 'line', showSymbol: false, data: d.map((x) => [x.i, x.dl]),
            lineStyle: { width: 2, color: p.lula }, itemStyle: { color: p.lula } },
          { name: 'Δ Flávio acumulado', type: 'line', showSymbol: false, data: d.map((x) => [x.i, x.df]),
            lineStyle: { width: 2, color: p.flavio }, itemStyle: { color: p.flavio },
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, label: { show: false }, data: [{ yAxis: 0 }] } },
        ],
      };
    },
  };
}

export const graficos = {
  'ch06c-placebo': {
    opcao: (json, p, { largura }) => {
      const d = json.dados['Campos dos Goytacazes (placebo)'];
      return {
        legend: { data: ['Flávio, votos do 2º turno', 'Flávio, votos do 1º turno (mesmas seções)'] },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v, 2) },
        grid: { left: 24, bottom: 46 },
        xAxis: { type: 'value', min: 1, max: d.length, name: 'Seções, na ordem de chegada do boletim (nº)', nameLocation: 'middle', nameGap: 30, axisLabel: { showMaxLabel: false } },
        yAxis: { type: 'value', scale: true, name: largura < 560 ? 'Flávio acumulado (%)' : 'Fatia acumulada de Flávio entre os finalistas (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [
          { name: 'Flávio, votos do 2º turno', type: 'line', showSymbol: false, data: d.map((x) => [x.i, x.t2]),
            lineStyle: { width: 2, color: p.flavio }, itemStyle: { color: p.flavio } },
          { name: 'Flávio, votos do 1º turno (mesmas seções)', type: 'line', showSymbol: false, data: d.map((x) => [x.i, x.t1]),
            lineStyle: { width: 2, color: p.texto2, type: 'dashed' }, itemStyle: { color: p.texto2 } },
        ],
      };
    },
  },
  'ch06c-delta-campos': deltaAcumulado('Campos dos Goytacazes'),
  'ch06c-delta-sj': deltaAcumulado('Silva Jardim'),
};

export const tabelas = {
  'ch06c-testes': {
    src: 'data/ch06c/tabela.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'grupo', rotulo: 'Grupo' },
      { chave: 'teste', rotulo: 'Teste' },
      { chave: 'efeito', rotulo: 'Maior desvio' },
      { chave: 'p', rotulo: 'p', formato: (v) => num(v, 3) },
      { chave: 'poder_2', rotulo: 'Detecta 2%', formato: (v) => (v == null ? '—' : pct(v, 0)) },
      { chave: 'poder_5', rotulo: 'Detecta 5%', formato: (v) => (v == null ? '—' : pct(v, 0)) },
    ],
  },
  'ch06c-municipios': {
    src: 'data/ch06c/municipios.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'municipio', rotulo: 'Município' },
      { chave: 'inicio', rotulo: 'Chegada: de' },
      { chave: 'fim', rotulo: 'até' },
      { chave: 'corr_placebo', rotulo: 'Placebo (r)', formato: (v) => num(v, 2) },
      { chave: 'delta_f_1a_metade', rotulo: 'Δ Flávio, 1ª metade', formato: (v) => sinal(v) },
      { chave: 'delta_f_2a_metade', rotulo: 'Δ Flávio, 2ª metade', formato: (v) => sinal(v) },
      { chave: 'secoes_f_caiu', rotulo: 'Seções com Flávio ↓', formato: 'num' },
      { chave: 'secoes_f_subiu', rotulo: 'Seções com Flávio ↑', formato: 'num' },
    ],
  },
};
