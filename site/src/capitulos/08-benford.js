/**
 * Capítulo 10 — Benford, dígitos e impressão digital.
 * Dados: public/data/ch10/*.json (gerados por analises/10_benford.py).
 */
import { num, pct } from '../lib/formato.js';

const ROT = { '1BL': '1º dígito', '2BL': '2º dígito', ultimo: 'último dígito' };
const ROT_EIXO = { '1BL': '1º dígito dos votos da seção', '2BL': '2º dígito dos votos da seção', ultimo: 'Último dígito dos votos da seção' };

/** Barras = observado (Lula e Flávio, 2º turno 2026); linha tracejada = Benford; ◆ = nulo simulado com faixa de 95%. */
function digitosOpcao(teste) {
  return (json, p, { largura }) => {
    const d = json.dados.filter((x) => x.teste === teste && x.eleicao === '2026 · 2º turno');
    const L = d.filter((x) => x.candidato === 'Lula');
    const F = d.filter((x) => x.candidato === 'Flávio');
    const cats = L.map((x) => String(x.digito));
    const faixa = (arr) => arr.map((x, i) => [i, x.nulo_p025, x.nulo_p975]);
    const barra = (nome, arr, cor) => ({
      name: nome, type: 'bar', barMaxWidth: 24, barGap: '20%',
      itemStyle: { color: cor, borderRadius: [4, 4, 0, 0] }, data: arr.map((x) => x.observado),
    });
    const intervalo = (arr, desloc) => ({
      name: 'Nulo simulado (95%)', type: 'custom', z: 5,
      renderItem: (params, api) => {
        const larg = api.size([1, 0])[0];
        const x = api.coord([api.value(0), 0])[0] + desloc * larg * 0.22;
        const y1 = api.coord([0, api.value(1)])[1];
        const y2 = api.coord([0, api.value(2)])[1];
        const ym = (y1 + y2) / 2;
        return { type: 'group', children: [
          { type: 'line', shape: { x1: x, y1: Math.min(y1, ym - 3), x2: x, y2: Math.max(y2, ym + 3) }, style: { stroke: p.texto1, lineWidth: 2 } },
          { type: 'line', shape: { x1: x - 4, y1: ym, x2: x + 4, y2: ym }, style: { stroke: p.texto1, lineWidth: 2 } },
        ] };
      },
      itemStyle: { color: p.texto1 },
      data: faixa(arr),
    });
    return {
      legend: { data: ['Lula', 'Flávio', 'Lei de Benford (teórica)', 'Nulo simulado (95%)'] },
      grid: { top: largura < 560 ? 64 : 40, left: 20, bottom: 46 },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.4 } },
        formatter: (its) => {
          const i = its[0].dataIndex;
          const l = L[i]; const f = F[i];
          return `<b>${ROT[teste]} = ${cats[i]}</b><br>`
            + `Lula: ${pct(l.observado, 2)} (nulo ${pct(l.nulo, 2)}; faixa ${pct(l.nulo_p025, 2)}–${pct(l.nulo_p975, 2)})<br>`
            + `Flávio: ${pct(f.observado, 2)} (nulo ${pct(f.nulo, 2)}; faixa ${pct(f.nulo_p025, 2)}–${pct(f.nulo_p975, 2)})<br>`
            + `Benford: ${pct(l.benford, 2)}`;
        },
      },
      xAxis: { type: 'category', data: cats, name: ROT_EIXO[teste], nameLocation: 'middle', nameGap: 30 },
      yAxis: { type: 'value', name: 'Frequência do dígito (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
      series: [
        barra('Lula', L, p.lula),
        barra('Flávio', F, p.flavio),
        { name: 'Lei de Benford (teórica)', type: 'line', symbol: 'circle', symbolSize: 8, z: 6,
          lineStyle: { color: p.texto2, type: 'dashed', width: 2 }, itemStyle: { color: p.texto2 }, data: L.map((x) => x.benford) },
        intervalo(L, -1),
        intervalo(F, 1),
      ],
    };
  };
}

