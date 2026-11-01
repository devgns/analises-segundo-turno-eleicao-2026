/**
 * Capítulo 5 — Os detectores conseguem ver uma alteração uniforme? (testes de poder)
 * Dados: public/data/cap05-*.json (gerados por analises/05_poder_detectores.py).
 * Simulador: worker próprio em src/workers/alteracao.worker.js (dados reais de 2026).
 */
import { pct, pp, num } from '../lib/formato.js';
import { urlDados } from '../lib/dados.js';

const TIPOS = ['Uniforme', 'Proporcional à força de Flávio', 'Concentrada em seções sorteadas',
  'Concentrada em municípios sorteados', 'Só urnas UE2020', 'Só seções que fecharam após 17h05'];
const UNIFORMES = ['uniforme', 'proporcional'];

/** Séries de poder por k para um conjunto de detectores num cenário. */
function curvas(json, p, cenario, detectores, cores, largura = 1000) {
  const ks = [0, ...new Set(json.dados.filter((d) => d.cenario === cenario).map((d) => d.k))];
  return {
    legend: { data: detectores.map((d) => json.detectores[d]), type: 'scroll' },
    tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v, 0) },
    grid: { left: 64, right: 20, top: 64, bottom: 52 },
    xAxis: { type: 'value', min: 0, max: 0.08, name: largura < 560 ? 'Votos de Flávio desviados (%)' : 'Votos de Flávio desviados para Lula (% do total nacional)', nameLocation: 'middle',
      nameGap: 32, axisLabel: { formatter: (v) => pct(v, 0) } },
    yAxis: { type: 'value', min: 0, max: 1, axisLabel: { formatter: (v) => pct(v, 0) }, name: 'Taxa de detecção (%)', nameLocation: 'middle', nameGap: 44 },
    series: detectores.map((d, i) => ({
      name: json.detectores[d], type: 'line', symbolSize: 8, lineStyle: { width: 2, color: cores[i] }, itemStyle: { color: cores[i] },
      data: ks.map((k) => [k, k === 0 ? 0.05 : json.dados.find((x) => x.cenario === cenario && x.detector === d && x.k === k)?.poder]),
      ...(i === 0 ? { markLine: { symbol: 'none', silent: true, lineStyle: { color: p.texto2, type: 'dashed', width: 1 },
        label: { color: p.texto2, formatter: 'vira o resultado', position: 'insideEndTop' }, data: [{ xAxis: json.k_virada }] } } : {}),
    })),
  };
}

