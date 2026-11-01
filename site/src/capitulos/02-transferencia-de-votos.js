/**
 * Capítulo 3: para onde foram os eleitores de Cury, Renan, Caiado e Zema.
 * Dados: site/public/data/cap03-*.json, gerados por analises/03_transferencia.py.
 * Contrato: veja site/CONTRIBUTING-CAPITULOS.md.
 */
import { pct, pp, num, compacto } from '../lib/formato.js';
import { carregarJSON } from '../lib/dados.js';
import { criarSimulador } from '../components/simulador.js';

/* ---------- utilidades ---------- */
const DEST = [
  { chave: 'lula', nome: 'Lula (2º turno)', cor: 'lula' },
  { chave: 'flavio', nome: 'Flávio (2º turno)', cor: 'flavio' },
  { chave: 'bn', nome: 'Branco/nulo (2º turno)', cor: 'brancos' },
  { chave: 'abst', nome: 'Abstenção (2º turno)', cor: 'abstencao' },
];
const corOrigem = (chave, p) => ({
  lula_1: p.lula, flavio_1: p.flavio, bn_1: p.brancos, abst_1: p.abstencao,
}[chave] ?? p.texto3);

/** Barra de intervalo horizontal (custom series): dados [lo, hi, indiceCategoria]. */
function serieIntervalo(nome, dados, cor) {
  return {
    name: nome,
    type: 'custom',
    silent: true,
    tooltip: { show: false },
    renderItem: (params, api) => {
      const a = api.coord([api.value(0), api.value(2)]);
      const b = api.coord([api.value(1), api.value(2)]);
      return {
        type: 'group',
        children: [
          { type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: { stroke: cor, lineWidth: 2 } },
          { type: 'line', shape: { x1: a[0], y1: a[1] - 5, x2: a[0], y2: a[1] + 5 }, style: { stroke: cor, lineWidth: 2 } },
          { type: 'line', shape: { x1: b[0], y1: b[1] - 5, x2: b[0], y2: b[1] + 5 }, style: { stroke: cor, lineWidth: 2 } },
        ],
      };
    },
    encode: { x: [0, 1], y: 2 },
    data: dados,
    z: 1,
  };
}

