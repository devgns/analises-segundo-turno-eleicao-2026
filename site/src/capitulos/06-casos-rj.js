/**
 * Capítulo 4 — Região dos Lagos e Silva Jardim: os casos do RJ.
 * Dados: public/data/cap04-*.json (gerados por analises/04_casos_rj.py).
 */
import { pct, pp, num } from '../lib/formato.js';

const curtoMun = (s) => s.replace('Campos dos Goytacazes', 'Campos').replace('Armação dos Búzios', 'Búzios')
  .replace('São Pedro da Aldeia', 'S. P. da Aldeia');
const sinal = (x, casas = 2) => (x > 0 ? '+' : '') + num(x, casas);

export const graficos = {
  /** Histograma nacional da oscilação de Flávio, com os 9 casos marcados. */
  'ch04-hist': {
    opcao: (json, p, { largura }) => {
      const h = json.hist_y;
      const estreito = largura < 560;
      return {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: (ps) => `Oscilação ≈ ${pp(ps[0].data[0], 1)}<br>${num(ps[0].data[1])} municípios` },
        grid: { left: 64, right: 16, top: 24, bottom: 52 },
        xAxis: { type: 'value', min: -0.1, max: 0.04, name: estreito ? 'Oscilação de Flávio (p.p.)' : 'Oscilação da fatia de Flávio entre finalistas (p.p.)',
          nameLocation: 'middle', nameGap: 32, axisLabel: { formatter: (v) => pp(v, 0) } },
        yAxis: { type: 'value', name: 'Municípios', nameLocation: 'middle', nameGap: 44 },
        series: [{
          type: 'bar', barWidth: '95%', itemStyle: { color: p.sequencial[2], borderRadius: [2, 2, 0, 0] },
          data: h.map((b) => [b.x, b.n]),
          markLine: {
            symbol: 'none', silent: true,
            lineStyle: { color: p.flavio, width: 1.5, type: 'solid' },
            label: { show: !estreito, color: p.texto2, fontSize: 10, formatter: (d) => d.name, position: 'insideEndTop' },
            // Os nove nomes se sobrepõem; as outras linhas permanecem no gráfico
            // e os municípios podem ser consultados na tabela do capítulo.
            data: json.dados.map((d) => ({ xAxis: d.osc_f, name: curtoMun(d.municipio),
              label: { show: !estreito && d.municipio.includes('Campos') } })),
          },
        }],
      };
    },
  },

  /** Dispersão: fatia de Flávio no 1º turno × oscilação. */
  'ch04-dispersao': {
    opcao: (json, p, { largura }) => {
      const outros = json.dados.filter((d) => !d.caso);
      const casos = json.dados.filter((d) => d.caso);
      const tip = (d) => `${d.nm_municipio} (${d.sg_uf})<br>Flávio no 1º turno: ${pct(d.sf1, 1)}<br>Oscilação: ${pp(d.y)}<br>z (modelo): ${num(d.z_reg, 2)}`;
      return {
        legend: { data: ['Municípios do país (amostra)', 'Nove casos do RJ'] },
        tooltip: { trigger: 'item', formatter: (it) => tip(it.data.d) },
        grid: { left: 72, right: 16, top: 36, bottom: 52 },
        xAxis: { type: 'value', min: 0, max: 1, name: largura < 560 ? 'Fatia de Flávio no 1º turno (%)' : 'Fatia de Flávio entre os finalistas, 1º turno (%)', nameLocation: 'middle', nameGap: 32,
          axisLabel: { formatter: (v) => pct(v, 0) } },
        yAxis: { type: 'value', min: -0.12, max: 0.08, name: largura < 560 ? 'Oscilação (p.p.)' : 'Oscilação da fatia de Flávio (p.p.)', nameLocation: 'middle', nameGap: 48, axisLabel: { formatter: (v) => pp(v, 0) } },
        series: [
          { name: 'Municípios do país (amostra)', type: 'scatter', symbolSize: 4, itemStyle: { color: p.texto3, opacity: 0.45 },
            data: outros.map((d) => ({ value: [d.sf1, d.y], d })), large: true },
          { name: 'Nove casos do RJ', type: 'scatter', symbolSize: 10, itemStyle: { color: p.flavio, borderColor: p.sup0, borderWidth: 2 },
            data: casos.map((d) => ({ value: [d.sf1, d.y], d })), z: 3 },
        ],
      };
    },
  },

  /** Resíduo médio por UF. */
  'ch04-uf': {
    opcao: (json, p) => {
      const d = json.dados.slice().sort((a, b) => b.residuo_medio - a.residuo_medio);
      return {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: (ps) => { const x = d[ps[0].dataIndex]; return `${x.sg_uf}: resíduo ${pp(x.residuo_medio)}<br>Oscilação bruta da UF: ${pp(x.osc_f_uf)}<br>${num(x.municipios)} municípios`; } },
        grid: { left: 36, right: 24, top: 8, bottom: 56 },
        yAxis: { type: 'category', data: d.map((x) => x.sg_uf), axisLabel: { fontSize: 11 } },
        xAxis: { type: 'value', name: 'Resíduo médio da UF (p.p. da fatia de Flávio)', nameLocation: 'middle', nameGap: 32, axisLabel: { formatter: (v) => pp(v, 1) } },
        series: [{
          type: 'bar', barMaxWidth: 14,
          data: d.map((x) => ({ value: x.residuo_medio,
            itemStyle: { color: x.sg_uf === 'RJ' ? p.lula : (x.residuo_medio < 0 ? p.lulaClaro : p.flavioClaro),
              borderRadius: x.residuo_medio < 0 ? [4, 0, 0, 4] : [0, 4, 4, 0] } })),
        }],
      };
    },
  },

  /** Aglomerados de 9 vizinhos: distribuição nacional e posição dos casos. */
  'ch04-aglomerados': {
    opcao: (json, p) => {
      const h = json.hist_aglomerados_z_reg;
      const m = json.z_reg.media_9_casos;
      return {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: (ps) => `z médio ≈ ${num(ps[0].data[0], 2)}<br>${num(ps[0].data[1])} aglomerados` },
        grid: { left: 64, right: 16, top: 24, bottom: 52 },
        xAxis: { type: 'value', min: -3, max: 3, name: 'Resíduo padronizado médio do aglomerado (z)', nameLocation: 'middle', nameGap: 32 },
        yAxis: { type: 'value', name: 'Aglomerados', nameLocation: 'middle', nameGap: 44 },
        series: [{
          type: 'bar', barWidth: '95%', itemStyle: { color: p.sequencial[2], borderRadius: [2, 2, 0, 0] },
          data: h.map((b) => [b.x, b.n]),
          markLine: { symbol: 'none', silent: true, lineStyle: { color: p.flavio, width: 2 },
            label: { color: p.texto1, formatter: `nove casos: ${num(m, 2)} (percentil ${num(json.z_reg.percentil_9_casos, 1)})`, position: 'insideEndTop' },
            data: [{ xAxis: m }] },
        }],
      };
    },
  },

  /** Silva Jardim: ΔF e ΔL por seção. */
  'ch04-sj-secoes': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      return {
        legend: { data: ['Variação de Flávio', 'Variação de Lula'] },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: (ps) => { const x = d[ps[0].dataIndex]; return `Zona ${x.zona}, seção ${x.secao} (local ${x.local})<br>Flávio: ${sinal(x.df, 0)} · Lula: ${sinal(x.dl, 0)}<br>Eliminados no 1º turno: ${num(x.outros_1)}<br>Comparecimento: ${num(x.comp_1)} → ${num(x.comp_2)}<br>Urna ${x.modelo_urna}, ${x.n_alertas} alertas, encerrou ${x.encerramento}`; } },
        grid: { left: 60, right: 12, top: 36, bottom: largura >= 700 ? 70 : 40 },
        xAxis: { type: 'category', data: d.map((x) => x.secao), name: largura < 560 ? 'Seções' : 'Seções de Silva Jardim (ordenadas pela variação de Flávio)', nameLocation: 'middle', nameGap: largura >= 700 ? 44 : 14, axisLabel: { show: largura >= 700, interval: 0, rotate: 90, fontSize: 9 } },
        yAxis: { type: 'value', name: 'Variação (votos, 2º − 1º turno)', nameLocation: 'middle', nameGap: 40 },
        series: [
          { name: 'Variação de Flávio', type: 'bar', barMaxWidth: 8, itemStyle: { color: p.flavio, borderRadius: [2, 2, 2, 2] }, data: d.map((x) => x.df) },
          { name: 'Variação de Lula', type: 'bar', barMaxWidth: 8, itemStyle: { color: p.lula, borderRadius: [2, 2, 2, 2] }, data: d.map((x) => x.dl) },
        ],
      };
    },
  },

  /** Monte Carlo: probabilidade por cenário. */
  'ch04-mc': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.slice().reverse();
      const rot = (x) => {
        const so = /só sorteio/.test(x.cenario);
        if (x.grupo === 'base') return so ? 'Premissas que circularam: só sorteio' : 'Premissas que circularam + variação municipal';
        if (x.grupo === 'eliminados') return `Eliminados ${pct(x.elim_f, x.elim_f === 0.644 ? 1 : 0)} p/ Flávio`;
        if (x.grupo === 'retencao') return `Retenção de Flávio ${pct(x.ret_f, 0)}`;
        if (x.grupo === 'dispersao') return `Concentração Dirichlet ${num(x.conc)}`;
        return so ? 'Matriz do RJ: só sorteio' : 'Matriz do RJ + variação do RJ';
      };
      const cor = { base: p.texto1, eliminados: p.sequencial[3], retencao: p.sequencial[4], dispersao: p.sequencial[2], dados: p.lula };
      return {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: (ps) => { const x = d[ps[0].dataIndex]; return `${x.cenario}<br>P(fatia de Flávio ≤ observada): <b>${pct(x.p_fatia_le_obs, 2)}</b><br>P(Flávio ≤ 8.933), válidos livres: ${pct(x.p_flavio_le_obs, 2)}${x.p_flavio_le_obs_validos_exato != null ? `<br>P(Flávio ≤ 8.933 | válidos = 14.367): ${pct(x.p_flavio_le_obs_validos_exato, 2)}<br>Válidos previstos: ${num(x.validos_previstos)} (observado 14.367)` : ''}<br>Mediana simulada de Flávio: ${num(x.mediana_flavio)} (95%: ${num(x.p025_flavio)}–${num(x.p975_flavio)})`; } },
        grid: { left: 190, right: 48, top: 8, bottom: 56 },
        yAxis: { type: 'category', data: d.map(rot), axisLabel: { fontSize: 11, width: 180, overflow: 'truncate' } },
        xAxis: { type: 'value', min: 0, max: 0.6, splitNumber: 3, name: largura < 560 ? 'Probabilidade (%)' : 'Probabilidade de a fatia de Flávio ser ≤ à observada (%)', nameLocation: 'middle', nameGap: 32, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [{
          type: 'bar', barMaxWidth: 14,
          label: { show: true, position: 'right', color: p.texto2, fontSize: 10, formatter: (it) => pct(it.value, 1) },
          data: d.map((x) => ({ value: x.p_fatia_le_obs, itemStyle: { color: cor[x.grupo] ?? p.texto2, borderRadius: [0, 4, 4, 0] } })),
        }],
      };
    },
  },
};

