/**
 * mapa.js — registro preguiçoso de GeoJSON no ECharts para coropléticos.
 *
 * Coloque os arquivos em public/data/geo/ (ex.: br-municipios.json, br-uf.json),
 * de preferência simplificados (mapshaper -simplify 5% keep-shapes) e com
 * `properties.codigo_ibge` / `properties.nome`. Arquivo de municípios: mire < 3 MB.
 *
 * @example
 * import { criarGrafico } from '../components/grafico.js';
 * import { registrarMapa } from '../components/mapa.js';
 * criarGrafico(fig, {
 *   src: 'data/ch02/deslocamento-municipios.json',
 *   altura: 620,
 *   opcao: async (json, p) => {
 *     await registrarMapa('br-municipios');          // data/geo/br-municipios.json
 *     return {
 *       tooltip: { trigger: 'item' },
 *       visualMap: { min: -0.1, max: 0.1, inRange: { color: p.divergente }, calculable: true, left: 0, bottom: 0 },
 *       series: [{ type: 'map', map: 'br-municipios', nameProperty: 'codigo_ibge', roam: true,
 *                  data: json.dados.map((d) => ({ name: String(d.codigo_ibge), value: d.delta })) }],
 *     };
 *   },
 * });
 */
import { carregarECharts } from './grafico.js';
import { carregarJSON } from '../lib/dados.js';

const registrados = new Map();

/**
 * Baixa (uma vez) e registra o GeoJSON sob `nome`.
 * @param {string} nome nome do mapa a usar em `series.map`/`geo.map`
 * @param {string} [caminho] default `data/geo/${nome}.json`
 * @returns {Promise<object>} o GeoJSON
 */
export function registrarMapa(nome, caminho = `data/geo/${nome}.json`) {
  if (!registrados.has(nome)) {
    const p = Promise.all([carregarECharts(), carregarJSON(caminho)]).then(([echarts, geo]) => {
      echarts.registerMap(nome, geo);
      return geo;
    });
    p.catch(() => registrados.delete(nome));
    registrados.set(nome, p);
  }
  return registrados.get(nome);
}