/* ---------- gráficos ---------- */
export const graficos = {
  /* Sankey da matriz estimada */
  'cap03-sankey': {
    opcao: async (json, p, { largura }) => {
      const estreito = largura < 560;
      const linhas = json.dados;
      const nodes = [
        ...linhas.map((l) => ({ name: `${l.origem} (1º)`, itemStyle: { color: corOrigem(l.chave, p) } })),
        ...DEST.map((d) => ({ name: d.nome, itemStyle: { color: p[d.cor] } })),
      ];
      const links = [];
      for (const l of linhas) {
        for (const d of DEST) {
          const v = l[`votos_${d.chave}`];
          if (v < 30000) continue;
          links.push({ source: `${l.origem} (1º)`, target: d.nome, value: v, taxa: l[`para_${d.chave}`] });
        }
      }
      return {
        tooltip: {
          trigger: 'item',
          formatter: (x) => (x.dataType === 'edge'
            ? `${x.data.source} → ${x.data.target}<br><b>${compacto(x.data.value)}</b> votos (${pct(x.data.taxa, 1)} da origem)`
            : `${x.name}<br><b>${num(x.value)}</b> eleitores`),
        },
        series: [{
          type: 'sankey',
          left: 4,
          right: estreito ? 90 : 150,
          top: 8,
          bottom: 8,
          nodeWidth: 12,
          nodeGap: estreito ? 6 : 10,
          nodeAlign: 'justify',
          layoutIterations: 0,
          draggable: false,
          emphasis: { focus: 'adjacency' },
          label: { color: p.texto1, fontSize: estreito ? 10 : 12, fontFamily: p.fonteUi,
            formatter: estreito ? (x) => x.name.replace(' (2º turno)', ' (2º)') : undefined },
          lineStyle: { color: 'source', opacity: 0.32, curveness: 0.5 },
          data: nodes,
          links,
        }],
      };
    },
  },

  /* Pesquisas verificadas × dados, por candidato (dot plot com IC) */
  'cap03-pesquisas': {
    opcao: (json, p, { largura }) => {
      const ind = json.dados;
      const cats = ind.map((i) => i.indicador);
      const estreito = largura < 560;
      return {
        legend: { data: ['Pesquisas verificadas', 'Dados oficiais (inferência ecológica)'] },
        grid: { top: 40, left: 8, right: 24, bottom: 30 },
        tooltip: { trigger: 'item', formatter: (x) => `${x.data[3] ?? x.seriesName}<br>${cats[x.data[1]]}: <b>${pct(x.data[0], 1)}</b> para Flávio` },
        xAxis: { type: 'value', min: 0.2, max: 1, name: estreito ? 'Fração para Flávio (%)' : 'Fração que votou em Flávio (% de quem escolheu um finalista)', nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pct(v, 0) } },
        yAxis: { type: 'category', data: cats, inverse: true,
          axisLabel: { width: estreito ? 90 : 160, overflow: 'break' } },
        series: [
          serieIntervalo('IC', ind.map((i, k) => [i.lo, i.hi, k]), p.texto1),
          {
            name: 'Pesquisas verificadas', type: 'scatter', symbol: 'diamond', symbolSize: 12,
            itemStyle: { color: p.sup0, borderColor: p.texto2, borderWidth: 2 },
            data: ind.flatMap((i, k) => i.pesquisas.map((q) => [q.valor, k, null, q.nome])),
            z: 3,
          },
          {
            name: 'Dados oficiais (inferência ecológica)', type: 'scatter', symbolSize: 11,
            itemStyle: { color: p.texto1, borderColor: p.sup0, borderWidth: 2 },
            data: ind.map((i, k) => [i.dados, k, null, 'Inferência ecológica (IC 95% bootstrap)']),
            z: 4,
          },
        ],
      };
    },
  },

  /* Robustez entre modelos + 2022 */
  'cap03-modelos': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const cats = d.map((x) => x.modelo);
      const estreito = largura < 560;
      const ic = d.map((x, k) => (x.elim_dir_entre_validos_lo != null
        ? [x.elim_dir_entre_validos_lo, x.elim_dir_entre_validos_hi, k] : null)).filter(Boolean);
      return {
        legend: { data: ['Eliminados → candidato da direita (entre quem escolheu)', 'Retenção do candidato da direita'] },
        grid: { top: 48, left: 8, right: 24, bottom: 30 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.5 } },
          valueFormatter: (v) => pct(v, 1) },
        xAxis: { type: 'value', min: 0, max: 1, name: estreito ? 'Fração (%)' : 'Fração estimada, por modelo (%)', nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pct(v, 0) } },
        yAxis: { type: 'category', data: cats, inverse: true, axisLabel: { width: estreito ? 120 : 260, overflow: 'break' } },
        series: [
          serieIntervalo('IC', ic, p.texto2),
          { name: 'Eliminados → candidato da direita (entre quem escolheu)', type: 'scatter', symbolSize: 11,
            itemStyle: { color: p.flavio, borderColor: p.sup0, borderWidth: 2 }, data: d.map((x) => x.elim_dir_entre_validos), z: 3 },
          { name: 'Retenção do candidato da direita', type: 'scatter', symbol: 'diamond', symbolSize: 11,
            itemStyle: { color: p.sup0, borderColor: p.flavio, borderWidth: 2 }, data: d.map((x) => x.ret_dir), z: 3 },
        ],
      };
    },
  },

  /* Cada eliminado: Brasil × UF onde foi mais forte */
  'cap03-candidatos': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const cats = d.map((x) => `${x.candidato} — ${x.recorte === 'Brasil' ? 'Brasil' : `${x.recorte} (${pct(x.share_validos, 1)} dos válidos)`}`);
      const s = [
        { chave: 'lula', nome: 'Foi para Lula', cor: p.lula },
        { chave: 'flavio', nome: 'Foi para Flávio', cor: p.flavio },
        { chave: 'fora', nome: 'Branco, nulo ou abstenção', cor: p.abstencao },
      ];
      return {
        legend: { data: s.map((x) => x.nome) },
        grid: { top: 40, left: 8, right: 16, bottom: 30 },
        tooltip: {
          trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.5 } },
          formatter: (ps) => {
            const x = d[ps[0].dataIndex];
            return `<b>${cats[ps[0].dataIndex]}</b> (${compacto(x.votos)} votos)<br>`
              + `Lula ${pct(x.lula, 1)} (IC ${pct(x.lula_lo, 0)}–${pct(x.lula_hi, 0)})<br>`
              + `Flávio ${pct(x.flavio, 1)} (IC ${pct(x.flavio_lo, 0)}–${pct(x.flavio_hi, 0)})<br>`
              + `Fora ${pct(x.fora, 1)}`;
          },
        },
        xAxis: { type: 'value', max: 1, name: 'Destino dos eleitores do eliminado (%)', nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pct(v, 0) } },
        yAxis: { type: 'category', data: cats, inverse: true, axisLabel: { width: largura < 560 ? 110 : 240, overflow: 'break' } },
        series: s.map((x) => ({
          name: x.nome, type: 'bar', stack: 't', barMaxWidth: 22,
          itemStyle: { color: x.cor, borderColor: p.sup0, borderWidth: 1 },
          data: d.map((r) => r[x.chave]),
        })),
      };
    },
  },

  /* Regiões */
  'cap03-regioes': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const cats = d.map((x) => x.regiao);
      const ser = [
        { nome: 'Eliminados → Flávio (entre quem escolheu)', k: 'elim_dir_entre_validos', cor: p.flavio, simb: 'circle' },
        { nome: 'Novos votantes válidos → Lula', k: 'novos_lula_entre_validos', cor: p.lula, simb: 'circle' },
      ];
      return {
        legend: { data: ser.map((s) => s.nome) },
        grid: { top: 48, left: 8, right: 24, bottom: 30 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.5 } },
          valueFormatter: (v) => pct(v, 1) },
        xAxis: { type: 'value', min: 0, max: 1, name: 'Fração estimada que votou no candidato indicado (%)', nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pct(v, 0) } },
        yAxis: { type: 'category', data: cats, inverse: true },
        series: [
          ...ser.map((s) => serieIntervalo(`IC ${s.nome}`, d.map((x, i) => [x[`${s.k}_lo`], x[`${s.k}_hi`], i]), s.cor)),
          ...ser.map((s) => ({ name: s.nome, type: 'scatter', symbolSize: 11,
            itemStyle: { color: s.cor, borderColor: p.sup0, borderWidth: 2 }, data: d.map((x) => x[s.k]), z: 3 })),
        ],
      };
    },
  },

  /* Goiás: experimento natural Caiado */
  'cap03-goias': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const xmax = Math.max(...d.map((x) => x.caiado));
      const reta = (b) => [[0, b[0]], [xmax, b[0] + b[1] * xmax]];
      const tam = (e) => Math.max(5, Math.min(26, Math.sqrt(e) / 14));
      const rg = json.regressao;
      return {
        legend: { data: ['Variação de Lula', 'Variação de Flávio'] },
        grid: { top: 40, left: 22, right: 24, bottom: 30 },
        tooltip: {
          trigger: 'item',
          formatter: (x) => (x.data.nome
            ? `<b>${x.data.nome}</b> (${num(x.data.eleitores)} eleitores)<br>Caiado: ${pct(x.data.value[0], 1)} do eleitorado<br>${x.seriesName}: ${pp(x.data.value[1], 1)} do eleitorado`
            : ''),
        },
        xAxis: { type: 'value', name: largura < 560 ? 'Caiado no 1º turno (% do eleitorado)' : 'Votos de Caiado no 1º turno (% do eleitorado do município)', nameLocation: 'middle', nameGap: 30,
          axisLabel: { formatter: (v) => pct(v, 0) } },
        yAxis: { type: 'value', name: largura < 560 ? 'Variação (p.p.)' : 'Variação entre turnos (p.p. do eleitorado)', nameLocation: 'middle', nameGap: 62, axisLabel: { formatter: (v) => pp(v, 0) } },
        series: [
          ...[['Variação de Lula', 'd_lula', p.lula], ['Variação de Flávio', 'd_flavio', p.flavio]].flatMap(([nome, k, cor]) => [
            { name: nome, type: 'scatter', itemStyle: { color: cor, opacity: 0.55, borderColor: p.sup0, borderWidth: 1 },
              symbolSize: (v, x) => tam(x.data.eleitores),
              data: d.map((m) => ({ value: [m.caiado, m[k]], nome: m.municipio, eleitores: m.eleitores })) },
            { name: nome, type: 'line', showSymbol: false, silent: true, lineStyle: { color: cor, width: 2 },
              data: reta(rg[k]), tooltip: { show: false },
              endLabel: { show: largura >= 560, color: p.texto2, formatter: () => `inclinação ${num(rg[k][1], 2)}` } },
          ]),
        ],
      };
    },
  },

  /* Mapa de viabilidade */
  'cap03-viabilidade': {
    opcao: (json, p, { largura }) => {
      const g = json.dados;
      const dx = 0.01;
      const dy = 0.0025;
      const lim = 0.05;
      const estreito = largura < 560;
      return {
        legend: { data: ['Pesquisas', 'Inferência ecológica', 'Resultado oficial reproduzido'], top: 0 },
        grid: { top: 40, left: 20, right: estreito ? 16 : 90, bottom: estreito ? 96 : 40 },
        tooltip: {
          trigger: 'item',
          formatter: (x) => {
            if (x.seriesName === 'mapa') {
              const [a, b, dif, sp] = x.data;
              return `Eliminados → Flávio ${pct(a, 0)} · retenção de Flávio ${pct(b, 2)}<br>`
                + `Lula previsto − oficial: <b>${pp(dif, 2)}</b><br>`
                + `Para bater o oficial, Lula precisaria de ${pct(sp, 1)} dos novos votantes válidos`;
            }
            if (x.data?.nome) return `<b>${x.data.nome}</b><br>Lula previsto ${pct(x.data.lula, 2)} (erro ${pp(x.data.erro, 2)})`;
            return '';
          },
        },
        visualMap: {
          type: 'continuous', dimension: 2, seriesIndex: 0, min: -lim, max: lim, calculable: false,
          inRange: { color: p.divergente },
          orient: estreito ? 'horizontal' : 'vertical', right: 0, top: estreito ? undefined : 'middle', bottom: estreito ? 0 : undefined,
          left: estreito ? 'center' : undefined,
          text: estreito ? ['Lula acima', 'Flávio acima'] : ['Lula acima do oficial', 'Flávio acima do oficial'],
          textStyle: { color: p.texto2, fontSize: 11 },
          formatter: (v) => pp(v, 0),
          itemHeight: estreito ? 100 : 180,
        },
        xAxis: { type: 'value', min: 0.295, max: 0.805, name: estreito ? 'Eliminados → Flávio (%)' : 'Eleitores dos eliminados que votam em Flávio (% de quem escolheu um finalista)',
          nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pct(v, 0) } },
        yAxis: { type: 'value', min: 0.87875, max: 1.00125, name: 'Retenção de Flávio (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [
          {
            name: 'mapa', type: 'custom',
            renderItem: (params, api) => {
              const a = api.coord([api.value(0) - dx / 2, api.value(1) + dy / 2]);
              const b = api.coord([api.value(0) + dx / 2, api.value(1) - dy / 2]);
              return { type: 'rect', shape: { x: a[0], y: a[1], width: b[0] - a[0] + 0.5, height: b[1] - a[1] + 0.5 },
                style: { fill: api.visual('color') } };
            },
            encode: { x: 0, y: 1 },
            data: g.map((c) => [c.x, c.y, Math.max(-lim, Math.min(lim, c.dif)), c.sP_necessario]),
            z: 1,
          },
          {
            name: 'Resultado oficial reproduzido', type: 'line', showSymbol: false, smooth: true,
            lineStyle: { color: p.texto1, width: 2, type: 'dashed' }, itemStyle: { color: p.texto1 },
            data: json.curva.map((c) => [c.x, c.y]), z: 3, silent: true,
          },
          {
            name: 'Pesquisas', type: 'scatter', symbol: 'diamond', symbolSize: 14,
            itemStyle: { color: p.sup0, borderColor: p.texto1, borderWidth: 2 },
            label: { show: !estreito, position: 'right', color: p.texto1, fontSize: 11, formatter: (x) => x.data.curto },
            data: json.pontos.filter((x) => !x.cenario.startsWith('Inferência')).map((x, i) => ({
              value: [x.x, Math.min(x.y, 1)], nome: x.cenario, lula: x.lula_previsto, erro: x.erro_pp,
              curto: x.cenario.split(' (')[0], label: { position: i === 0 ? 'top' : 'bottom' } })),
            z: 4,
          },
          {
            name: 'Inferência ecológica', type: 'scatter', symbolSize: 14,
            itemStyle: { color: p.texto1, borderColor: p.sup0, borderWidth: 2 },
            label: { show: !estreito, position: 'left', color: p.texto1, fontSize: 11, formatter: 'Dados (IE)' },
            data: json.pontos.filter((x) => x.cenario.startsWith('Inferência')).map((x) => ({
              value: [x.x, Math.min(x.y, 1)], nome: x.cenario, lula: x.lula_previsto, erro: x.erro_pp })),
            z: 4,
          },
        ],
      };
    },
  },
};

