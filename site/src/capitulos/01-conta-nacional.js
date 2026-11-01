/**
 * Capítulo 1 — A conta nacional. Dados: analises/01_conta_nacional.py → public/data/ch01/*.json
 */
import { compacto, num, pct } from '../lib/formato.js';

const MI = (v) => `${num(v / 1e6, 2)} mi`;
const eixoMi = { type: 'value', name: 'Votos (milhões)', nameLocation: 'middle', nameGap: 40, axisLabel: { formatter: (v) => `${num(v / 1e6, 0)} mi` } };

export const graficos = {
  /** Barras empilhadas: fontes contábeis × destino do ganho, 2026 e 2022. */
  'ch01-fontes': {
    opcao: (json, p, { largura }) => {
      const d = json.dados;
      const anos = [2026, 2022];
      const cats = anos.flatMap((a) => [`${a}\nfontes`, `${a}\ndestino`]);
      const v = (ano, fonte) => d.find((x) => x.ano === ano && x.fonte === fonte)?.votos ?? 0;
      const fontes = [
        { nome: 'Votos dos eliminados', cor: p.neutroMeio },
        { nome: 'Aumento do comparecimento', cor: p.abstencao },
        { nome: 'Queda de brancos e nulos', cor: p.brancos },
      ];
      const destinos = [
        { nome: 'Ganho de Lula', cor: p.lula },
        { nome: 'Ganho do adversário', cor: p.flavio, rotulo: 'Ganho de Flávio (2026) / Bolsonaro (2022)' },
      ];
      const serie = (s, ehFonte) => ({
        name: s.rotulo ?? s.nome,
        type: 'bar',
        stack: 'total',
        barMaxWidth: 56,
        itemStyle: { color: s.cor, borderColor: p.sup0, borderWidth: 1 },
        label: {
          show: false,
          formatter: ({ value }) => (Math.abs(value) >= 1.2e6 ? MI(value) : ''),
        },
        data: cats.map((c) => {
          const ano = Number(c.slice(0, 4));
          const lado = c.endsWith('fontes');
          return lado === ehFonte ? v(ano, s.nome) : null;
        }),
      });
      return {
        legend: { data: [...fontes, ...destinos].map((s) => s.rotulo ?? s.nome) },
        grid: { top: largura < 560 ? 90 : 64, left: 60, right: 16, bottom: 52 },
        tooltip: { trigger: 'item', formatter: (x) => `${x.seriesName}<br>${x.name.replace('\n', ' · ')}: <b>${num(x.value)}</b> votos` },
        xAxis: { type: 'category', data: cats, axisLabel: { interval: 0, lineHeight: 16 } },
        yAxis: eixoMi,
        series: [...fontes.map((s) => serie(s, true)), ...destinos.map((s) => serie(s, false))],
      };
    },
  },

  /** Barras agrupadas: % de seções com perda absoluta, por candidato e ano. */
  'ch01-perdas': (json, p, { largura }) => {
    const d = json.dados;
    const anos = [2026, 2022];
    const val = (ano, med) => d.find((x) => x.ano === ano && x.medida === med);
    const series = [
      { nome: 'Adversário de Lula perdeu votos', med: 'Seções em que o adversário de Lula perdeu votos', cor: p.flavio },
      { nome: 'Lula perdeu votos', med: 'Seções em que Lula perdeu votos', cor: p.lula },
    ];
    return {
      legend: { data: series.map((s) => s.nome) },
      grid: { top: 48, left: 64, right: 16, bottom: 32 },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.5 } },
        formatter: (ps) => `${ps[0].axisValue}<br>${ps.map((x) => `${x.marker}${x.seriesName}: <b>${pct(x.value, 1)}</b> (${num(x.data.secoes)} seções)`).join('<br>')}`,
      },
      xAxis: { type: 'category', data: anos.map((a) => (a === 2026 ? '2026 (adversário = Flávio)' : '2022 (adversário = Bolsonaro)')) },
      yAxis: { type: 'value', max: 0.25, name: largura < 560 ? 'Seções (%)' : 'Seções com perda de votos (% das pareadas)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
      series: series.map((s) => ({
        name: s.nome, type: 'bar', barMaxWidth: 48, barGap: '20%',
        itemStyle: { color: s.cor, borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: 'top', color: p.texto2, fontSize: 11, formatter: ({ value }) => pct(value, 1) },
        data: anos.map((a) => ({ value: val(a, s.med).fracao, secoes: val(a, s.med).secoes })),
      })),
    };
  },

  /** Linhas: histograma da variação do finalista que perdeu fatia, por seção. */
  'ch01-hist': (json, p, { largura }) => {
    const d = json.dados;
    const s26 = d.filter((x) => x.ano === 2026 && x.candidato === 'Adversário');
    const s22 = d.filter((x) => x.ano === 2022 && x.candidato === 'Lula');
    const tot = (s) => s.reduce((a, x) => a + x.secoes, 0);
    const linha = (s, nome, cor) => ({
      name: nome, type: 'line', smooth: false, symbol: 'none', lineStyle: { width: 2, color: cor },
      itemStyle: { color: cor }, areaStyle: { color: cor, opacity: 0.1 },
      data: s.map((x) => [x.faixa, x.secoes / tot(s)]),
    });
    return {
      legend: { data: ['Flávio, 2026', 'Lula, 2022'] },
      grid: { top: 48, left: 64, right: 16, bottom: 48 },
      tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v, 1) + ' das seções' },
      xAxis: {
        type: 'value', min: -0.2, max: 0.3, name: largura < 560 ? '' : 'Δ votos ÷ comparecimento do 1º turno',
        nameLocation: 'middle', nameGap: 30, axisLabel: { formatter: (v) => pct(v, 0) },
      },
      yAxis: { type: 'value', name: 'Seções (% do total)', nameLocation: 'middle', nameGap: 44, axisLabel: { formatter: (v) => pct(v, 0) } },
      series: [
        { ...linha(s26, 'Flávio, 2026', p.flavio),
          markLine: { silent: true, symbol: 'none', lineStyle: { color: p.texto3, type: 'dashed', width: 1 },
            label: { color: p.texto2, formatter: 'perdeu ← | → ganhou' }, data: [{ xAxis: 0 }] } },
        linha(s22, 'Lula, 2022', p.lula),
      ],
    };
  },

  /** Barras agrupadas por nível de agregação. */
  'ch01-migracao': (json, p) => {
    const d = json.dados;
    const niveis = ['Seção', 'Município', 'UF', 'Brasil'];
    const g = (ano, nivel) => d.find((x) => x.ano === ano && x.nivel === nivel);
    return {
      legend: { data: ['2026: Flávio → Lula', '2022: Lula → Bolsonaro'] },
      grid: { top: 48, left: 72, right: 16, bottom: 56 },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: p.grade, opacity: 0.5 } },
        valueFormatter: (v) => `${num(v)} votos`,
      },
      xAxis: { type: 'category', data: niveis.map((n) => `somado por ${n.toLowerCase()}`), name: 'Nível de agregação', nameLocation: 'middle', nameGap: 32 },
      yAxis: { type: 'value', name: 'Migração mínima (votos)', nameLocation: 'middle', nameGap: 50, axisLabel: { formatter: (v) => compacto(v, 0) } },
      series: [
        { name: '2026: Flávio → Lula', type: 'bar', barMaxWidth: 40, itemStyle: { color: p.lula, borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', color: p.texto2, fontSize: 11, formatter: ({ value }) => num(value) },
          data: niveis.map((n) => g(2026, n).min_adv_para_lula) },
        { name: '2022: Lula → Bolsonaro', type: 'bar', barMaxWidth: 40, itemStyle: { color: p.flavio, borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', color: p.texto2, fontSize: 11, formatter: ({ value }) => num(value) },
          data: niveis.map((n) => g(2022, n).min_lula_para_adv) },
      ],
    };
  },
};