export const graficos = {
  'ch05-mapa-poder': {
    opcao: (json, p, { largura }) => {
      const k = 0.04;
      const cens = Object.keys(json.cenarios);
      const dets = Object.keys(json.detectores);
      const CURTO_CEN = { uniforme: 'Uniforme', proporcional: 'Proporcional', secoes10: '10% seções', municipios10: '10% municípios',
        urna_ue2020: 'Só UE2020', tardias: 'Só tardias' };
      const CURTO_DET = { d1_outliers_secao: 'Outliers de seção', d2_fdr_municipios: 'Regressão + FDR', d3_dispersao_residuo: 'Dispersão do resíduo',
        d4_benford2: 'Benford 2º dígito', d5_ultimo_digito: 'Último dígito', d6_extremos: 'Seções extremas', d7_digital: 'Impressão digital',
        d8_disp_vs_2022: 'Dispersão vs. 2022', d9_forma_1t2t: 'Forma 1º × 2º turno', s1_retencao_f: 'Retenção de Flávio' };
      const dados = [];
      cens.forEach((c, i) => dets.forEach((d, j) => {
        const v = json.dados.find((x) => x.cenario === c && x.detector === d && x.k === k)?.poder;
        dados.push([i, j, v]);
      }));
      return {
        tooltip: { formatter: (it) => `${json.cenarios[cens[it.data[0]]]}<br>${json.detectores[dets[it.data[1]]]}<br>Detecção: <b>${pct(it.data[2], 0)}</b>` },
        grid: { left: largura < 560 ? 112 : 150, right: 8, top: 8, bottom: largura < 560 ? 82 : 56, containLabel: largura >= 560 },
        xAxis: { type: 'category', data: cens.map((c) => CURTO_CEN[c]), axisLabel: {
          interval: 0, rotate: largura < 560 ? 0 : largura < 700 ? 35 : 0, fontSize: largura < 560 ? 9 : 11,
          hideOverlap: largura >= 560,
          formatter: largura < 560 ? (v) => ({ Uniforme: 'Unif.', Proporcional: 'Prop.', '10% seções': '10%\nseções', '10% municípios': '10%\nmun.', 'Só UE2020': 'UE2020', 'Só tardias': 'Tard.' }[v] ?? v) : undefined,
        }, splitArea: { show: false } },
        yAxis: { type: 'category', data: dets.map((d) => CURTO_DET[d]), axisLabel: { fontSize: largura < 560 ? 10 : 11, width: largura < 560 ? 100 : 140, overflow: 'truncate' } },
        visualMap: { min: 0, max: 1, show: false, inRange: { color: p.sequencial } },
        series: [{ type: 'heatmap', data: dados, itemStyle: { borderColor: p.sup0, borderWidth: 2, borderRadius: 4 },
          label: { show: true, fontSize: largura < 560 ? 9 : 11, color: p.texto1, formatter: (it) => pct(it.data[2], 0),
            backgroundColor: p.sup0, padding: [1, largura < 560 ? 0 : 4], borderRadius: 3 } }],
      };
    },
  },
  'ch05-uniforme': {
    opcao: (json, p, { largura }) => curvas(json, p, 'uniforme',
      ['d1_outliers_secao', 'd2_fdr_municipios', 'd4_benford2', 'd5_ultimo_digito', 'd6_extremos', 'd9_forma_1t2t'],
      [p.lula, p.flavio, p.texto3, p.brancos, p.sequencial[3], p.nulos], largura),
  },
  'ch05-nivel': {
    opcao: (json, p, { largura }) => curvas(json, p, 'uniforme', ['s1_retencao_f', 'd8_disp_vs_2022', 'd3_dispersao_residuo', 'd7_digital'],
      [p.lula, p.flavio, p.sequencial[3], p.texto3], largura),
  },
  'ch05-fdr-cenarios': {
    opcao: (json, p, { largura }) => {
      const cens = Object.keys(json.cenarios);
      const cores = [p.texto3, p.brancos, p.lula, p.flavio, p.sequencial[3], p.nulos];
      const op = curvas(json, p, cens[0], ['d2_fdr_municipios'], [cores[0]], largura);
      op.legend = { data: cens.map((c) => json.cenarios[c]), type: 'scroll' };
      op.series = cens.map((c, i) => {
        const ks = [0, ...new Set(json.dados.filter((d) => d.cenario === c).map((d) => d.k))];
        return { name: json.cenarios[c], type: 'line', symbolSize: 8, lineStyle: { width: 2, color: cores[i], type: UNIFORMES.includes(c) ? 'dashed' : 'solid' },
          itemStyle: { color: cores[i] },
          data: ks.map((k) => [k, k === 0 ? 0.05 : json.dados.find((x) => x.cenario === c && x.detector === 'd2_fdr_municipios' && x.k === k)?.poder]) };
      });
      return op;
    },
  },
  'ch05-retencao': {
    opcao: (json, p, ctx) => {
      const e22 = json.eco_mun_2022;
      const e26 = json.eco_mun_2026;
      const ic = json.ic_mun;
      const cats = ['Retenção de Lula', 'Retenção da direita'];
      const v22 = [e22.lula[0], e22.direita[1]];
      const v26 = [e26.lula[0], e26.direita[1]];
      const ic22 = [ic['2022'].ret_lula, ic['2022'].ret_direita];
      const ic26 = [ic['2026'].ret_lula, ic['2026'].ret_direita];
      const barra = (nome, vals, ics, cor, desl) => ([
        { name: nome, type: 'bar', barMaxWidth: 28, itemStyle: { color: cor, borderRadius: [4, 4, 0, 0] }, data: vals },
        { name: nome, type: 'custom', z: 3, renderItem: (params, api) => {
          const i = api.value(0);
          const a = api.coord([i, api.value(1)]);
          const b = api.coord([i, api.value(2)]);
          const w = Math.min(28, (api.size([1, 0])[0] * 0.8) / 2.3); // largura real da barra (2 séries, barGap 30%)
          const x = a[0] + desl * w * 0.65;
          return { type: 'group', children: [
            { type: 'line', shape: { x1: x, y1: a[1], x2: x, y2: b[1] }, style: { stroke: p.texto1, lineWidth: 1.5 } },
          ] };
        }, data: ics.map((c, i) => [i, c[0], c[1]]), tooltip: { show: false } },
      ]);
      return {
        legend: { data: ['2022 (Lula × Bolsonaro)', '2026 (Lula × Flávio)'] },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => pct(v, 1) },
        grid: { left: 68, right: 16, top: 40, bottom: 40 },
        xAxis: { type: 'category', data: cats, axisLabel: { interval: 0, width: ctx.largura < 560 ? 96 : 140, overflow: 'break', fontSize: ctx.largura < 560 ? 10 : 12 } },
        yAxis: { type: 'value', min: 0.85, max: 1.1, name: ctx.largura < 560 ? 'Retenção (%)' : 'Retenção líquida estimada (% do 1º turno)', nameLocation: 'middle', nameGap: 46, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [...barra('2022 (Lula × Bolsonaro)', v22, ic22, p.sequencial[2], -1), ...barra('2026 (Lula × Flávio)', v26, ic26, p.sequencial[4], 1)],
      };
    },
  },
};