/* ---------- tabelas ---------- */
const ic = (k) => (l) => `${pct(l[k], 1)} <small>(${pct(l[`${k}_lo`], 1)}–${pct(l[`${k}_hi`], 1)})</small>`;
export const tabelas = {
  'cap03-tab-matriz': {
    src: 'data/cap03-matriz.json',
    legenda: 'Matriz de transição estimada, 2026 (fração de cada origem; IC 95% entre parênteses)',
    porPagina: 0,
    colunas: [
      { chave: 'origem', rotulo: 'Origem (1º turno)' },
      { chave: 'votos_origem', rotulo: 'Eleitores', formato: 'compacto' },
      { chave: 'para_lula', rotulo: '→ Lula', html: ic('para_lula'), numerica: true },
      { chave: 'para_flavio', rotulo: '→ Flávio', html: ic('para_flavio'), numerica: true },
      { chave: 'para_bn', rotulo: '→ Branco/nulo', html: ic('para_bn'), numerica: true },
      { chave: 'para_abst', rotulo: '→ Abstenção', html: ic('para_abst'), numerica: true },
    ],
  },
  'cap03-tab-2022': {
    src: 'data/cap03-matriz-2022.json',
    legenda: 'Linha de base: matriz estimada de 2022 com o mesmo método (nível municipal)',
    porPagina: 0,
    colunas: [
      { chave: 'origem', rotulo: 'Origem (1º turno 2022)' },
      { chave: 'votos_origem', rotulo: 'Eleitores', formato: 'compacto' },
      { chave: 'para_lula', rotulo: '→ Lula', html: ic('para_lula'), numerica: true },
      { chave: 'para_bolsonaro', rotulo: '→ Bolsonaro', html: ic('para_bolsonaro'), numerica: true },
      { chave: 'para_bn', rotulo: '→ Branco/nulo', html: ic('para_bn'), numerica: true },
      { chave: 'para_abst', rotulo: '→ Abstenção', html: ic('para_abst'), numerica: true },
    ],
  },
  'cap03-tab-ufs': {
    src: 'data/cap03-ufs.json',
    legenda: 'Ajuste separado por UF (2026)',
    porPagina: 0,
    filtro: true,
    ordem: { chave: 'ret_dir', direcao: 'asc' },
    colunas: [
      { chave: 'uf', rotulo: 'UF' },
      { chave: 'ret_dir', rotulo: 'Retenção Flávio', formato: 'pct1' },
      { chave: 'dir_para_lula', rotulo: 'Flávio → Lula', formato: 'pct1' },
      { chave: 'ret_lula', rotulo: 'Retenção Lula', formato: 'pct1' },
      { chave: 'elim_dir_entre_validos', rotulo: 'Eliminados → Flávio (entre válidos)', formato: 'pct1' },
      { chave: 'novos_lula_entre_validos', rotulo: 'Novos votantes → Lula', formato: 'pct1' },
      { chave: 'caiado_share', rotulo: 'Caiado, % válidos', formato: 'pct1' },
      { chave: 'caiado_flavio', rotulo: 'Caiado → Flávio', formato: 'pct1' },
    ],
  },
};

