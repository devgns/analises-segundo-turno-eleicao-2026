/**
 * Capítulo 8 — Os logs das urnas: modelos, alertas, substituições.
 * Dados: public/data/ch08/*.json (gerados por analises/08_logs.py e analises/08_substituicoes.py).
 */
import { pct, pp, num } from '../lib/formato.js';

function intervalos(p, d, rotulo, chaveRot) {
  return [
    { type: 'custom', encode: { x: [1, 2], y: 0 }, renderItem: (params, api) => {
      const y = api.coord([0, api.value(0)])[1];
      const a = api.coord([api.value(1), 0])[0];
      const b = api.coord([api.value(2), 0])[0];
      return { type: 'line', shape: { x1: a, y1: y, x2: b, y2: y }, style: { stroke: p.texto2, lineWidth: 2 } };
    }, data: d.map((x, i) => [i, x.ic_inf, x.ic_sup]) },
    { type: 'scatter', symbolSize: 10, itemStyle: { color: p.texto1 }, data: d.map((x, i) => [x.coef, i]),
      markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, data: [{ xAxis: 0 }], label: { show: false } } },
  ];
}

export const graficos = {
  /** Fatia de Lula por modelo, 1º e 2º turno. */
  'ch08-modelos': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      return {
        legend: { data: ['1º turno', '2º turno'] },
        grid: { left: 20, bottom: 52 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => pct(v) },
        xAxis: { type: 'category', data: d.map((x) => `${x.modelo_urna} (${num(x.secoes)} seções)`), name: 'Modelo de urna (nº de seções)', nameLocation: 'middle', nameGap: 36, axisLabel: { fontSize: 11 } },
        yAxis: { type: 'value', name: largura < 560 ? 'Fatia de Lula (%)' : 'Fatia de Lula nos votos válidos (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) }, min: 0.3 },
        series: [
          { name: '1º turno', type: 'bar', barMaxWidth: 24, itemStyle: { color: p.lulaClaro, borderRadius: [4, 4, 0, 0] }, data: d.map((x) => x.lula_1_fatia) },
          { name: '2º turno', type: 'bar', barMaxWidth: 24, itemStyle: { color: p.lula, borderRadius: [4, 4, 0, 0] }, data: d.map((x) => x.lula_2_fatia),
            label: { show: true, position: 'top', color: p.texto2, fontSize: 11, formatter: (it) => pp(d[it.dataIndex].delta, 1) } },
        ],
      };
    },
  },

  /** Coeficientes de modelo de urna (relativo à UE2013) por especificação. */
  'ch08-modelos-reg': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.slice().reverse();
      const rot = d.map((x) => `${x.modelo} · ${largura < 560 ? x.especificacao.replace(/\s*\(.*\)/, '').slice(0, 22) : x.especificacao}`);
      return {
        grid: { left: 8, right: 24, top: 16, bottom: 46 },
        tooltip: { trigger: 'item', formatter: (it) => {
          const x = d[it.dataIndex];
          return `${x.modelo} vs UE2013 — ${x.especificacao}<br>Diferença no Δ de Lula: <b>${pp(x.coef)}</b><br>IC 95%: ${pp(x.ic_inf)} a ${pp(x.ic_sup)}<br>n = ${num(x.n)}`;
        } },
        yAxis: { type: 'category', data: rot, axisLabel: { fontSize: 11 } },
        xAxis: { type: 'value', axisLabel: { formatter: (v) => pp(v, 1) }, name: largura < 560 ? 'Δ fatia de Lula vs. UE2013 (p.p.)' : 'Diferença no Δ da fatia de Lula, relativa à UE2013 (p.p.)',
          nameLocation: 'middle', nameGap: 30 },
        series: intervalos(p, d),
      };
    },
  },

  /** Hora em que a urna ficou pronta. */
  'ch08-pronta': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      return {
        legend: { data: ['Seções normais', 'Seções com troca de urna'] },
        grid: { left: 28, bottom: 46 },
        tooltip: { trigger: 'axis', valueFormatter: (v) => `${num(v)} seções` },
        xAxis: { type: 'category', data: d.map((x) => x.hora), name: largura < 560 ? 'Urna pronta (Brasília)' : 'Hora em que a urna ficou pronta (Brasília)', nameLocation: 'middle', nameGap: 30, axisLabel: { interval: largura < 560 ? 23 : 11 } },
        yAxis: { type: 'log', min: 1, name: largura < 560 ? 'Seções (log)' : 'Seções (nº, escala log)', nameLocation: 'middle', nameGap: 80, axisLabel: { formatter: (v) => num(v) } },
        series: [
          { name: 'Seções normais', type: 'bar', barMaxWidth: 24, itemStyle: { color: p.sequencial[2], borderRadius: [4, 4, 0, 0] },
            data: d.map((x) => x.normal || null) },
          { name: 'Seções com troca de urna', type: 'bar', barMaxWidth: 24, barGap: '-100%', itemStyle: { color: p.sequencial[4], borderRadius: [4, 4, 0, 0] },
            data: d.map((x) => x.substituida || null) },
        ],
      };
    },
  },

  /** Δ Lula por decil de alertas. */
  'ch08-alertas': {
    opcao: (json, p) => {
      const d = json.dados;
      return {
        tooltip: { trigger: 'axis', formatter: (its) => {
          const x = d[its[0].dataIndex];
          return `${x.decil}: ${num(x.alertas_por_100, 1)} alertas por 100 votos<br>Δ Lula vs município: <b>${pp(x.dlula_w, 2)}</b><br>${num(x.secoes)} seções`;
        } },
        xAxis: { type: 'category', data: d.map((x) => `${x.decil}\n${num(x.alertas_por_100, 1)}`), name: 'Decil de alertas (alertas por 100 votos)',
          nameLocation: 'middle', nameGap: 42 },
        grid: { left: 28, bottom: 60 },
        yAxis: { type: 'value', name: 'Δ fatia de Lula vs. município (p.p.)', nameLocation: 'middle', nameGap: 76, axisLabel: { formatter: (v) => pp(v, 1) }, min: -0.01, max: 0.01 },
        series: [{ type: 'bar', barMaxWidth: 24, itemStyle: { color: p.sequencial[3], borderRadius: [4, 4, 0, 0] }, data: d.map((x) => x.dlula_w) }],
      };
    },
  },
};

