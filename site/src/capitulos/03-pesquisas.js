/**
 * Capítulo 11 — As pesquisas erraram só para um lado?
 * Dados: public/data/ch11/*.json (gerados por analises/11_pesquisas.py).
 */
import { num, pct } from '../lib/formato.js';

const ORDEM = ['2014 · 2º turno', '2018 · 2º turno', '2022 · 1º turno', '2022 · 2º turno', '2026 · 1º turno', '2026 · 2º turno'];
const ppSin = (v, c = 1) => `${v > 0 ? '+' : ''}${num(v, c)} p.p.`;

export const graficos = {
  /** Pesquisas finais do 2º turno de 2026: fatia de Lula vs. resultado. */
  'ch11-finais': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.filter((x) => x.eleicao === '2026 · 2º turno')
        .slice().sort((a, b) => a.fatia_pt_pesquisa - b.fatia_pt_pesquisa);
      const res = d[0]?.fatia_pt_resultado;
      return {
        grid: { left: largura < 560 ? 112 : 150, right: 24, top: 28, bottom: 40 },
        tooltip: {
          trigger: 'item',
          formatter: (it) => {
            const x = d[it.dataIndex];
            return `<b>${x.instituto}</b> (${x.campo}${x.amostra ? `, n = ${num(x.amostra)}` : ''})<br>`
              + `Lula na pesquisa: ${num(x.fatia_pt_pesquisa, 1)}% dos votos em Lula + Flávio<br>`
              + `Resultado: ${num(x.fatia_pt_resultado, 2)}%<br>Erro: <b>${ppSin(x.erro_pt, 2)}</b>`;
          },
        },
        yAxis: { type: 'category', data: d.map((x) => x.instituto), axisLabel: { fontSize: largura < 560 ? 10 : 12 } },
        xAxis: { type: 'value', min: 46, max: 53, name: largura < 560 ? 'Fatia de Lula na pesquisa (%)' : 'Fatia de Lula na pesquisa (% dos votos em Lula + Flávio)', nameLocation: 'middle', nameGap: 30,
          axisLabel: { formatter: (v) => `${v}%` } },
        series: [
          { type: 'scatter', symbolSize: 10, itemStyle: { color: p.lula }, data: d.map((x, i) => [x.fatia_pt_pesquisa, i]),
            markLine: {
              silent: true, symbol: 'none',
              data: [
                { xAxis: res, lineStyle: { color: p.lula, width: 2 }, label: { formatter: `resultado ${num(res, 2)}%`, color: p.texto1, position: 'end' } },
                { xAxis: 50, lineStyle: { color: p.texto3, type: 'dashed', width: 1 }, label: { show: false } },
              ],
            } },
        ],
      };
    },
  },

  /** Erro das pesquisas finais na fatia do PT, por eleição (pontos com leve deslocamento vertical). */
  'ch11-historico': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const cat = ORDEM.filter((e) => d.some((x) => x.eleicao === e));
      const desloc = (i) => (((i * 37) % 11) / 11) * 0.5 - 0.25;
      const estreito = largura < 560;
      return {
        grid: { left: estreito ? 96 : 124, right: 24, top: 16, bottom: 48 },
        tooltip: {
          trigger: 'item',
          formatter: (it) => {
            const x = it.data.linha;
            return `<b>${x.instituto}</b> — ${x.eleicao}<br>PT na pesquisa: ${num(x.fatia_pt_pesquisa, 1)}%<br>`
              + `Resultado: ${num(x.fatia_pt_resultado, 2)}%<br>Erro: <b>${ppSin(x.erro_pt, 2)}</b>`;
          },
        },
        yAxis: { type: 'category', data: cat, inverse: true, axisLabel: { fontSize: estreito ? 10 : 12 }, splitLine: { show: true } },
        xAxis: { type: 'value', min: -6, max: 6, axisLabel: { formatter: (v) => ppSin(v, 0) },
          name: estreito ? 'resultado − pesquisa (p.p.)' : '← superestimou o PT     resultado − pesquisa (p.p.)     subestimou o PT →',
          nameLocation: 'middle', nameGap: 30, nameTextStyle: { fontSize: estreito ? 10 : 11 } },
        series: [{
          type: 'scatter', symbolSize: 10,
          itemStyle: { color: (it) => (it.data.value[0] > 0 ? p.lula : p.flavio), borderColor: p.sup0, borderWidth: 1 },
          data: d.map((x, i) => ({ value: [x.erro_pt, x.eleicao], symbolOffset: [0, desloc(i) * 40], linha: x })),
          markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, label: { show: false }, data: [{ xAxis: 0 }] },
        }],
      };
    },
  },
};

export const tabelas = {
  'ch11-resumo': {
    src: 'data/ch11/resumo.json',
    porPagina: 0, filtro: false,
    colunas: [
      { chave: 'eleicao', rotulo: 'Eleição' },
      { chave: 'pesquisas', rotulo: 'Pesquisas', formato: 'num' },
      { chave: 'erro_medio', rotulo: 'Erro médio (PT)', formato: (v) => ppSin(v, 2) },
      { chave: 'erro_min', rotulo: 'Mín.', formato: (v) => ppSin(v, 1) },
      { chave: 'erro_max', rotulo: 'Máx.', formato: (v) => ppSin(v, 1) },
      { chave: 'subestimaram_pt', rotulo: 'Subestimaram o PT', formato: 'num' },
    ],
  },
  'ch11-todas': {
    src: 'data/ch11/erros.json',
    porPagina: 20, filtro: true,
    ordem: { chave: 'erro_pt', direcao: 'desc' },
    colunas: [
      { chave: 'eleicao', rotulo: 'Eleição' },
      { chave: 'instituto', rotulo: 'Instituto' },
      { chave: 'campo', rotulo: 'Campo' },
      { chave: 'fatia_pt_pesquisa', rotulo: 'PT na pesquisa', formato: (v) => `${num(v, 1)}%` },
      { chave: 'fatia_pt_resultado', rotulo: 'Resultado', formato: (v) => `${num(v, 2)}%` },
      { chave: 'erro_pt', rotulo: 'Erro', formato: (v) => ppSin(v, 2) },
      { chave: 'escala', rotulo: 'Escala' },
      { chave: 'fonte', rotulo: 'Fonte', html: (l) => (l.fonte ? `<a href="${l.fonte}" target="_blank" rel="noopener">link</a>` : '—') },
    ],
  },
  'ch11-transferencia': {
    src: 'data/ch11/transferencia.json',
    porPagina: 0, filtro: false,
    colunas: [
      { chave: 'instituto', rotulo: 'Pesquisa' },
      { chave: 'campo', rotulo: 'Campo' },
      { chave: 'flavio', rotulo: 'Flávio', formato: (v) => pct(v / 100, 0) },
      { chave: 'lula', rotulo: 'Lula', formato: (v) => pct(v / 100, 0) },
      { chave: 'branco_nulo', rotulo: 'Branco/nulo', formato: (v) => (v == null ? '—' : pct(v / 100, 0)) },
      { chave: 'verificado', rotulo: 'Conferido na fonte', formato: (v) => (v ? 'sim' : 'não') },
    ],
  },
};