/* ---------- simulador (montado à mão para ter botões de cenário) ---------- */
const ELIM = [
  { id: 'cury', nome: 'Cury' }, { id: 'renan', nome: 'Renan' }, { id: 'caiado', nome: 'Caiado' },
  { id: 'zema', nome: 'Zema' }, { id: 'menores', nome: 'demais candidatos' },
];

function medias(v) {
  const m = {
    lula: [v.retL, (1 - v.retL) * v.troca, (1 - v.retL) * (1 - v.troca)],
    flavio: [(1 - v.retF) * v.troca, v.retF, (1 - v.retF) * (1 - v.troca)],
    bn: [v.bnV * v.bnL, v.bnV * (1 - v.bnL), 1 - v.bnV],
    abst: [v.abV * v.abL, v.abV * (1 - v.abL), 1 - v.abV],
  };
  for (const e of ELIM) m[e.id] = [v.elimV * (1 - v[e.id]), v.elimV * v[e.id], 1 - v.elimV];
  return m;
}

/** Ajusta a participação dos ex-abstencionistas para que o total de válidos bata com o oficial. */
function calibrarAbstencao(v, sim) {
  const g = sim.grupos;
  const m = medias({ ...v, abV: 0 });
  let validos = 0;
  for (const [k, vet] of Object.entries(m)) validos += g[k] * (vet[0] + vet[1]);
  const alvo = sim.oficial.lula + sim.oficial.flavio;
  return Math.max(0, Math.min(0.3, (alvo - validos) / g.abst));
}