export const tabelas = {
  'ch01-comparecimento-uf': {
    src: 'data/ch01/comparecimento-uf.json', porPagina: 0, filtro: true,
    ordem: { chave: 'delta_comparecimento', direcao: 'desc' },
    colunas: [
      { chave: 'sg_uf', rotulo: 'UF' },
      { chave: 'regiao', rotulo: 'Região' },
      { chave: 'comp_1', rotulo: 'Comparecimento 1º turno', formato: 'num' },
      { chave: 'comp_2', rotulo: 'Comparecimento 2º turno', formato: 'num' },
      { chave: 'delta_comparecimento', rotulo: 'Saldo entre turnos', formato: 'num' },
      { chave: 'fatia_lula', rotulo: 'Lula nos válidos 2º turno', formato: 'pct1' },
    ],
  },
  'ch01-reconciliacao': {
    src: 'data/ch01/reconciliacao-rj.json',
    legenda: 'Resíduo de reconciliação nos municípios do RJ citados nas alegações que circulam',
    filtro: false,
    colunas: [
      { chave: 'municipio', rotulo: 'Município' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'comp_2', rotulo: 'Comparecimento (2º t.)', formato: 'num' },
      { chave: 'residuo_csv_alegacao', rotulo: 'R no CSV que circulou', formato: (v) => (v == null ? 'n/d' : num(v)) },
      { chave: 'residuo_oficial_t2', rotulo: 'R nos BUs oficiais', formato: 'num' },
      { chave: 'delta_lula', rotulo: 'Δ Lula', formato: 'num' },
      { chave: 'delta_flavio', rotulo: 'Δ Flávio', formato: 'num' },
    ],
  },
  'ch01-uf': {
    src: 'data/ch01/reservatorio-uf.json',
    legenda: 'Seções com perda absoluta e migração mínima, por UF e ano',
    porPagina: 28,
    ordem: { chave: 'min_adv_para_lula_sobre_comp', direcao: 'desc' },
    colunas: [
      { chave: 'ano', rotulo: 'Ano', formato: 'texto' },
      { chave: 'sg_uf', rotulo: 'UF' },
      { chave: 'secoes', rotulo: 'Seções', formato: 'num' },
      { chave: 'frac_adv_perdeu', rotulo: 'Adversário perdeu votos', formato: 'pct1' },
      { chave: 'frac_lula_perdeu', rotulo: 'Lula perdeu votos', formato: 'pct1' },
      { chave: 'min_adv_para_lula', rotulo: 'Mín. adversário → Lula', formato: 'num' },
      { chave: 'min_lula_para_adv', rotulo: 'Mín. Lula → adversário', formato: 'num' },
      { chave: 'min_adv_para_lula_sobre_comp', rotulo: 'Adv. → Lula (% votantes)', formato: (v) => pct(v, 2) },
      { chave: 'min_lula_para_adv_sobre_comp', rotulo: 'Lula → adv. (% votantes)', formato: (v) => pct(v, 2) },
    ],
  },
  'ch01-top': {
    src: 'data/ch01/secoes-maior-perda-flavio.json',
    legenda: 'Seções com maior perda absoluta de Flávio entre turnos, 2026',
    porPagina: 10,
    filtro: false,
    colunas: [
      { chave: 'sg_uf', rotulo: 'UF' },
      { chave: 'nm_municipio', rotulo: 'Município' },
      { chave: 'zona', rotulo: 'Zona' },
      { chave: 'secao', rotulo: 'Seção' },
      { chave: 'comp_1', rotulo: 'Votantes 1º', formato: 'num' },
      { chave: 'comp_2', rotulo: 'Votantes 2º', formato: 'num' },
      { chave: 'lula_1', rotulo: 'Lula 1º', formato: 'num' },
      { chave: 'lula_2', rotulo: 'Lula 2º', formato: 'num' },
      { chave: 'flavio_1', rotulo: 'Flávio 1º', formato: 'num' },
      { chave: 'flavio_2', rotulo: 'Flávio 2º', formato: 'num' },
      { chave: 'outros_1', rotulo: 'Eliminados', formato: 'num' },
      { chave: 'min_A_para_L', rotulo: 'Migração mínima', formato: 'num' },
    ],
  },
};
