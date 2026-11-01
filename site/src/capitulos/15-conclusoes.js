/**
 * Capítulo 15 — Conclusões. Dados: public/data/ch12/escala.json (números copiados das saídas
 * dos scripts dos capítulos 1, 2, 5, 6, 7, 8 e 9; ver meta.script).
 */
import { num } from '../lib/formato.js';

const MI = (v) => (v >= 1e6 ? `${num(v / 1e6, 2)} mi` : `${num(v / 1e3, 0)} mil`);

const SITUACOES = [
  { chave: 'descartado', nome: 'Testado e descartado', cor: (p) => p.texto3 },
  { chave: 'sem pegadas', nome: 'Pegadas procuradas, não encontradas', cor: (p) => p.sequencial[2] },
  { chave: 'aberto', nome: 'Não distinguível com contagens', cor: (p) => p.sequencial[4] },
];

export const graficos = {
  'ch12-escala': {
    tabela: true,
    opcao: (json, p, { largura }) => {
      const estreito = largura < 560;
      const margem = json.meta.margem;
      const d = [...json.dados].sort((a, b) => a.efeito_max - b.efeito_max);
      const rotulo = (m) => (estreito ? m.replace(/\s*\(.*\)$/, '') : m);
      return {
        legend: { data: SITUACOES.map((s) => s.nome) },
        grid: { top: estreito ? 104 : 56, left: 8, right: estreito ? 24 : 64, bottom: 52, containLabel: true },
        tooltip: {
          trigger: 'item',
          formatter: (x) => {
            const r = d[x.dataIndex];
            return `${r.mecanismo}<br>Votos envolvidos: <b>${num(r.votos)}</b>${r.multiplicador > 1 ? ' (trocados: contam 2×)' : ''}`
              + `<br>Efeito máximo: <b>${num(r.efeito_max)}</b> (${num((100 * r.efeito_max) / margem, 1)}% da margem)`
              + `<br>Capítulo ${r.capitulo}`;
          },
        },
        xAxis: {
          type: 'value', max: Math.ceil(Math.max(margem, ...d.map((r) => r.efeito_max)) / (estreito ? 4e6 : 2e6)) * (estreito ? 4e6 : 2e6), interval: estreito ? 4e6 : 2e6,
          name: estreito ? 'Efeito máximo (milhões de votos)' : 'Efeito máximo sobre a margem de Lula (milhões de votos)', nameLocation: 'middle', nameGap: 30,
          axisLabel: { formatter: (v) => (v ? `${num(v / 1e6, 0)} mi` : '0') },
        },
        yAxis: {
          type: 'category', data: d.map((r) => rotulo(r.mecanismo)),
          axisLabel: { width: estreito ? 128 : 300, overflow: 'break', lineHeight: 13, fontSize: estreito ? 10 : 12 },
        },
        series: SITUACOES.map((s, i) => ({
          name: s.nome,
          type: 'bar',
          stack: 'x',
          barMaxWidth: 24,
          itemStyle: { color: s.cor(p), borderRadius: [0, 4, 4, 0] },
          label: {
            show: !estreito, position: 'right', color: p.texto2, fontSize: 11,
            formatter: (x) => `${num((100 * x.value) / margem, 1)}%`,
          },
          data: d.map((r) => (r.situacao === s.chave ? r.efeito_max : null)),
          ...(i === 0 ? {
            markLine: {
              silent: true, symbol: 'none',
              lineStyle: { color: p.texto1, type: 'dashed', width: 1.5 },
              label: { formatter: `margem ${MI(margem)}`, color: p.texto1, fontSize: 11, position: 'insideEndTop' },
              data: [{ xAxis: margem }],
            },
          } : {}),
        })),
      };
    },
  },
};