function cenarios(sim) {
  const ei = sim.preset_ei;
  const base = { k: 400 };
  const eco = {
    ...base, retL: ei.retL, retF: ei.retF, troca: ei.trocaF, elimV: ELIM.reduce((s, e) => s + ei.elim[e.id].valido * sim.grupos[e.id], 0)
      / ELIM.reduce((s, e) => s + sim.grupos[e.id], 0),
    bnV: ei.bnValido, bnL: ei.bnLula, abV: ei.abstValido, abL: ei.abstLula,
    ...Object.fromEntries(ELIM.map((e) => [e.id, ei.elim[e.id].flavio])),
  };
  // Para comparar as pesquisas entre si, usamos a retenção estimada pelos dados (só a Quaest de 22/10 publicou uma
  // retenção declarada) e, para os novos votantes, o cabeçalho (válidos) da própria pesquisa, ou, na Quaest de 22/10,
  // o cruzamento de quem diz ter faltado ou votado branco/nulo (40% Lula × 36% Flávio).
  const pesquisa = (elimV, fr, lulaNovos) => {
    const v = { ...base, retL: ei.retL, retF: ei.retF, troca: ei.trocaF, elimV, bnV: ei.bnValido, bnL: lulaNovos, abL: lulaNovos, ...fr };
    return { ...v, abV: calibrarAbstencao(v, sim) };
  };
  // Quaest 17–20/10 por candidato (Cury 48 L × 33 F; Renan 25 × 51; Caiado 21 × 57); Zema não publicado (usa Caiado);
  // demais = média ponderada (58% Flávio). 78,6% dos eleitores desses três votam em um finalista.
  const quaest = pesquisa(0.786, { cury: 33 / 81, renan: 51 / 76, caiado: 57 / 78, zema: 57 / 78, menores: 0.581 }, 0.494);
  // Datafolha 06–07/10 (divulgado 08/10): eliminados 46% Flávio × 32% Lula × 15% branco/nulo.
  const datafolha = pesquisa(0.78, Object.fromEntries(ELIM.map((e) => [e.id, 46 / 78])), 0.48);
  // Quaest divulgada em 22/10: eliminados 43% Flávio × 37% Lula (agregado, sem divisão por candidato).
  const quaest22 = pesquisa(0.80, Object.fromEntries(ELIM.map((e) => [e.id, 43 / 80])), 40 / 76);
  const tese = { ...base, retL: 0.99, retF: 0.99, troca: 0, elimV: 0.85, bnV: ei.bnValido, bnL: 0.5, abL: 0.5,
    cury: 0.6, renan: 0.8, caiado: 0.9, zema: 0.9, menores: 0.5 };
  tese.abV = calibrarAbstencao(tese, sim);
  return [
    { nome: 'Inferência ecológica (dados)', v: eco },
    { nome: 'Quaest 17–20/10', v: quaest },
    { nome: 'Datafolha 06–07/10', v: datafolha },
    { nome: 'Quaest 22/10', v: quaest22 },
    { nome: 'Premissa da tese', v: tese },
  ];
}