export const tabelas = {
  'ch05-acrescimo': {
    src: 'data/ch05/poder-acrescimo.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'fonte', rotulo: 'Origem hipotética' },
      { chave: 'forma', rotulo: 'Distribuição' },
      { chave: 'taxa', rotulo: 'Fração do estoque', formato: 'pct1' },
      { chave: 'votos_media', rotulo: 'Votos acrescentados (média)', formato: 'num' },
      { chave: 'alarme_fdr', rotulo: 'Alarme FDR', formato: 'pct1' },
      { chave: 'alarme_ultimo_digito', rotulo: 'Alarme último dígito', formato: 'pct1' },
    ],
  },
  'ch05-excesso': {
    src: 'data/cap05-assinaturas.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'faixa_f1', rotulo: 'Flávio no 1º turno (seção)' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'pct_lula_acima_estoque', rotulo: 'Lula ganha mais que o estoque', formato: 'pct' },
      { chave: 'pct_flavio_acima_estoque', rotulo: 'Flávio ganha mais que o estoque', formato: 'pct' },
      { chave: 'pct_flavio_perde', rotulo: 'Flávio perde votos', formato: 'pct1' },
      { chave: 'pct_lula_perde', rotulo: 'Lula perde votos', formato: 'pct1' },
      { chave: 'delta_f_rel', rotulo: 'Δ Flávio / Flávio 1º t.', formato: 'pct1' },
      { chave: 'delta_l_rel', rotulo: 'Δ Lula / Lula 1º t.', formato: 'pct1' },
    ],
  },
};

/* ---------- simulador ---------- */
let painelVereditos = null;
function desenharVereditos(r) {
  if (!painelVereditos) return;
  const linhas = r.detectores.map((d) => {
    const ve = d.poder >= 0.5;
    const fmt = (x) => (Math.abs(x) < 10 ? num(x, 4) : num(x, 0));
    return `<tr><td>${d.nome}</td><td class="tabela__num">${fmt(d.media_nulo)}</td><td class="tabela__num">${fmt(d.media_manip)}</td>
      <td class="tabela__num">${fmt(d.nulo_lo)} a ${fmt(d.nulo_hi)}</td>
      <td><strong>${ve ? 'percebe' : 'não percebe'}</strong> (${pct(d.poder, 0)} das réplicas)</td></tr>`;
  }).join('');
  painelVereditos.classList.add('tabela');
  painelVereditos.innerHTML = `<div class="tabela__rolagem"><table><caption class="sr-only">Veredito de cada detector</caption><thead><tr><th>Detector</th><th class="tabela__num">Sem alteração (média)</th>
    <th class="tabela__num">Com a alteração</th><th class="tabela__num">Faixa sem alteração</th><th>Veredito</th></tr></thead><tbody>${linhas}</tbody></table></div>`;
}

