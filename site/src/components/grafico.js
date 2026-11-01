/**
 * grafico.js — gráfico ECharts preguiçoso com estados, fonte e download.
 *
 * O que faz:
 *  - só baixa o ECharts e os dados quando a figura entra na tela (IntersectionObserver);
 *  - mostra "carregando…" e erro legível;
 *  - redimensiona sozinho (ResizeObserver) e se redesenha ao trocar o tema;
 *  - mescla a sua opção com a base visual do relatório (lib/tema.js → baseGrafico);
 *  - põe embaixo "Fonte: …" + "baixar dados (CSV · JSON)" + "código: script.py" (GitHub) + "ver dados em tabela".
 *
 * Uso programático:
 * @example
 * import { criarGrafico } from '../components/grafico.js';
 * criarGrafico(document.querySelector('#meu-grafico'), {
 *   src: 'data/demo.json',
 *   titulo: 'Votos válidos por turno',
 *   fonte: 'TSE — boletins de urna (demo)',
 *   opcao: (json, p) => ({
 *     xAxis: { type: 'category', data: json.dados.map((d) => d.turno) },
 *     yAxis: { type: 'value' },
 *     series: [{ type: 'bar', data: json.dados.map((d) => d.lula), itemStyle: { color: p.lula } }],
 *   }),
 * });
 *
 * Uso declarativo (no HTML do capítulo; o construtor vem de `export const graficos` do JS do capítulo):
 *   <figure class="grafico largo" data-grafico="ch01-demo" data-src="data/demo.json"
 *           data-titulo="…" data-subtitulo="…" data-fonte="…" data-altura="380" data-demo></figure>
 */
import { carregarJSON, linhasDe, paraCSV, baixarTexto, urlDados, urlRepositorio } from '../lib/dados.js';
import { paleta, baseGrafico, aoMudarTema } from '../lib/tema.js';
import { criarTabela } from './tabela.js';

let echartsPromessa = null;
/** Carrega o ECharts (uma vez). */
export function carregarECharts() {
  echartsPromessa ??= import('../lib/echarts.js').then((m) => m.default);
  return echartsPromessa;
}

const ehObj = (x) => x && typeof x === 'object' && !Array.isArray(x);

/** Merge profundo simples: `b` vence; eixos em array recebem a base em cada item. */
export function mesclar(a, b) {
  if (!ehObj(a)) return b;
  if (!ehObj(b)) return b === undefined ? a : b;
  const out = { ...a };
  for (const [k, v] of Object.entries(b)) {
    if (Array.isArray(v) && ehObj(a[k]) && ['xAxis', 'yAxis', 'grid', 'legend', 'visualMap', 'dataZoom'].includes(k)) {
      out[k] = v.map((item) => mesclar(a[k], item));
    } else {
      out[k] = ehObj(v) && ehObj(a[k]) ? mesclar(a[k], v) : v;
    }
  }
  return out;
}

/** Remove da base chaves que o gráfico não usa (ex.: eixos num gráfico de mapa). */
function baseParaOpcao(base, opcao) {
  const b = { ...base };
  if (!('xAxis' in opcao)) delete b.xAxis;
  if (!('yAxis' in opcao)) delete b.yAxis;
  if (!('legend' in opcao)) delete b.legend;
  if (!('xAxis' in opcao) && !('grid' in opcao)) delete b.grid;
  return b;
}

function el(tag, cls, txt) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (txt !== undefined) e.textContent = txt;
  return e;
}

/**
 * @typedef {object} OpcoesGrafico
 * @property {string} [src]       caminho do JSON (ex.: 'data/ch02/deslocamento.json')
 * @property {any}    [dados]     dados já em memória (alternativa a `src`)
 * @property {(dados:any, p:object, ctx:{largura:number, el:HTMLElement}) => object|Promise<object>} opcao
 *           constrói a opção ECharts; chamada de novo a cada troca de tema/resize de breakpoint
 * @property {string} [titulo]
 * @property {string} [subtitulo]
 * @property {string} [fonte]     texto da fonte ("TSE — boletins de urna, 2º turno 2026")
 * @property {number} [altura=380] altura em px da área do gráfico
 * @property {string|false} [csv] caminho de um CSV pronto; default: CSV gerado de `dados`; false esconde
 * @property {boolean} [demo]     marca o gráfico como DEMONSTRAÇÃO
 * @property {boolean} [tabela=true] oferece "ver dados em tabela" quando os dados são linhas planas
 * @property {(chart:any, echarts:any) => void} [aoMontar] gancho após o primeiro render (eventos etc.)
 * @property {boolean} [imediato] ignora o IntersectionObserver
 */