async function montarSimulador(alvo) {
  const sim = await carregarJSON('data/cap03-sim.json');
  const cs = cenarios(sim);
  const ini = cs[1].v;
  const ctl = (id, rotulo, min, max, passo, ajuda) => ({ id, rotulo, min, max, passo, valor: ini[id], formato: 'pct1', ajuda });
  const controles = [
    ctl('retL', 'Retenção de Lula', 0.85, 1, 0.0025, 'Fração dos eleitores de Lula no 1º turno que votam nele de novo.'),
    ctl('retF', 'Retenção de Flávio', 0.85, 1, 0.0025, 'Fração dos eleitores de Flávio no 1º turno que votam nele de novo.'),
    ctl('troca', 'Quem abandona o seu candidato vai para o adversário', 0, 1, 0.01,
      'O resto de quem não é retido vota branco, nulo ou se abstém.'),
    ctl('elimV', 'Eleitores dos eliminados que votam válido', 0.4, 1, 0.01),
    ...ELIM.map((e) => ctl(e.id, `${e.nome}: parcela que vai para Flávio`, 0, 1, 0.01,
      e.id === 'cury' ? 'Entre os eleitores do eliminado que votaram em Lula ou Flávio.' : undefined)),
    ctl('bnV', 'Brancos/nulos do 1º turno que votam válido', 0, 1, 0.01),
    ctl('bnL', 'Desses, parcela que vai para Lula', 0, 1, 0.01),
    ctl('abV', 'Abstencionistas do 1º turno que votam válido', 0, 0.3, 0.0025,
      'Os botões de pesquisa calibram este valor para o total de votos válidos bater com o oficial.'),
    ctl('abL', 'Desses, parcela que vai para Lula', 0, 1, 0.01),
    { id: 'k', rotulo: 'Certeza sobre as taxas', min: 20, max: 3000, passo: 10, valor: ini.k, formato: 'num',
      ajuda: 'Concentração da Dirichlet: maior = taxas verdadeiras mais próximas das escolhidas.' },
  ];

  const barra = document.createElement('div');
  barra.className = 'cap03-cenarios';
  barra.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px;font-family:var(--fonte-ui);font-size:.85rem;color:var(--texto-2)';
  barra.append('Cenários prontos:');
  barra.setAttribute('role', 'group');
  barra.setAttribute('aria-label', 'Cenários prontos');
  const contem = document.createElement('div');
  alvo.append(barra, contem);

  const inst = criarSimulador(contem, {
    titulo: 'Simulador: refaça o 2º turno com as suas premissas',
    subtitulo: 'Distribuição da fatia de Lula nos votos válidos em 20.000 sorteios. Linha cheia: resultado oficial.',
    fonte: 'TSE (totais do 1º turno de 2026); Monte Carlo próprio. Botões de pesquisa: Quaest 17–20/10 (por candidato) e Datafolha 06–07/10; retenção dos finalistas = estimada pelos dados (as pesquisas não a publicaram).',
    tarefa: 'transferencia03',
    altura: 340,
    criarWorker: () => new Worker(new URL('../workers/transferencia.worker.js', import.meta.url), { type: 'module' }),
    controles,
    parametros: (v) => ({ grupos: sim.grupos, medias: medias(v), k: v.k, iteracoes: 20000, semente: 2026, oficial: sim.oficial }),
    opcao: (r, v, p) => ({
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.5 } },
        formatter: (ps) => `Lula com ${pct(ps[0].data[0])} dos válidos<br>${num(ps[0].data[1])} sorteios`,
      },
      grid: { bottom: 40, top: 24, left: 28 },
      xAxis: { type: 'value', scale: true, name: 'Fatia de Lula nos votos válidos (%)', nameLocation: 'middle', nameGap: 30,
        axisLabel: { formatter: (x) => pct(x, 1) } },
      yAxis: { type: 'value', name: 'Frequência (nº de sorteios)', nameLocation: 'middle', nameGap: 14, axisLabel: { show: false } },
      series: [{
        type: 'bar', barWidth: '92%',
        itemStyle: { color: p.sequencial[3], borderRadius: [2, 2, 0, 0] },
        data: r.histograma.map((h) => [h.x, h.n]),
        markLine: {
          symbol: 'none', silent: true,
          data: [
            { xAxis: r.oficial.share_lula, lineStyle: { color: p.texto1, width: 2, type: 'solid' },
              label: { color: p.texto1, formatter: `oficial ${pct(r.oficial.share_lula)}`, position: 'insideEndTop' } },
            { xAxis: 0.5, lineStyle: { color: p.texto3, width: 1, type: 'dashed' },
              label: { color: p.texto3, formatter: '50%', position: 'insideStartTop' } },
          ],
        },
      }],
    }),
    resumo: (r) => {
      const dif = r.oficial.share_lula - r.p50;
      const dl = r.medianaVotos.lula - r.oficial.lula;
      const df = r.medianaVotos.flavio - r.oficial.flavio;
      return `Mediana: Lula ${pct(r.p50)} dos válidos (90% dos sorteios entre ${pct(r.p05)} e ${pct(r.p95)}); `
        + `Lula vence em ${pct(r.probLula, 1)} dos sorteios. O oficial (${pct(r.oficial.share_lula)}) fica ${pp(dif)} `
        + `${dif >= 0 ? 'acima' : 'abaixo'} da mediana; ${pct(r.probAcimaOficial, 1)} dos sorteios dão a Lula pelo menos o oficial. `
        + `Votos na mediana × oficial: Lula ${dl >= 0 ? '+' : '−'}${compacto(Math.abs(dl))}, Flávio ${df >= 0 ? '+' : '−'}${compacto(Math.abs(df))}.`;
    },
  });

  for (const c of cs) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'botao cap03-cenario';
    b.textContent = c.nome;
    b.addEventListener('click', () => {
      barra.querySelectorAll('button').forEach((x) => {
        x.setAttribute('aria-pressed', String(x === b));
        x.style.borderColor = x === b ? 'var(--texto-1)' : '';
      });
      for (const [k, val] of Object.entries(c.v)) inst.definir(k, val);
    });
    if (c === cs[1]) { b.setAttribute('aria-pressed', 'true'); b.style.borderColor = 'var(--texto-1)'; }
    barra.append(b);
  }
}