export const simuladores = {
  'sim-fraude': {
    titulo: 'Simule uma alteração nos dados reais de 2026',
    subtitulo: 'Distribuição da oscilação de Flávio entre finalistas nos 5.571 municípios: dados reais × dados com a alteração simulada.',
    fonte: 'TSE — boletins de urna 2026 (5.571 municípios e amostra aleatória de 30.000 seções); manipulação sintética',
    tarefa: 'fraude',
    espera: 250,
    criarWorker: () => new Worker(new URL('../workers/alteracao.worker.js', import.meta.url), { type: 'module' }),
    controles: [
      { id: 'tipo', rotulo: 'Tipo de alteração', min: 0, max: 5, passo: 1, valor: 0, formato: (v) => TIPOS[v],
        ajuda: 'Uniforme = mesma fração dos votos de Flávio vira Lula em toda seção.' },
      { id: 'k', rotulo: 'Tamanho: votos de Flávio transferidos (total nacional)', min: 0, max: 0.08, passo: 0.0025, valor: 0.04, formato: 'pct1',
        ajuda: '3,7% bastam para inverter o resultado.' },
      { id: 'frac', rotulo: 'Fração atingida (só para os tipos concentrados)', min: 0.02, max: 0.5, passo: 0.01, valor: 0.1, formato: 'pct1' },
    ],
    parametros: (v) => ({ ...v, urlMun: urlDados('data/cap05-municipios.json'), urlSec: urlDados('data/cap05-secoes.json'), reps: 30, semente: 7 }),
    opcao: (r, v, p) => {
      desenharVereditos(r);
      return {
        legend: { data: ['Dados reais', 'Com a alteração simulada'] },
        tooltip: { trigger: 'axis', formatter: (ps) => `Oscilação ≈ ${pp(r.x[ps[0].dataIndex], 1)}<br>${ps.map((s) => `${s.seriesName}: ${num(s.value)} municípios`).join('<br>')}` },
        grid: { left: 64, right: 16, top: 40, bottom: 52 },
        xAxis: { type: 'category', data: r.x.map((x) => pp(x, 0)), axisLabel: { interval: 14 }, name: 'Oscilação da fatia de Flávio entre finalistas (p.p.)', nameLocation: 'middle', nameGap: 32 },
        yAxis: { type: 'value', name: 'Municípios', nameLocation: 'middle', nameGap: 44 },
        series: [
          { name: 'Dados reais', type: 'line', step: 'middle', symbol: 'none', lineStyle: { width: 2, color: p.texto3 }, itemStyle: { color: p.texto3 }, data: r.histReal },
          { name: 'Com a alteração simulada', type: 'line', step: 'middle', symbol: 'none', lineStyle: { width: 2, color: p.lula }, itemStyle: { color: p.lula },
            areaStyle: { color: p.lula, opacity: 0.1 }, data: r.histMan },
        ],
      };
    },
    resumo: (r, v) => `Alteração: ${TIPOS[v.tipo].toLowerCase()}, ${num(r.votosMovidos)} votos de Flávio para Lula `
      + `(Lula iria de ${pct(r.lulaReal)} para ${pct(r.lulaManip)}). A média municipal da oscilação se desloca de ${pp(r.mediaReal)} para ${pp(r.mediaMan)}; `
      + `o desvio-padrão, de ${pp(r.sdReal)} para ${pp(r.sdMan)}. `
      + `Regressão + FDR: ${r.detectores[0].poder >= 0.5 ? 'percebe' : 'não percebe'} (${pct(r.detectores[0].poder, 0)} das ${r.reps} réplicas). `
      + `Detectores com referência conhecida que percebem: ${r.detectores.slice(1).filter((d) => d.poder >= 0.5).length} de ${r.detectores.length - 1} (eles conhecem os dados sem a alteração; um analista real não).`,
  },
};

export function montar(secao) {
  painelVereditos = secao.querySelector('[data-ch05-vereditos]');
}
