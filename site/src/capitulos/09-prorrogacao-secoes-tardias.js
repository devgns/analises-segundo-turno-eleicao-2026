/**
 * Capítulo 6 — A prorrogação e as seções tardias.
 * Dados: public/data/ch06/*.json, gerados por analises/06_horarios.py.
 */
import { pct, pp, num, compacto } from '../lib/formato.js';
import { carregarJSON } from '../lib/dados.js';
import { criarGrafico } from '../components/grafico.js';

/** minutos desde 0h → "HH:MM" (aceita > 24h, ex.: 1º turno passou da meia-noite). */
const hm = (m) => {
  const h = Math.floor(m / 60) % 24;
  const mm = Math.round(m % 60);
  return `${String(h).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
};
const eixoHora = (min, max, nome = 'Horário (Brasília)', extra = {}) => ({
  type: 'value', min, max, interval: 60, name: nome, nameLocation: 'middle', nameGap: 30,
  axisLabel: { formatter: (v) => hm(v) }, splitLine: { show: false }, ...extra,
});
const cores = (p) => ({
  '2026 · 2º turno': p.texto1,
  '2026 · 1º turno': p.sequencial[3],
  '2022 · 2º turno': p.texto3,
});

const RELOGIOS = {
  ult_voto_b: 'Último voto registrado no log',
  enc2_b: 'Encerramento da seção',
  emis2_b: 'Emissão do BU',
  rec2: 'Recebimento do BU pelo TSE',
};

export const graficos = {
  /** Os quatro relógios do 2º turno: seções por janela de 5 min (Brasília). */
  'ch06-relogios': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const paleta = [p.sequencial[2], p.texto1, p.sequencial[4], p.lula];
      const series = Object.entries(RELOGIOS).map(([k, nome], i) => ({
        name: nome, type: 'line', symbol: 'none', step: 'end',
        lineStyle: { width: 2, color: paleta[i] }, itemStyle: { color: paleta[i] },
        data: d.filter((x) => x.relogio === k && x.minuto_dia >= 960).map((x) => [x.minuto_dia, x.secoes]),
      }));
      return {
        legend: { data: Object.values(RELOGIOS) },
        grid: { top: largura < 560 ? 70 : 44, left: 24, bottom: 46 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'line' },
          formatter: (ps) => `<b>${hm(ps[0].value[0])}–${hm(ps[0].value[0] + 5)}</b><br>`
            + ps.map((x) => `${x.marker}${x.seriesName}: ${num(x.value[1])} seções`).join('<br>') },
        xAxis: eixoHora(960, 1440, 'Horário do evento (Brasília)'),
        yAxis: { type: 'log', min: 1, name: largura < 560 ? 'Seções (log)' : 'Seções por janela de 5 min (escala log)', nameLocation: 'middle', nameGap: 62,
          axisLabel: { formatter: (v) => compacto(v, 0) } },
        series: [
          ...series,
          { type: 'line', data: [], markArea: { silent: true, itemStyle: { color: p.grade, opacity: 0.5 },
            label: { color: p.texto2, fontSize: 11, position: 'insideTop' },
            data: [[{ xAxis: 17 * 60 + 8, name: 'sem recebimento de BUs' }, { xAxis: 19 * 60 + 3 }]] },
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' },
              label: { color: p.texto2, fontSize: 11, formatter: '{b}' },
              data: [{ xAxis: 17 * 60, name: '17h' }, { xAxis: 17 * 60 + 2, name: '' }, { xAxis: 19 * 60, name: '19h' }] } },
        ],
      };
    },
  },

  /** Encerramento: 1º × 2º turno. */
  'ch06-encerramento-turnos': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const s = (k, nome, cor) => ({
        name: nome, type: 'line', symbol: 'none', step: 'end', lineStyle: { width: 2, color: cor }, itemStyle: { color: cor },
        areaStyle: { color: cor, opacity: 0.1 },
        data: d.filter((x) => x.relogio === k && x.minuto_dia >= 1020 && x.minuto_dia <= 1320).map((x) => [x.minuto_dia, x.secoes]),
      });
      return {
        legend: { data: ['1º turno (4/10)', '2º turno (25/10)'] },
        tooltip: { trigger: 'axis', formatter: (ps) => `<b>${hm(ps[0].value[0])}–${hm(ps[0].value[0] + 5)}</b><br>`
          + ps.map((x) => `${x.marker}${x.seriesName}: ${num(x.value[1])} seções`).join('<br>') },
        grid: { left: 20, bottom: 46 },
        xAxis: eixoHora(1020, 1320, 'Horário de encerramento da seção (Brasília)'),
        yAxis: { type: 'log', min: 10, name: largura < 560 ? 'Seções (log)' : 'Seções por janela de 5 min (escala log)', nameLocation: 'middle', nameGap: 62, axisLabel: { formatter: (v) => compacto(v, 0) } },
        series: [s('enc1_b', '1º turno (4/10)', p.sequencial[3]), s('enc2_b', '2º turno (25/10)', p.texto1)],
      };
    },
  },

  /** Votos por minuto 16h30–19h10 e Δ das seções ativas (estudo de evento). */
  'ch06-evento-votos': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      return {
        tooltip: { trigger: 'axis', valueFormatter: (v) => `${num(v)} votos` },
        grid: { left: 20, bottom: 46 },
        xAxis: { type: 'category', data: d.map((x) => x.hora), name: 'Horário do voto (Brasília)', nameLocation: 'middle', nameGap: 30, axisLabel: { interval: 29 } },
        yAxis: { type: 'log', min: 1, name: largura < 560 ? 'Votos/min (log)' : 'Votos por minuto (escala log)', nameLocation: 'middle', nameGap: 62,
          axisLabel: { formatter: (v) => compacto(v, 0) } },
        series: [{ name: 'Votos computados', type: 'bar', barMaxWidth: 24, itemStyle: { color: p.sequencial[3] },
          data: d.map((x) => x.votos),
          markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' },
            label: { color: p.texto2, fontSize: 11, formatter: '{b}' },
            data: [{ xAxis: '17:00', name: '17h00', label: { show: false } }, { xAxis: '17:02', name: 'decisão 17h02', label: { position: 'insideEndTop' } }] } }],
      };
    },
  },
  'ch06-evento-delta': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.filter((x) => x.votos >= 20);
      return {
        legend: { data: ['Lula no 2º turno (estimado)', 'Lula no 1º turno, mesmas seções'] },
        tooltip: { trigger: 'axis', formatter: (ps) => {
          const r = d[ps[0].dataIndex];
          return `<b>${r.hora}</b> · ${num(r.votos)} votos<br>${ps.map((x) => `${x.marker}${x.seriesName}: ${pct(x.value, 1)}`).join('<br>')}`
            + `<br>Δ entre turnos: ${pp(r.delta)}`;
        } },
        grid: { left: 20, bottom: 46 },
        xAxis: { type: 'category', data: d.map((x) => x.hora), name: 'Horário do voto (Brasília)', nameLocation: 'middle', nameGap: 30, axisLabel: { interval: 29 } },
        yAxis: { type: 'value', min: 0.4, max: 0.7, name: largura < 560 ? 'Fatia de Lula (%)' : 'Fatia de Lula entre os finalistas (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [
          { name: 'Lula no 2º turno (estimado)', type: 'line', symbol: 'none', lineStyle: { width: 2, color: p.lula },
            itemStyle: { color: p.lula }, data: d.map((x) => x.lula_2t_est),
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' },
              label: { color: p.texto2, fontSize: 11, formatter: '{b}' }, data: [{ xAxis: '17:02', name: '17h02' }] } },
          { name: 'Lula no 1º turno, mesmas seções', type: 'line', symbol: 'none', lineStyle: { width: 2, color: p.lulaClaro, type: 'dashed' },
            itemStyle: { color: p.lulaClaro }, data: d.map((x) => x.lula_1t_mesmas) },
        ],
      };
    },
  },

  /** Perfil por faixa de encerramento: fatia de Lula 1T × 2T. */
  'ch06-composicao': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.filter((x) => x.faixa !== 'antes das 17h');
      return {
        legend: { data: ['1º turno', '2º turno'] },
        grid: { left: 20, bottom: largura < 560 ? 64 : 46 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.5 } },
          formatter: (ps) => {
            const r = d[ps[0].dataIndex];
            return `<b>Encerradas ${r.faixa}</b><br>${num(r.secoes)} seções · ${pct(r.frac_capital, 0)} em capitais`
              + `<br>${ps.map((x) => `${x.marker}Lula, ${x.seriesName}: ${pct(x.value, 1)}`).join('<br>')}<br>Δ: ${pp(r.delta)}`;
          } },
        xAxis: { type: 'category', data: d.map((x) => x.faixa), name: largura < 560 ? 'Encerramento da seção' : 'Faixa de encerramento da seção (Brasília)', nameLocation: 'middle', nameGap: largura < 560 ? 48 : 30, axisLabel: { interval: 0, rotate: largura < 560 ? 40 : 0 } },
        yAxis: { type: 'value', min: 0.4, max: 0.62, name: largura < 560 ? 'Fatia de Lula (%)' : 'Fatia de Lula entre os finalistas (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [
          { name: '1º turno', type: 'bar', barMaxWidth: 24, barGap: '20%', itemStyle: { color: p.lulaClaro, borderRadius: [4, 4, 0, 0] },
            data: d.map((x) => x.lula_1t) },
          { name: '2º turno', type: 'bar', barMaxWidth: 24, itemStyle: { color: p.lula, borderRadius: [4, 4, 0, 0] },
            data: d.map((x) => x.lula_2t),
            label: { show: largura >= 560, position: 'top', color: p.texto2, fontSize: 11,
              formatter: ({ dataIndex }) => pp(d[dataIndex].delta, 1) } },
        ],
      };
    },
  },

  /** Diferenças em diferenças com IC 95%. */
  'ch06-did': {
    opcao: (json, p, { largura }) => {
      const grupos = [
        ['Encerramento no 2º turno', 'ajustado', 'Relógio do 2º turno (ajustado)', p.texto1],
        ['Encerramento no 2º turno', 'bruto', 'Relógio do 2º turno (bruto)', p.texto3],
        ['Encerramento no 1º turno', 'ajustado', 'Relógio do 1º turno — placebo (ajustado)', p.sequencial[3]],
      ];
      const faixas = ['17h01', '17h02–04', '17h05–09', '17h10–29', '17h30–59', '18h00–59', '19h ou depois'];
      const desloc = [-0.22, 0, 0.22];
      const series = grupos.flatMap(([rel, aj, nome, cor], gi) => {
        const pts = faixas.map((f, i) => {
          const r = json.dados.find((x) => x.relogio === rel && x.ajuste === aj && x.faixa === f);
          return r ? { i, ...r } : null;
        }).filter(Boolean);
        return [
          { name: nome, type: 'scatter', symbolSize: 9, itemStyle: { color: cor }, z: 3,
            data: pts.map((r) => ({ value: [r.i + desloc[gi], r.coef], r })) },
          { name: nome, type: 'custom', silent: true, z: 2,
            renderItem: (params, api) => {
              const a = api.coord([api.value(0), api.value(1)]);
              const b = api.coord([api.value(0), api.value(2)]);
              return { type: 'group', children: [
                { type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: { stroke: cor, lineWidth: 2 } },
                { type: 'line', shape: { x1: a[0] - 4, y1: a[1], x2: a[0] + 4, y2: a[1] }, style: { stroke: cor, lineWidth: 2 } },
                { type: 'line', shape: { x1: b[0] - 4, y1: b[1], x2: b[0] + 4, y2: b[1] }, style: { stroke: cor, lineWidth: 2 } },
              ] };
            },
            data: pts.map((r) => [r.i + desloc[gi], r.ic_inf, r.ic_sup]) },
        ];
      });
      return {
        legend: { data: grupos.map((g) => g[2]) },
        grid: { top: largura < 560 ? 80 : 44, left: 24, bottom: largura < 560 ? 84 : 46 },
        tooltip: { trigger: 'item', formatter: (x) => {
          const r = x.data.r;
          return `<b>${x.seriesName}</b><br>Encerradas ${r.faixa} (${num(r.secoes)} seções)<br>`
            + `Δ a mais que as de 17h00: ${pp(r.coef)}<br>IC 95%: ${pp(r.ic_inf)} a ${pp(r.ic_sup)}<br>p (Holm): ${r.p_holm < 0.001 ? '< 0,001' : num(r.p_holm, 3)}`;
        } },
        xAxis: { type: 'value', min: -1, max: faixas.length, interval: 1, splitLine: { show: false },
          name: largura < 560 ? 'Encerramento da seção' : 'Faixa de encerramento da seção (Brasília)', nameLocation: 'middle', nameGap: largura < 560 ? 62 : 30,
          axisLabel: { formatter: (v) => faixas[v] ?? '', rotate: largura < 560 ? 40 : 0, hideOverlap: false } },
        yAxis: { type: 'value', min: -0.012, max: 0.012, name: largura < 560 ? 'Deslocamento extra (p.p.)' : 'Deslocamento extra para Lula (p.p.)', nameLocation: 'middle', nameGap: 66, axisLabel: { formatter: (v) => pp(v, 1) } },
        series: [
          ...series,
          { type: 'line', data: [], markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3 },
            label: { show: false }, data: [{ yAxis: 0 }] } },
        ],
      };
    },
  },

  /** Curva da apuração: diferença acumulada pelo horário de recebimento. */
  'ch06-curvas': {
    opcao: (json, p, { largura }) => {
      const c = cores(p);
      const nomes = Object.keys(c);
      const infos = Object.fromEntries((json.infos ?? []).map((i) => [i.eleicao, i]));
      return {
        legend: { data: nomes },
        grid: { top: largura < 560 ? 64 : 44, left: 20, bottom: 46 },
        tooltip: { trigger: 'axis', formatter: (ps) => `<b>${hm(ps[0].value[0])}</b><br>`
          + ps.map((x) => `${x.marker}${x.seriesName}: ${x.value[1] >= 0 ? 'Lula' : 'adversário'} à frente por ${num(Math.abs(x.value[1]))} `
            + `(${pct(x.value[2], 1)} dos BUs)`).join('<br>') },
        xAxis: eixoHora(17 * 60, 24 * 60 + 60, largura < 560 ? 'Recebimento do BU (Brasília)' : 'Horário de recebimento do boletim (Brasília)'),
        yAxis: { type: 'value', name: largura < 560 ? 'Lula − adversário (votos)' : 'Vantagem acumulada de Lula (votos)', nameLocation: 'middle', nameGap: 48,
          axisLabel: { formatter: (v) => compacto(v, 0) } },
        series: nomes.map((n) => {
          const v = infos[n]?.virada_hora;
          return {
            name: n, type: 'line', symbol: 'none', showSymbol: false, lineStyle: { width: 2, color: c[n], type: n.startsWith('2022') ? 'dashed' : 'solid' },
            itemStyle: { color: c[n] },
            data: json.dados.filter((x) => x.eleicao === n && x.minuto_dia >= 17 * 60).map((x) => [x.minuto_dia, x.dif, x.frac_secoes]),
            markPoint: v && n !== '2026 · 1º turno' ? { symbol: 'circle', symbolSize: 9, itemStyle: { color: c[n] },
              label: { show: largura >= 560, position: 'bottom', color: p.texto2, fontSize: 11, formatter: `virada ${v}` },
              data: [{ coord: [Number(v.slice(0, 2)) * 60 + Number(v.slice(3, 5)), 0] }] } : undefined,
          };
        }).concat([{ type: 'line', data: [], markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3 }, label: { show: false }, data: [{ yAxis: 0 }] } }]),
      };
    },
  },

  /** BUs recebidos por minuto: a pausa. */
  'ch06-chegadas': {
    opcao: (json, p, { largura }) => {
      const c = cores(p);
      const nomes = Object.keys(c);
      return {
        legend: { data: nomes },
        tooltip: { trigger: 'axis', formatter: (ps) => `<b>${hm(ps[0].value[0])}</b><br>`
          + ps.map((x) => `${x.marker}${x.seriesName}: ${num(x.value[1])} BUs`).join('<br>') },
        grid: { left: 20, bottom: 46 },
        xAxis: eixoHora(17 * 60, 24 * 60 + 60, largura < 560 ? 'Recebimento do BU (Brasília)' : 'Horário de recebimento do boletim (Brasília)'),
        yAxis: { type: 'value', name: largura < 560 ? 'Boletins por minuto' : 'Boletins recebidos por minuto', nameLocation: 'middle', nameGap: 58 },
        series: nomes.map((n) => {
          const pts = json.dados.filter((x) => x.eleicao === n && x.minuto_dia >= 17 * 60);
          // preenche minutos sem chegada com zero (a pausa precisa aparecer como zero, não como linha reta)
          const mapa = new Map(pts.map((x) => [x.minuto_dia, x.bus]));
          const ini = 17 * 60; const fim = Math.min(25 * 60, Math.max(...pts.map((x) => x.minuto_dia)));
          const data = [];
          for (let m = ini; m <= fim; m += 1) data.push([m, mapa.get(m) ?? 0]);
          return { name: n, type: 'line', symbol: 'none', lineStyle: { width: n.startsWith('2026 · 2') ? 2 : 1.5, color: c[n] },
            itemStyle: { color: c[n] }, data,
            markArea: n.startsWith('2026 · 2') ? { silent: true, itemStyle: { color: p.grade, opacity: 0.6 },
              label: { color: p.texto2, fontSize: 11 },
              data: [[{ xAxis: 17 * 60 + 8, name: '115 min sem BU' }, { xAxis: 19 * 60 + 3 }]] } : undefined };
        }),
      };
    },
  },

  /** Fatia de Lula por décimo da ordem de chegada. */
  'ch06-decis': {
    opcao: (json, p, { largura }) => {
      const series = [
        ['2026 · 2º turno', p.texto1, 'solid'],
        ['2026 · mesmas seções do 2º turno, votação do 1º turno', p.sequencial[2], 'dashed'],
        ['2022 · 2º turno', p.texto3, 'dashed'],
      ];
      return {
        legend: { data: series.map((s) => s[0]) },
        grid: { top: 64, left: 20, bottom: 46 },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v, 1) },
        xAxis: { type: 'category', name: 'Décimo dos boletins, por ordem de chegada', nameLocation: 'middle', nameGap: 30,
          data: ['1º', '2º', '3º', '4º', '5º', '6º', '7º', '8º', '9º', '10º'] },
        yAxis: { type: 'value', min: 0.44, max: 0.56, name: largura < 560 ? 'Fatia de Lula (%)' : 'Fatia de Lula entre os finalistas (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: series.map(([n, cor, tipo]) => ({ name: n, type: 'line', symbolSize: 8, lineStyle: { width: 2, color: cor, type: tipo },
          itemStyle: { color: cor }, data: json.dados.filter((x) => x.serie === n).map((x) => x.lula) })),
      };
    },
  },

  /** Votos por faixa de 20 min com divisão estimada. */
  'ch06-horario': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const S = [['lula', 'Lula (estimado)', p.lula], ['flavio', 'Flávio (estimado)', p.flavio],
        ['brancos', 'Brancos', p.brancos], ['nulos', 'Nulos', p.nulos]];
      return {
        legend: { data: S.map((s) => s[1]) },
        grid: { top: largura < 560 ? 60 : 40, left: 20, bottom: 46 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.5 } },
          formatter: (ps) => {
            const r = d[ps[0].dataIndex];
            return `<b>${r.hora} (+20 min)</b> · ${num(r.votos)} votos<br>`
              + ps.map((x) => `${x.marker}${x.seriesName}: ${compacto(x.value)}`).join('<br>')
              + `<br>Lula entre os dois (estimado): ${pct(r.lula_est, 1)} · mesmas seções no 1º turno: ${pct(r.lula_1t_mesmas, 1)}`;
          } },
        xAxis: { type: 'category', data: d.map((x) => x.hora), name: largura < 560 ? 'Horário (Brasília)' : 'Horário do voto, faixas de 20 min (Brasília)', nameLocation: 'middle', nameGap: 30, axisLabel: { interval: 2 } },
        yAxis: { type: 'value', name: 'Votos computados', nameLocation: 'middle', nameGap: 60, axisLabel: { formatter: (v) => compacto(v, 0) } },
        series: S.map(([k, nome, cor], i) => ({ name: nome, type: 'bar', stack: 'v', barMaxWidth: 24,
          itemStyle: { color: cor, borderColor: p.sup0, borderWidth: 1, borderRadius: i === S.length - 1 ? [4, 4, 0, 0] : 0 },
          data: d.map((x) => x[k]) })),
      };
    },
  },

  /** Mapa de calor hora × região. */
  'ch06-calor': {
    opcao: (json, p, { largura }) => {
      const reg = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul'];
      const horas = [...new Set(json.dados.map((x) => x.h))].sort((a, b) => a - b).filter((h) => h <= 17);
      const dados = json.dados.filter((x) => x.h <= 17).map((x) => [horas.indexOf(x.h), reg.indexOf(x.regiao), x.frac_regiao, x]);
      return {
        grid: { top: 8, bottom: 84 },
        tooltip: { formatter: (x) => {
          const r = x.data[3];
          return `<b>${r.regiao}, ${r.h}h–${r.h + 1}h</b><br>${pct(r.frac_regiao, 1)} dos votos da região (${num(r.votos)})`
            + `<br>Lula entre os dois (estimado): ${pct(r.lula_est, 1)}<br>Δ vs 1º turno, mesmas seções: ${pp(r.delta)}`;
        } },
        xAxis: { type: 'category', data: horas.map((h) => `${h}h`), name: 'Hora do dia (Brasília)', nameLocation: 'middle', nameGap: 28, splitArea: { show: false } },
        yAxis: { type: 'category', data: reg },
        visualMap: { min: 0, max: 0.18, calculable: false, orient: 'horizontal', left: 'center', bottom: 0,
          itemWidth: 12, itemHeight: largura < 560 ? 160 : 240, inRange: { color: p.sequencial },
          textStyle: { color: p.texto2 }, formatter: (v) => pct(v, 0) },
        series: [{ type: 'heatmap', data: dados, itemStyle: { borderColor: p.sup0, borderWidth: 2 },
          label: { show: largura >= 560, color: p.texto1, fontSize: 10, formatter: (x) => pct(x.data[2], 0) } }],
      };
    },
  },
};

export const tabelas = {
  'ch06-alegacoes': {
    src: 'data/ch06/alegacoes-circulantes.json',
    porPagina: 0,
    colunas: [
      { chave: 'definicao', rotulo: 'Definição de "encerrada até 17h"' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'comparecimento', rotulo: 'Comparecimento', formato: 'num' },
      { chave: 'flavio_2t_ate', rotulo: 'Flávio, 2º turno', formato: 'pct' },
      { chave: 'flavio_1t_mesmas', rotulo: 'Flávio, 1º turno (mesmas seções)', formato: 'pct' },
      { chave: 'vantagem_lula_demais', rotulo: 'Vantagem de Lula nas demais', formato: 'num' },
    ],
  },
  'ch06-uf': {
    src: 'data/ch06/pos17-uf.json',
    porPagina: 10,
    ordem: { chave: 'votos_pos17', direcao: 'desc' },
    colunas: [
      { chave: 'sg_uf', rotulo: 'UF' },
      { chave: 'votos_pos17', rotulo: 'Votos após 17h', formato: 'num' },
      { chave: 'votos_pos1710', rotulo: 'Após 17h10', formato: 'num' },
      { chave: 'secoes_com_voto_pos17', rotulo: 'Seções com voto após 17h', formato: 'num' },
      { chave: 'frac_pos17', rotulo: '% dos votos da UF', formato: (v) => pct(v, 3) },
      { chave: 'lula_1t_secoes_tardias', rotulo: 'Lula 1T, seções tardias', formato: 'pct1' },
      { chave: 'lula_2t_secoes_tardias', rotulo: 'Lula 2T, seções tardias', formato: 'pct1' },
    ],
  },
  'ch06-secoes': {
    src: 'data/ch06/pos17-secoes-top.json',
    porPagina: 10,
    filtro: true,
    colunas: [
      { chave: 'sg_uf', rotulo: 'UF' },
      { chave: 'nm_municipio', rotulo: 'Município' },
      { chave: 'zona', rotulo: 'Zona' },
      { chave: 'secao', rotulo: 'Seção' },
      { chave: 'n_log', rotulo: 'Votos no log', formato: 'num' },
      { chave: 'n_pos17', rotulo: 'Após 17h', formato: 'num' },
      { chave: 'ultimo_voto', rotulo: 'Último voto' },
      { chave: 'encerramento', rotulo: 'Encerrou' },
      { chave: 's1', rotulo: 'Lula 1T', formato: 'pct1' },
      { chave: 's2', rotulo: 'Lula 2T', formato: 'pct1' },
    ],
  },
};

/** Interativo: escolha o relógio e o corte e veja a "fatia de Flávio até X". */
async function montarCorte(alvo) {
  const json = await carregarJSON('data/ch06/corte-interativo.json');
  const linhas = json.dados;
  const rotulos = [...new Map(linhas.map((x) => [x.relogio, x.rotulo])).entries()];
  alvo.classList.add('simulador');
  alvo.innerHTML = `
    <h3 class="simulador__titulo">"Flávio venceu nas seções fechadas até…": escolha o relógio e a hora</h3>
    <div class="simulador__controles">
      <div class="controle"><label for="ch06-rel"><span>Relógio</span></label>
        <select id="ch06-rel" style="width:100%;min-height:32px;font:inherit;background:var(--sup-0);color:var(--texto-1);border:1px solid var(--borda);border-radius:6px;padding:4px"></select></div>
      <div class="controle"><label for="ch06-hora"><span>Corte (Brasília, exceto o relógio local)</span><output></output></label>
        <input type="range" id="ch06-hora"></div>
      <div class="kpis" style="margin:0;grid-template-columns:1fr 1fr">
        <div class="kpi"><span class="kpi__marca" style="background:var(--flavio)"></span><p class="kpi__rotulo">Flávio no 2º turno, seções até o corte</p><div class="kpi__valor" data-k="f2"></div></div>
        <div class="kpi"><p class="kpi__rotulo">As mesmas seções no 1º turno</p><div class="kpi__valor" data-k="f1"></div></div>
      </div>
      <p class="controle__ajuda" data-k="det"></p>
    </div>
    <div class="simulador__saida"><figure style="margin:0"></figure></div>`;
  const sel = alvo.querySelector('select');
  for (const [k, r] of rotulos) sel.add(new Option(r, k));
  const inp = alvo.querySelector('input');
  const out = alvo.querySelector('output');
  let atual = [];
  let idx = 0;
  const grafico = criarGrafico(alvo.querySelector('figure'), {
    dados: { dados: [] }, altura: 320, tabela: false, csv: false,
    fonte: 'TSE — bweb e logs das urnas, 2026. Fatias entre os dois finalistas.',
    opcao: (j, p) => {
      const d = j.dados;
      if (!d.length) return null;
      return {
        legend: { data: ['Flávio, 2º turno', 'Flávio, 1º turno (mesmas seções)'] },
        tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v, 2) },
        grid: { left: 20, bottom: 46 },
        xAxis: { type: 'category', data: d.map((x) => x.corte), name: 'Corte: seções encerradas até (horário)', nameLocation: 'middle', nameGap: 30, axisLabel: { interval: 'auto' } },
        yAxis: { type: 'value', min: 0.44, max: 0.66, name: 'Fatia de Flávio entre os finalistas (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
        series: [
          { name: 'Flávio, 2º turno', type: 'line', symbol: 'none', lineStyle: { width: 2, color: p.flavio }, itemStyle: { color: p.flavio },
            data: d.map((x) => x.flavio_2t),
            markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, label: { show: false },
              data: [{ xAxis: d[j.idx]?.corte }, { yAxis: 0.5 }] } },
          { name: 'Flávio, 1º turno (mesmas seções)', type: 'line', symbol: 'none', lineStyle: { width: 2, color: p.flavioClaro, type: 'dashed' },
            itemStyle: { color: p.flavioClaro }, data: d.map((x) => x.flavio_1t) },
        ],
      };
    },
  });
  const desenhar = () => {
    const r = atual[idx];
    if (!r) return;
    out.textContent = r.corte;
    alvo.querySelector('[data-k="f2"]').textContent = r.secoes ? pct(r.flavio_2t) : '—';
    alvo.querySelector('[data-k="f1"]').textContent = r.secoes ? pct(r.flavio_1t) : '—';
    alvo.querySelector('[data-k="det"]').textContent = r.secoes
      ? `${num(r.secoes)} seções (${num(r.comparecimento)} eleitores votaram nelas). Nas demais seções, Lula teve ${num(r.vantagem_lula_demais)} votos de vantagem. `
        + `Diferença entre turnos nessas seções: ${pp(r.flavio_2t - r.flavio_1t)} para Flávio.`
      : 'Nenhuma seção marca horário até esse corte neste relógio.';
    grafico.atualizar({ dados: atual, idx });
  };
  const trocar = () => {
    atual = linhas.filter((x) => x.relogio === sel.value && (x.secoes > 0 || x.minuto_dia >= 1020));
    inp.min = 0; inp.max = atual.length - 1; inp.step = 1;
    const alvoMin = sel.value === 'enc2_local' ? 17 * 60 : (sel.value.startsWith('rec') ? 20 * 60 : 17 * 60 + 1);
    idx = Math.max(0, atual.findIndex((x) => x.minuto_dia >= alvoMin));
    inp.value = idx;
    desenhar();
  };
  sel.addEventListener('change', trocar);
  inp.addEventListener('input', () => { idx = Number(inp.value); desenhar(); });
  trocar();
}

export function montar(secao) {
  const alvo = secao.querySelector('[data-ch06-corte]');
  if (alvo) montarCorte(alvo).catch((e) => { alvo.textContent = `Não foi possível carregar o interativo (${e.message}).`; });
}