export const tabelas = {
  'ch08-tab-subst': {
    src: 'data/ch08/substituicoes.json', porPagina: 25, filtro: true, ordem: { chave: 'comparecimento', direcao: 'desc' },
    legenda: 'Seções com log principal menor que o BU',
    colunas: [
      { chave: 'uf', rotulo: 'UF' }, { chave: 'municipio', rotulo: 'Município' }, { chave: 'zona', rotulo: 'Zona' },
      { chave: 'secao', rotulo: 'Seção' }, { chave: 'comparecimento', rotulo: 'Comparecimento (BU)', formato: 'num' },
      { chave: 'votos_ultima_urna', rotulo: 'Votos na última urna', formato: 'num' },
      { chave: 'votos_todos_logs', rotulo: 'Votos em todos os logs', formato: 'num' },
      { chave: 'dif_bu', rotulo: 'Diferença', formato: 'num' }, { chave: 'urnas_com_voto', rotulo: 'Urnas com voto', formato: 'num' },
      { chave: 'troca_bsb', rotulo: 'Troca (Brasília)' }, { chave: 'modelo_urna', rotulo: 'Modelo' },
      { chave: 'lula1', rotulo: 'Lula 1º', formato: 'pct1' }, { chave: 'lula2', rotulo: 'Lula 2º', formato: 'pct1' },
      { chave: 'dlula_w', rotulo: 'Δ vs município', formato: 'pp1' },
    ],
  },
  'ch08-tab-esq': {
    src: 'data/ch08/esquisitices.json', porPagina: 0, filtro: false,
    legenda: 'Inconsistências procuradas no log por eleitor',
    colunas: [
      { chave: 'item', rotulo: 'O que procuramos' },
      { chave: 'eleitores', rotulo: 'Registros', formato: 'num' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
    ],
  },
  'ch08-tab-tipo': {
    src: 'data/ch08/tipo_urna.json', porPagina: 0, filtro: false,
    legenda: 'Tipo de urna no bweb',
    colunas: [
      { chave: 'turno', rotulo: 'Turno' }, { chave: 'tipo_urna', rotulo: 'Tipo de urna' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' }, { chave: 'comparecimento', rotulo: 'Comparecimento', formato: 'num' },
      { chave: 'lula', rotulo: 'Lula', formato: 'num' }, { chave: 'flavio', rotulo: 'Flávio', formato: 'num' },
    ],
  },
};