/**
 * Cria um gráfico preguiçoso dentro de `figura`.
 * @param {HTMLElement} figura
 * @param {OpcoesGrafico} op
 * @returns {{ pronto: Promise<any>, atualizar(dados:any):void, redesenhar():void, destruir():void, instancia():any }}
 */
export function criarGrafico(figura, op) {
  const d = figura.dataset;
  const cfg = {
    src: op.src ?? d.src,
    titulo: op.titulo ?? d.titulo,
    subtitulo: op.subtitulo ?? d.subtitulo,
    fonte: op.fonte ?? d.fonte,
    altura: op.altura ?? (d.altura ? Number(d.altura) : 380),
    csv: op.csv ?? (d.csv === 'false' ? false : d.csv),
    demo: op.demo ?? 'demo' in d,
    tabela: op.tabela ?? d.tabela !== 'false',
  };
  figura.classList.add('grafico');

  // --- estrutura ---
  if (cfg.demo) figura.prepend(el('div', 'selo-demo', 'Demonstração — dados fictícios'));
  if (cfg.titulo && !figura.querySelector('.grafico__titulo')) figura.append(el('h3', 'grafico__titulo', cfg.titulo));
  if (cfg.subtitulo && !figura.querySelector('.grafico__subtitulo')) figura.append(el('p', 'grafico__subtitulo', cfg.subtitulo));
  const eixos = el('p', 'grafico__eixos');
  eixos.hidden = true;
  figura.append(eixos);
  const legendaCompleta = el('details', 'grafico__legenda-completa');
  legendaCompleta.hidden = true;
  legendaCompleta.append(el('summary', '', 'Ver nomes completos da legenda'));
  const nomesLegenda = el('ul');
  legendaCompleta.append(nomesLegenda);
  figura.append(legendaCompleta);
  const area = el('div', 'grafico__area');
  area.style.setProperty('--altura', `${cfg.altura}px`);
  area.setAttribute('role', 'img');
  area.setAttribute('aria-label', cfg.titulo || 'Gráfico');
  const estado = el('div', 'grafico__estado');
  estado.innerHTML = '<span class="carregando">Carregando gráfico…</span>';
  area.append(estado);
  if (d.larguraMinima) {
    const aviso = el('p', 'grafico__aviso-rolagem', 'Deslize o gráfico para ver todas as colunas.');
    const rolagem = el('div', 'grafico__rolagem');
    rolagem.tabIndex = 0;
    rolagem.setAttribute('aria-label', 'Área rolável do gráfico');
    area.style.minWidth = `${Number(d.larguraMinima)}px`;
    rolagem.append(area);
    figura.append(aviso, rolagem);
  } else {
    figura.append(area);
  }

  const rodape = el('figcaption', 'grafico__rodape');
  const fonteEl = el('span', 'grafico__fonte', cfg.fonte ? `Fonte: ${cfg.fonte}` : '');
  const baixar = el('span', 'grafico__baixar');
  rodape.append(fonteEl, baixar);
  figura.append(rodape);
  const detalhes = el('details', 'tabela-alternativa');
  detalhes.hidden = true;
  detalhes.append(el('summary', '', 'Ver dados em tabela'));
  figura.append(detalhes);

  let chart = null;
  let echarts = null;
  let dados = op.dados;
  let destruido = false;
  let cancelarTema = () => {};
  let ro = null;
  let io = null;

  const mostrarErro = (e) => {
    console.error('[grafico]', cfg.src, e);
    estado.hidden = false;
    estado.className = 'grafico__estado grafico__estado--erro';
    estado.textContent = `Não foi possível carregar o gráfico (${e.message || e}).`;
  };

  async function renderizar(primeira = false) {
    const p = paleta();
    const opcao = await op.opcao(dados, p, { largura: area.clientWidth, el: figura });
    if (!opcao) return;
    const final = mesclar(baseParaOpcao(baseGrafico(p), opcao), opcao);
    const estreito = area.clientWidth < 560;
    const nomesEixos = [];
    for (const [chave, rotulo] of [['xAxis', 'Horizontal'], ['yAxis', 'Vertical']]) {
      const eixosDoTipo = Array.isArray(final[chave]) ? final[chave] : [final[chave]];
      for (const eixo of eixosDoTipo) {
        if (!eixo) continue;
        eixo.axisLabel = { ...eixo.axisLabel, hideOverlap: eixo.axisLabel?.hideOverlap ?? true };
        if (estreito && eixo.name) {
          nomesEixos.push(`${rotulo}: ${eixo.name}`);
          eixo.name = '';
        }
      }
    }
    eixos.textContent = nomesEixos.join(' · ');
    eixos.hidden = !nomesEixos.length;
    const legendas = Array.isArray(final.legend) ? final.legend : [final.legend];
    const nomesLongos = [];
    if (estreito) for (const legenda of legendas) {
      if (!legenda || !Array.isArray(legenda.data)) continue;
      const nomes = legenda.data.map((item) => typeof item === 'string' ? item : item.name).filter(Boolean);
      if (!nomes.some((nome) => nome.length > 16)) continue;
      nomesLongos.push(...nomes);
      const formatar = legenda.formatter;
      legenda.formatter = (nome) => {
        const texto = typeof formatar === 'function' ? formatar(nome) : nome;
        return texto.length > 16 ? `${texto.slice(0, 13)}…` : texto;
      };
      legenda.type = 'scroll';
      legenda.tooltip = { show: true };
    }
    nomesLegenda.replaceChildren(...[...new Set(nomesLongos)].map((nome) => el('li', '', nome)));
    legendaCompleta.hidden = !nomesLongos.length;
    chart.setOption(final, { notMerge: true });
    if (primeira) op.aoMontar?.(chart, echarts);
  }

  function montarDownloads() {
    baixar.textContent = '';
    const linhas = linhasDe(dados);
    const nomeBase = (cfg.src || 'dados').split('/').pop().replace(/\.json$/, '');
    if (cfg.csv !== false && (typeof cfg.csv === 'string' || linhas)) {
      const b = el('button', '', 'CSV');
      b.type = 'button';
      b.addEventListener('click', () => {
        if (typeof cfg.csv === 'string') window.open(urlDados(cfg.csv), '_blank', 'noopener');
        else baixarTexto(paraCSV(linhas), `${nomeBase}.csv`);
      });
      baixar.append('baixar dados: ', b);
    }
    if (cfg.src) {
      const a = el('a', '', 'JSON');
      a.href = urlDados(cfg.src);
      a.download = `${nomeBase}.json`;
      if (!baixar.childNodes.length) baixar.append('baixar dados: ');
      else baixar.append(' · ');
      baixar.append(a);
    }
    const script = dados?.meta?.script;
    if (script) {
      const a = el('a', '', script.split('/').pop());
      a.href = urlRepositorio(script);
      a.target = '_blank';
      a.rel = 'noopener';
      a.title = 'Script que gera estes dados, no GitHub';
      if (baixar.childNodes.length) baixar.append(' · ');
      baixar.append('código: ', a);
    }
    if (cfg.tabela && linhas?.length) {
      detalhes.hidden = false;
      detalhes.addEventListener('toggle', () => {
        if (detalhes.open && !detalhes.querySelector('.tabela')) {
          const alvo = el('div');
          detalhes.append(alvo);
          criarTabela(alvo, { dados: linhas, porPagina: 25, filtro: linhas.length > 25 });
        }
      });
    }
    if (!cfg.fonte && dados?.meta?.fonte) fonteEl.textContent = `Fonte: ${dados.meta.fonte}`;
  }

  async function montar() {
    try {
      const [ec, json] = await Promise.all([carregarECharts(), dados !== undefined ? dados : (cfg.src ? carregarJSON(cfg.src) : null)]);
      if (destruido) return null;
      echarts = ec;
      dados = json;
      estado.hidden = true;
      chart = echarts.init(area, null, { renderer: 'canvas' });
      montarDownloads();
      await renderizar(true);
      let ultimaLargura = area.clientWidth;
      ro = new ResizeObserver(() => {
        chart?.resize();
        // redesenha ao cruzar ~breakpoint (opções podem depender de ctx.largura)
        const w = area.clientWidth;
        if ((w < 560) !== (ultimaLargura < 560)) renderizar();
        ultimaLargura = w;
      });
      ro.observe(area);
      cancelarTema = aoMudarTema(() => renderizar());
      return chart;
    } catch (e) {
      mostrarErro(e);
      return null;
    }
  }

  let resolver;
  const pronto = new Promise((r) => { resolver = r; });
  const iniciar = () => montar().then(resolver);

  if (op.imediato || !('IntersectionObserver' in window)) {
    iniciar();
  } else {
    io = new IntersectionObserver((ents) => {
      if (ents.some((e) => e.isIntersecting)) {
        io.disconnect();
        iniciar();
      }
    }, { rootMargin: '300px 0px' });
    io.observe(figura);
  }

  return {
    pronto,
    instancia: () => chart,
    /** Troca os dados e redesenha (ex.: filtro externo). */
    atualizar(novos) {
      dados = novos;
      if (chart) renderizar();
    },
    redesenhar: () => chart && renderizar(),
    destruir() {
      destruido = true;
      io?.disconnect();
      ro?.disconnect();
      cancelarTema();
      chart?.dispose();
    },
  };
}