export const tabelas = {
  'ch04-recalculo': {
    src: 'data/cap04-casos.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'municipio', rotulo: 'Município' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'delta_lula', rotulo: 'Δ Lula', formato: (v) => sinal(v, 0) },
      { chave: 'delta_flavio', rotulo: 'Δ Flávio', formato: (v) => sinal(v, 0) },
      { chave: 'eliminados_1', rotulo: 'Eliminados (1º t.)', formato: 'num' },
      { chave: 'delta_comp', rotulo: 'Δ comparec.', formato: (v) => sinal(v, 0) },
      { chave: 'osc_flavio_finalistas', rotulo: 'Oscilação de Flávio', formato: 'pp' },
      { chave: 'confere', rotulo: 'Confere c/ alegação', formato: (v) => (v ? 'sim' : 'não') },
      { chave: 'residuo_r_2t', rotulo: 'Resíduo R (2º t.)', formato: 'num' },
    ],
  },
  'ch04-contexto': {
    src: 'data/cap04-contexto.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'municipio', rotulo: 'Município' },
      { chave: 'osc_f', rotulo: 'Oscilação de Flávio', formato: 'pp' },
      { chave: 'pct_nacional', rotulo: 'Percentil no país', formato: (v) => num(v, 1) },
      { chave: 'pct_rj', rotulo: 'Percentil no RJ', formato: (v) => num(v, 1) },
      { chave: 'pct_gemeos', rotulo: 'Percentil entre 50 gêmeos', formato: (v) => num(v, 0) },
      { chave: 'prev_reg', rotulo: 'Previsto (1º turno)', formato: 'pp' },
      { chave: 'z_reg', rotulo: 'z (região)', formato: 'num2' },
      { chave: 'q_reg', rotulo: 'q FDR (região)', formato: 'num2' },
      { chave: 'z_uf', rotulo: 'z (UF)', formato: 'num2' },
      { chave: 'q_uf', rotulo: 'q FDR (UF)', formato: 'num2' },
    ],
  },
  'ch04-secoes-resumo': {
    src: 'data/cap04-secoes-resumo.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'municipio', rotulo: 'Município' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'secoes_df_pos', rotulo: 'Seções F ↑', formato: 'num' },
      { chave: 'secoes_df_neg', rotulo: 'Seções F ↓', formato: 'num' },
      { chave: 'soma_df_pos', rotulo: 'Soma F ↑', formato: (v) => sinal(v, 0) },
      { chave: 'soma_df_neg', rotulo: 'Soma F ↓', formato: (v) => sinal(v, 0) },
      { chave: 'sd_df', rotulo: 'DP de ΔF', formato: 'num1' },
      { chave: 'sd_df_nulo_med', rotulo: 'DP esperado', formato: 'num1' },
      { chave: 'pct_sd_nulo', rotulo: 'Percentil do DP', formato: (v) => num(v, 0) },
      { chave: 'corr_df_dcomp', rotulo: 'Corr. ΔF × Δcomparec.', formato: 'num2' },
      { chave: 'secoes_dl_neg', rotulo: 'Seções L ↓', formato: 'num' },
    ],
  },
  'ch04-logs': {
    src: 'data/cap04-logs.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'grupo', rotulo: 'Grupo' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'pct_ue2020_2022', rotulo: 'Urnas UE2020/2022', formato: 'pct1' },
      { chave: 'alertas_med', rotulo: 'Alertas/seção', formato: 'num1' },
      { chave: 'erros_med', rotulo: 'Erros/seção', formato: 'num2' },
      { chave: 'biom_sh_1', rotulo: 'Sem biometria, 1º t.', formato: 'pct' },
      { chave: 'biom_sh_2', rotulo: 'Sem biometria, 2º t.', formato: 'pct' },
      { chave: 'pct_enc_pos_1705', rotulo: 'Encerrou após 17h05', formato: 'pct1' },
      { chave: 'votos_log_menos_comp', rotulo: 'Votos no log − comparec.', formato: 'num' },
    ],
  },
  'ch04-top': {
    src: 'data/cap04-top-nacional.json', porPagina: 0, filtro: false,
    colunas: [
      { chave: 'municipio', rotulo: 'Município' },
      { chave: 'uf', rotulo: 'UF' },
      { chave: 'aptos', rotulo: 'Eleitores', formato: 'num' },
      { chave: 'fatia_f_1t', rotulo: 'Flávio, 1º t.', formato: 'pct1' },
      { chave: 'osc_f', rotulo: 'Oscilação', formato: 'pp' },
      { chave: 'prev', rotulo: 'Previsto', formato: 'pp' },
      { chave: 'z_reg', rotulo: 'z', formato: 'num2' },
      { chave: 'q_reg', rotulo: 'q FDR', formato: (v) => (v < 0.001 ? '< 0,001' : num(v, 3)) },
    ],
  },
};