export function montar(secao) {
  const alvo = secao.querySelector('#cap03-simulador');
  if (alvo) montarSimulador(alvo).catch((e) => { alvo.textContent = `Não foi possível montar o simulador (${e.message}).`; });
}

/* ---------- faixas de votação de Lula: 2026 × 2022 ---------- */
graficos['cap03-faixas'] = {
  opcao: (json, p, { largura }) => {
    const d = json.dados;
    const cats = d.filter((x) => x.ano === 2026).map((x) => x.rotulo);
    const ser = [
      { nome: 'Lula, 2026', ano: 2026, k: 'd_lula', cor: p.lula, tipo: 'solid' },
      { nome: 'Flávio, 2026', ano: 2026, k: 'd_direita', cor: p.flavio, tipo: 'solid' },
      { nome: 'Lula, 2022', ano: 2022, k: 'd_lula', cor: p.lula, tipo: 'dashed' },
      { nome: 'Bolsonaro, 2022', ano: 2022, k: 'd_direita', cor: p.flavio, tipo: 'dashed' },
    ];
    return {
      legend: { data: ser.map((s) => s.nome) },
      grid: { top: largura < 560 ? 100 : 40, left: 20, right: 16, bottom: 40 },
      tooltip: { trigger: 'axis', valueFormatter: (v) => pp(v, 2) },
      xAxis: { type: 'category', data: cats, name: largura < 560 ? 'Fatia de Lula no 1º turno (%)' : 'Faixa de Lula entre os finalistas no 1º turno, por município (%)',
        nameLocation: 'middle', nameGap: 30 },
      yAxis: { type: 'value', name: largura < 560 ? 'Variação (p.p.)' : 'Variação entre turnos (p.p. do eleitorado)', nameLocation: 'middle', nameGap: 56, axisLabel: { formatter: (v) => pp(v, 0) } },
      series: ser.map((s) => ({
        name: s.nome, type: 'line', symbol: 'circle', symbolSize: 8,
        lineStyle: { color: s.cor, width: 2, type: s.tipo }, itemStyle: { color: s.cor },
        data: d.filter((x) => x.ano === s.ano).map((x) => x[s.k]),
      })),
    };
  },
};
graficos['cap03-faixas-bn'] = {
  opcao: (json, p, { largura }) => {
    const d = json.dados;
    const cats = d.filter((x) => x.ano === 2026).map((x) => x.rotulo);
    const ser = [
      { nome: 'Queda de brancos/nulos, 2026', ano: 2026, k: 'queda_bn', cor: p.texto1, tipo: 'solid' },
      { nome: 'Queda de brancos/nulos, 2022', ano: 2022, k: 'queda_bn', cor: p.texto1, tipo: 'dashed' },
      { nome: 'Aumento do comparecimento, 2026', ano: 2026, k: 'd_comparecimento', cor: p.texto3, tipo: 'solid' },
      { nome: 'Aumento do comparecimento, 2022', ano: 2022, k: 'd_comparecimento', cor: p.texto3, tipo: 'dashed' },
    ];
    return {
      legend: { data: ser.map((s) => s.nome) },
      grid: { top: largura < 560 ? 100 : 52, left: 20, right: 16, bottom: 40 },
      tooltip: { trigger: 'axis', valueFormatter: (v) => pp(v, 2) },
      xAxis: { type: 'category', data: cats, name: largura < 560 ? 'Fatia de Lula no 1º turno (%)' : 'Faixa de Lula entre os finalistas no 1º turno, por município (%)',
        nameLocation: 'middle', nameGap: 30 },
      yAxis: { type: 'value', name: largura < 560 ? 'Variação (p.p.)' : 'Variação entre turnos (p.p. do eleitorado)', nameLocation: 'middle', nameGap: 56, axisLabel: { formatter: (v) => pp(v, 1) } },
      series: ser.map((s) => ({
        name: s.nome, type: 'line', symbol: s.tipo === 'solid' ? 'circle' : 'emptyCircle', symbolSize: 8,
        lineStyle: { color: s.cor, width: 2, type: s.tipo }, itemStyle: { color: s.cor },
        data: d.filter((x) => x.ano === s.ano).map((x) => x[s.k]),
      })),
    };
  },
};

tabelas['cap03-tab-poder'] = {
  src: 'data/cap03-poder.json',
  legenda: 'O que a inferência ecológica mostra quando injetamos uma alteração uniforme (reestimação por UF)',
  porPagina: 0,
  colunas: [
    { chave: 'cenario', rotulo: 'Cenário' },
    { chave: 'votos_movidos', rotulo: 'Votos movidos', formato: 'compacto' },
    { chave: 'ret_dir', rotulo: 'Retenção de Flávio', formato: 'pct1' },
    { chave: 'dir_para_lula', rotulo: 'Flávio → Lula', formato: 'pct1' },
    { chave: 'elim_dir_entre_validos', rotulo: 'Eliminados → Flávio (entre válidos)', formato: 'pct1' },
    { chave: 'abst1_lula', rotulo: 'Abstenção → Lula', formato: 'pct1' },
    { chave: 'novos_validos_mi', rotulo: 'Novos válidos (mi)', formato: 'num1' },
  ],
};
