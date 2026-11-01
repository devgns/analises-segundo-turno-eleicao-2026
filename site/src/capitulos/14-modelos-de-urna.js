/**
 * Capítulo 8b — Modelos de urna: o padrão de 2022 voltou em 2026?
 * Dados: public/data/ch08b/*.json (gerados por analises/08b_modelos_urna.py).
 * Coeficientes nos JSONs estão em pontos percentuais (não em fração): dividir por 100 antes de pp().
 */
import { pct, pp, num, compacto } from '../lib/formato.js';

const ppp = (v, casas = 2) => (v == null ? '—' : pp(v / 100, casas));
const PORTES = ['< 50 mil', '50–100 mil', '100–500 mil', '≥ 500 mil'];

/** Gráfico de intervalos (forest plot) horizontal. Linhas: {coef, ic_inf, ic_sup} em p.p. */
function floresta(p, linhas, rotulo, { largura, cor = () => p.texto1, tooltip, esquerda = 300, nomeX = 'Diferença (p.p.)' } = {}) {
  const d = linhas.slice().reverse();
  const estreito = largura < 560;
  return {
    grid: { left: 8, right: 24, top: 12, bottom: 50 },
    tooltip: { trigger: 'item', formatter: (it) => tooltip(d[it.dataIndex]) },
    yAxis: { type: 'category', data: d.map(rotulo), axisLabel: { fontSize: estreito ? 10 : 11, width: estreito ? 160 : esquerda - 16, overflow: 'truncate' } },
    xAxis: { type: 'value', axisLabel: { formatter: (v) => ppp(v, 1) }, name: estreito ? 'Diferença (p.p.)' : nomeX, nameLocation: 'middle', nameGap: 30 },
    series: [
      { type: 'custom', silent: true, encode: { x: [1, 2], y: 0 },
        renderItem: (params, api) => {
          const y = api.coord([0, api.value(0)])[1];
          const a = api.coord([api.value(1), 0])[0];
          const b = api.coord([api.value(2), 0])[0];
          return { type: 'line', shape: { x1: a, y1: y, x2: b, y2: y }, style: { stroke: p.texto2, lineWidth: 2 } };
        },
        data: d.map((x, i) => [i, x.ic_inf ?? x.coef, x.ic_sup ?? x.coef]) },
      { type: 'scatter', symbolSize: 10,
        itemStyle: { color: (it) => cor(d[it.dataIndex]), borderColor: p.sup0, borderWidth: 2 },
        data: d.map((x, i) => [x.coef, i]),
        markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed' }, data: [{ xAxis: 0 }], label: { show: false } } },
    ],
  };
}

const tipCoef = (titulo) => (x) => `${titulo(x)}<br>Diferença: <b>${ppp(x.coef)}</b>`
  + `<br>IC 95%: ${ppp(x.ic_inf)} a ${ppp(x.ic_sup)}`
  + (x.p != null ? `<br>p = ${x.p < 0.001 ? '< 0,001' : num(x.p, 3)}` : '')
  + (x.p_holm != null ? ` · p (Holm) = ${num(x.p_holm, 2)}` : '')
  + (x.municipios_ponte != null && x.municipios_ponte < 1e5 ? `<br>Municípios que identificam o contraste: ${num(x.municipios_ponte)}` : '')
  + (x.n ? `<br>n = ${num(x.n)} seções` : '');

/** Votos por intervalo de 5 min de recebimento do BU, antigas × novas (o gráfico do pedronauck). */
function tempo(ano) {
  return {
    opcao: (json, p, { largura }) => {
      // janela da apuração (16h–23h55 de Brasília); descarta poucos BUs com relógio de recebimento fora do dia
      const d = json.dados.filter((x) => x.ano === ano && x.hora >= '16:00');
      const horas = [...new Set(d.map((x) => x.hora))].sort();
      const serie = (grupo, campo) => {
        const m = new Map(d.filter((x) => x.grupo === grupo).map((x) => [x.hora, x[campo]]));
        return horas.map((h) => m.get(h) ?? 0);
      };
      const adv = ano === 2022 ? 'Bolsonaro' : 'Flávio';
      const ant = ano === 2022 ? 'UE2009–2015' : 'UE2013–2015';
      const nov = ano === 2022 ? 'UE2020' : 'UE2020–2022';
      const linha = (name, grupo, campo, cor, tracejada) => ({
        name, type: 'line', showSymbol: false, data: serie(grupo, campo),
        lineStyle: { width: 2, color: cor, type: tracejada ? 'dashed' : 'solid' }, itemStyle: { color: cor },
      });
      return {
        legend: { data: [`Lula · ${ant}`, `Lula · ${nov}`, `${adv} · ${ant}`, `${adv} · ${nov}`] },
        grid: { top: largura < 560 ? 72 : 48, left: 20, bottom: 46 },
        tooltip: { trigger: 'axis', valueFormatter: (v) => `${num(v)} votos` },
        xAxis: { type: 'category', data: horas, name: largura < 560 ? 'Recebimento do BU (Brasília)' : 'Horário de recebimento do boletim (Brasília)', nameLocation: 'middle', nameGap: 30, axisLabel: { interval: largura < 560 ? 11 : 5 } },
        yAxis: { type: 'value', name: largura < 560 ? 'Votos / 5 min' : 'Votos por intervalo de 5 min', nameLocation: 'middle', nameGap: 62, axisLabel: { formatter: (v) => compacto(v) } },
        series: [
          linha(`Lula · ${ant}`, 'antigas', 'lula_2', p.lula, false),
          linha(`Lula · ${nov}`, 'novas', 'lula_2', p.lula, true),
          linha(`${adv} · ${ant}`, 'antigas', 'adv_2', p.flavio, false),
          linha(`${adv} · ${nov}`, 'novas', 'adv_2', p.flavio, true),
        ],
      };
    },
  };
}

export const graficos = {
  'ch08b-tempo-2022': tempo(2022),
  'ch08b-tempo-2026': tempo(2026),

  /** N+NE 2022: número de seções por porte e grupo — o que as contagens de votos medem. */
  'ch08b-porte-secoes': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.filter((x) => x.macro === 'N+NE');
      const v = (g) => PORTES.map((po) => d.find((x) => x.porte === po && x.grupo === g)?.secoes ?? 0);
      return {
        legend: { data: ['UE2009–2015', 'UE2020'] },
        grid: { left: 20, bottom: 52 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (x) => `${num(x)} seções` },
        xAxis: { type: 'category', data: PORTES.map((x) => `${x} votantes`), name: 'Porte do município (votantes no 2º turno)', nameLocation: 'middle', nameGap: 32 },
        yAxis: { type: 'value', name: 'Seções (nº)', nameLocation: 'middle', nameGap: 60, axisLabel: { formatter: (x) => compacto(x) } },
        series: [
          { name: 'UE2009–2015', type: 'bar', barMaxWidth: 24, data: v('UE2009–2015'), itemStyle: { color: p.sequencial[4], borderRadius: [4, 4, 0, 0] } },
          { name: 'UE2020', type: 'bar', barMaxWidth: 24, data: v('UE2020'), itemStyle: { color: p.sequencial[2], borderRadius: [4, 4, 0, 0] } },
        ],
      };
    },
  },

  /** Fatia de Lula por macro × porte × grupo. */
  'ch08b-porte-fatia': {
    opcao: (json, p, { largura }) => {
      const cats = ['N+NE', 'S+SE+CO'].flatMap((m) => PORTES.map((po) => [m, po]));
      const v = (g) => cats.map(([m, po]) => json.dados.find((x) => x.macro === m && x.porte === po && x.grupo === g)?.lula ?? null);
      return {
        legend: { data: ['UE2009–2015', 'UE2020'] },
        grid: { left: 20, bottom: largura < 560 ? 90 : 62 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (x) => pct(x, 1) },
        xAxis: { type: 'category', data: cats.map(([m, po]) => (largura < 560 ? `${m} ${po.replace(' mil', 'k')}` : `${m}\n${po}`)),
          name: largura < 560 ? 'Região e porte' : 'Região e porte do município (votantes)', nameLocation: 'middle', nameGap: largura < 560 ? 62 : 46,
          axisLabel: { fontSize: largura < 560 ? 9 : 11, interval: 0, rotate: largura < 560 ? 45 : 0 } },
        yAxis: { type: 'value', min: 0.3, name: largura < 560 ? 'Fatia de Lula (%)' : 'Fatia de Lula nos votos válidos (%)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (x) => pct(x, 0) } },
        series: [
          { name: 'UE2009–2015', type: 'bar', barMaxWidth: 24, data: v('UE2009–2015'), itemStyle: { color: p.sequencial[4], borderRadius: [4, 4, 0, 0] } },
          { name: 'UE2020', type: 'bar', barMaxWidth: 24, data: v('UE2020'), itemStyle: { color: p.sequencial[2], borderRadius: [4, 4, 0, 0] } },
        ],
      };
    },
  },

  /** Nível da fatia de Lula vs UE2020, dentro do local (Brasil). */
  'ch08b-nivel': {
    opcao: (json, p, ctx) => {
      const d = json.dados.filter((x) => x.spec === 'EF local' && x.ref === 'UE2020' && x.amostra === 'Brasil' && x.identificado)
        .sort((a, b) => a.ano - b.ano || a.turno - b.turno || a.modelo.localeCompare(b.modelo));
      return floresta(p, d, (x) => `${x.ano} · ${x.turno}º turno · ${x.modelo}`, {
        ...ctx, esquerda: 200, nomeX: 'Diferença na fatia de Lula em relação à UE2020 (p.p.)', cor: (x) => (x.ano === 2022 ? p.sequencial[2] : p.sequencial[4]),
        tooltip: tipCoef((x) => `${x.modelo} vs UE2020 — ${x.ano}, ${x.turno}º turno, mesmo local`),
      });
    },
  },

  /** Δ entre turnos vs UE2020 (Brasil), mesmo município e mesmo local. */
  'ch08b-delta': {
    opcao: (json, p, ctx) => {
      const d = json.dados.filter((x) => x.amostra === 'Brasil' && x.spec !== 'bruto' && x.identificado)
        .sort((a, b) => a.ano - b.ano || a.spec.localeCompare(b.spec) || a.modelo.localeCompare(b.modelo));
      const sp = (s) => (s === 'EF local' ? 'mesmo local' : 'mesmo município');
      return floresta(p, d, (x) => `${x.ano} · ${x.modelo} · ${sp(x.spec)}`, {
        ...ctx, esquerda: 240, nomeX: 'Diferença no Δ de Lula entre turnos, vs. UE2020 (p.p.)', cor: (x) => (x.ano === 2022 ? p.sequencial[2] : p.sequencial[4]),
        tooltip: tipCoef((x) => `Δ 1º→2º turno, ${x.modelo} vs UE2020 — ${x.ano}, ${sp(x.spec)}`),
      });
    },
  },

  /** Persistência da diferença nas mesmas seções após a troca de urna. */
  'ch08b-persistencia': {
    opcao: (json, p, ctx) => {
      const ordem = ['N+NE · < 50 mil', 'Brasil', 'S+SE+CO', 'N+NE'];
      const d = json.dados.filter((x) => x.identificado)
        .sort((a, b) => ordem.indexOf(a.amostra) - ordem.indexOf(b.amostra) || a.eleicao.localeCompare(b.eleicao));
      return floresta(p, d, (x) => `${x.amostra} · ${x.eleicao}`, {
        ...ctx, esquerda: 230, nomeX: 'Diferença na fatia de Lula, urna antiga − UE2020 (p.p.)', cor: (x) => (x.eleicao.startsWith('2022') ? p.sequencial[2] : p.sequencial[4]),
        tooltip: tipCoef((x) => `${x.amostra} — ${x.eleicao}<br>Seções com urna antiga em 2022 menos seções com UE2020 (mesmo município)`),
      });
    },
  },

  /** Realocação: seções que perderam UE2009–2011. */
  'ch08b-realocacao': {
    opcao: (json, p, ctx) => {
      const ordem = ['Brasil', 'N+NE', 'N+NE · < 50 mil', 'S+SE+CO'];
      const d = json.dados.filter((x) => x.termo === 'ret22' && x.spec === 'EF município' && x.identificado && ordem.includes(x.amostra))
        .sort((a, b) => ordem.indexOf(a.amostra) - ordem.indexOf(b.amostra) || b.y.localeCompare(a.y));
      return floresta(p, d, (x) => `${x.amostra} · ${x.y.split(':')[0]}`, {
        ...ctx, esquerda: 200, nomeX: 'Variação da fatia de Lula 2022 → 2026, relativa ao município (p.p.)', cor: (x) => (x.y.startsWith('2º') ? p.sequencial[4] : p.sequencial[2]),
        tooltip: tipCoef((x) => `${x.amostra} — ${x.y}<br>Seções que tinham UE2009–2011 em 2022 vs. seções que tinham UE2020`),
      });
    },
  },

  /** Mesma urna física: correlação do desvio da seção em 2022 e 2026. */
  'ch08b-urna-fisica': {
    opcao: (json, p, { largura }) => {
      const d = json.dados.filter((x) => x.modelo_2022 === 'todas');
      return {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (its) => {
          const x = d[its[0].dataIndex];
          const sub = json.dados.filter((y) => y.destino === x.destino && y.modelo_2022 !== 'todas')
            .map((y) => `${y.modelo_2022}: ${num(y.correlacao, 3)} (${num(y.urnas)} urnas)`).join('<br>');
          return `${x.destino}<br>Correlação: <b>${num(x.correlacao, 3)}</b> (${num(x.urnas)} urnas)<br>${sub}`;
        } },
        grid: { left: 20, bottom: 80 },
        xAxis: { type: 'category', data: d.map((x) => x.destino), name: 'Destino da urna em 2026', nameLocation: 'middle', nameGap: 56, axisLabel: { interval: 0, fontSize: largura < 560 ? 9 : 11, width: largura < 560 ? 80 : 160, overflow: 'break' } },
        yAxis: { type: 'value', min: -0.2, max: 1, name: 'Correlação do desvio da seção, 2022 × 2026', nameLocation: 'middle', nameGap: 36, axisLabel: { formatter: (v) => num(v, 1) } },
        series: [{ type: 'bar', barMaxWidth: 24, data: d.map((x) => x.correlacao),
          itemStyle: { color: p.sequencial[3], borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', color: p.texto2, formatter: (it) => num(it.value, 2) } }],
      };
    },
  },
};

export const tabelas = {
  'ch08b-tab-validacao': {
    src: 'data/ch08b/validacao.json', filtro: false,
    colunas: [
      { chave: 'amostra', rotulo: 'Amostra' },
      { chave: 'modelo_log', rotulo: 'Modelo no log' },
      { chave: 'modelo_inferido', rotulo: 'Modelo pela série' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'serie_min', rotulo: 'Série mín.', formato: 'num' },
      { chave: 'serie_max', rotulo: 'Série máx.', formato: 'num' },
    ],
  },
  'ch08b-tab-bruto': {
    src: 'data/ch08b/bruto_regiao.json', porPagina: 12, filtro: true,
    colunas: [
      { chave: 'ano', rotulo: 'Ano', formato: 'texto' },
      { chave: 'regiao', rotulo: 'Região' },
      { chave: 'modelo', rotulo: 'Modelo' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'frac_secoes', rotulo: '% das seções da região', formato: 'pct1' },
      { chave: 'lula', rotulo: 'Lula (2º turno)', formato: 'pct1' },
      { chave: 'lula_regiao', rotulo: 'Lula na região', formato: 'pct1' },
    ],
  },
  'ch08b-tab-robustez': {
    src: 'data/ch08b/robustez.json', porPagina: 12, filtro: true,
    ordem: { chave: 'ano', direcao: 'desc' },
    colunas: [
      { chave: 'ano', rotulo: 'Ano', formato: 'texto' },
      { chave: 'turno', rotulo: 'Turno', formato: 'texto' },
      { chave: 'variante', rotulo: 'Variante' },
      { chave: 'modelo', rotulo: 'Modelo vs UE2020' },
      { chave: 'coef', rotulo: 'Diferença', formato: (v) => ppp(v) },
      { chave: 'ic_inf', rotulo: 'IC inf.', formato: (v) => ppp(v) },
      { chave: 'ic_sup', rotulo: 'IC sup.', formato: (v) => ppp(v) },
      { chave: 'p', rotulo: 'p', formato: (v) => (v == null ? 'não identificado' : num(v, 3)) },
    ],
  },
};