/** Impressão digital (Klimek): comparecimento × fatia de Lula. */
function digitalOpcao(eleicao) {
  return (json, p, { largura }) => {
    const d = json.dados.filter((x) => x.eleicao === eleicao);
    const passo = 0.02;
    const xs = Array.from({ length: 50 }, (_, i) => +(i * passo + 0.01).toFixed(3));
    const idx = (v) => Math.round((v - 0.01) / passo);
    const dados = d.map((x) => [idx(x.fatia_lula), idx(x.comparecimento), Math.log10(x.secoes), x.secoes]);
    return {
      grid: { left: 24, right: 16, top: 16, bottom: largura < 560 ? 72 : 64, containLabel: true },
      tooltip: {
        trigger: 'item',
        formatter: (it) => `Fatia de Lula ${pct(xs[it.value[0]] - 0.01, 0)}–${pct(xs[it.value[0]] + 0.01, 0)}<br>`
          + `Comparecimento ${pct(xs[it.value[1]] - 0.01, 0)}–${pct(xs[it.value[1]] + 0.01, 0)}<br><b>${num(it.value[3])} seções</b>`,
      },
      xAxis: { type: 'category', data: xs, name: 'Fatia de Lula nos votos válidos da seção (%)', nameLocation: 'middle', nameGap: 30,
        axisLabel: { interval: 9, formatter: (v) => pct(v - 0.01, 0) }, splitLine: { show: false } },
      yAxis: { type: 'category', data: xs, name: 'Comparecimento da seção (%)', nameLocation: 'middle', nameGap: 40, axisLabel: { interval: 9, formatter: (v) => pct(v - 0.01, 0) },
        splitLine: { show: false } },
      visualMap: {
        min: 0, max: 4, dimension: 2, calculable: false, orient: 'horizontal', left: 'center', bottom: 0, itemHeight: 140,
        inRange: { color: p.sequencial }, text: ['10.000 seções', '1'], textStyle: { color: p.texto2, fontSize: 11 },
      },
      series: [{ type: 'heatmap', data: dados, progressive: 0, emphasis: { itemStyle: { borderColor: p.texto1, borderWidth: 1 } } }],
    };
  };
}

export const graficos = {
  'ch10-1bl': { opcao: digitosOpcao('1BL') },
  'ch10-2bl': { opcao: digitosOpcao('2BL') },
  'ch10-ultimo': { opcao: digitosOpcao('ultimo') },
  'ch10-digital-2026-2': { opcao: digitalOpcao('2026 · 2º turno') },
  'ch10-digital-2026-1': { opcao: digitalOpcao('2026 · 1º turno') },
  'ch10-digital-2022-2': { opcao: digitalOpcao('2022 · 2º turno') },
};

const chi = (v) => num(v, v >= 100 ? 0 : 1);
const pv = (v) => (v < 0.001 ? '< 0,001' : num(v, 3));

export const tabelas = {
  'ch10-testes': {
    src: 'data/ch10/testes.json',
    porPagina: 0, filtro: false,
    colunas: [
      { chave: 'eleicao', rotulo: 'Eleição' },
      { chave: 'candidato', rotulo: 'Candidato' },
      { chave: 'teste', rotulo: 'Teste', formato: (v) => ROT[v] },
      { chave: 'n', rotulo: 'Seções', formato: 'num' },
      { chave: 'chi2_benford', rotulo: 'χ² vs. Benford', formato: chi },
      { chave: 'rejeicao_ingenua_betabinomial', rotulo: 'Eleições simuladas sem alteração "reprovadas"', formato: (v) => pct(v, 0) },
      { chave: 'chi2_nulo_betabinomial', rotulo: 'χ² vs. nulo', formato: chi },
      { chave: 'chi2_nulo_betabinomial_p95', rotulo: 'χ² nulo (p95)', formato: chi },
      { chave: 'p_nulo_betabinomial', rotulo: 'p (nulo)', formato: pv },
      { chave: 'media_digito', rotulo: 'Dígito médio', formato: 'num2' },
    ],
  },
  'ch10-digital-resumo': {
    src: 'data/ch10/impressao-resumo.json',
    porPagina: 0, filtro: false,
    colunas: [
      { chave: 'eleicao', rotulo: 'Eleição' },
      { chave: 'comparecimento_medio', rotulo: 'Comparecimento médio', formato: 'pct1' },
      { chave: 'corr_comparecimento_fatia_lula', rotulo: 'Correlação comp. × Lula', formato: 'num2' },
      { chave: 'secoes_comp_ge95', rotulo: 'Seções com comp. ≥ 95%', formato: 'num' },
      { chave: 'secoes_comp_ge95_lula_ge95', rotulo: '… e Lula ≥ 95%', formato: 'num' },
      { chave: 'secoes_comp_ge95_flavio_ge95', rotulo: '… e adversário ≥ 95%', formato: 'num' },
      { chave: 'fatia_lula_comp_ge95', rotulo: 'Lula nas seções comp. ≥ 95%', formato: 'pct1' },
      { chave: 'fatia_lula_total', rotulo: 'Lula no total', formato: 'pct1' },
    ],
  },
};
