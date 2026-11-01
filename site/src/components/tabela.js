/**
 * tabela.js — tabela ordenável, filtrável e paginada a partir de JSON.
 * Rola dentro do próprio contêiner (nunca gera rolagem horizontal na página).
 *
 * @example
 * import { criarTabela } from '../components/tabela.js';
 * criarTabela(document.querySelector('#tab-secoes'), {
 *   src: 'data/ch09/secoes-extremas.json',   // ou dados: [...]
 *   colunas: [
 *     { chave: 'uf', rotulo: 'UF' },
 *     { chave: 'municipio', rotulo: 'Município' },
 *     { chave: 'aptos', rotulo: 'Aptos', formato: 'num' },
 *     { chave: 'pct_lula', rotulo: '% Lula', formato: 'pct' },        // fração 0–1
 *     { chave: 'delta', rotulo: 'Δ entre turnos', formato: 'pp' },
 *   ],
 *   ordem: { chave: 'aptos', direcao: 'desc' },
 *   porPagina: 50,          // 0 = sem paginação
 *   filtro: true,           // caixa de busca (texto, todas as colunas)
 * });
 *
 * Declarativo: <div data-tabela="ch09-extremas"></div> com a config em
 * `export const tabelas = { 'ch09-extremas': { src, colunas, ... } }` no JS do capítulo.
 */
import { carregarJSON, linhasDe } from '../lib/dados.js';
import { formatador } from '../lib/formato.js';

/**
 * @typedef {object} Coluna
 * @property {string} chave
 * @property {string} [rotulo]
 * @property {string|((v:any, linha:object)=>string)} [formato] nome em lib/formato.js#formatador ou função
 * @property {boolean} [numerica] força alinhamento à direita (auto se formato numérico ou valores numéricos)
 * @property {(linha:object)=>string} [html] renderização HTML livre da célula (cuidado: não escapa)
 */

/**
 * @param {HTMLElement} alvo
 * @param {{src?:string, dados?:object[], colunas?:Coluna[], ordem?:{chave:string, direcao:'asc'|'desc'},
 *          porPagina?:number, filtro?:boolean, legenda?:string}} op
 * @returns {Promise<{atualizar(dados:object[]):void}>}
 */
export async function criarTabela(alvo, op = {}) {
  alvo.classList.add('tabela');
  alvo.innerHTML = '<p class="tabela__info carregando">Carregando tabela…</p>';
  let linhas;
  try {
    linhas = op.dados ?? linhasDe(await carregarJSON(op.src)) ?? [];
  } catch (e) {
    alvo.innerHTML = `<p class="tabela__vazio">Não foi possível carregar a tabela (${e.message}).</p>`;
    return { atualizar() {} };
  }

  const colunas = (op.colunas ?? Object.keys(linhas[0] ?? {}).map((chave) => ({ chave }))).map((c) => {
    const fmt = c.formato ? formatador(c.formato) : null;
    const numerica = c.numerica ?? (c.formato
      ? !['texto', 'data'].includes(c.formato)
      : linhas.slice(0, 20).every((l) => l[c.chave] == null || typeof l[c.chave] === 'number'));
    return {
      ...c,
      rotulo: c.rotulo ?? c.chave,
      numerica,
      fmt: fmt ?? (numerica ? formatador(Number.isInteger(linhas[0]?.[c.chave]) ? 'num' : 'num2') : formatador('texto')),
    };
  });

  const porPagina = op.porPagina ?? (linhas.length > 100 ? 50 : 0);
  let ordem = op.ordem ? { ...op.ordem } : null;
  let termo = '';
  let pagina = 0;

  alvo.innerHTML = '';
  const barra = document.createElement('div');
  barra.className = 'tabela__barra';
  const usarFiltro = op.filtro ?? linhas.length > 15;
  let entrada = null;
  if (usarFiltro) {
    entrada = document.createElement('input');
    entrada.type = 'search';
    entrada.className = 'tabela__filtro';
    entrada.placeholder = 'Filtrar…';
    entrada.setAttribute('aria-label', 'Filtrar linhas da tabela');
    barra.append(entrada);
  }
  const info = document.createElement('span');
  info.className = 'tabela__info';
  info.setAttribute('aria-live', 'polite');
  barra.append(info);

  const rolagem = document.createElement('div');
  rolagem.className = 'tabela__rolagem';
  rolagem.tabIndex = 0;
  const tabela = document.createElement('table');
  if (op.legenda) {
    const cap = document.createElement('caption');
    cap.className = 'sr-only';
    cap.textContent = op.legenda;
    tabela.append(cap);
  }
  const thead = tabela.createTHead();
  const trh = thead.insertRow();
  colunas.forEach((c) => {
    const th = document.createElement('th');
    th.scope = 'col';
    if (c.numerica) th.className = 'tabela__num';
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = c.rotulo;
    b.addEventListener('click', () => {
      ordem = ordem?.chave === c.chave
        ? { chave: c.chave, direcao: ordem.direcao === 'asc' ? 'desc' : 'asc' }
        : { chave: c.chave, direcao: c.numerica ? 'desc' : 'asc' };
      pagina = 0;
      desenhar();
    });
    th.append(b);
    trh.append(th);
  });
  const tbody = tabela.createTBody();
  rolagem.append(tabela);

  const pag = document.createElement('div');
  pag.className = 'tabela__paginacao';
  alvo.append(barra, rolagem, pag);

  const colator = new Intl.Collator('pt-BR', { sensitivity: 'base', numeric: true });
  const norm = (s) => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  let indiceBusca = linhas.map((l) => norm(colunas.map((c) => l[c.chave]).join(' ')));

  function desenhar() {
    let vis = linhas.map((l, i) => i);
    if (termo) {
      const t = norm(termo);
      vis = vis.filter((i) => indiceBusca[i].includes(t));
    }
    if (ordem) {
      const { chave, direcao } = ordem;
      const s = direcao === 'asc' ? 1 : -1;
      vis.sort((a, b) => {
        const x = linhas[a][chave];
        const y = linhas[b][chave];
        if (x == null) return 1;
        if (y == null) return -1;
        return s * (typeof x === 'number' && typeof y === 'number' ? x - y : colator.compare(x, y));
      });
    }
    trh.querySelectorAll('th').forEach((th, i) => {
      th.setAttribute('aria-sort', ordem?.chave === colunas[i].chave ? (ordem.direcao === 'asc' ? 'ascending' : 'descending') : 'none');
    });

    const total = vis.length;
    const paginas = porPagina ? Math.max(1, Math.ceil(total / porPagina)) : 1;
    pagina = Math.min(pagina, paginas - 1);
    const fatia = porPagina ? vis.slice(pagina * porPagina, (pagina + 1) * porPagina) : vis;

    const frag = document.createDocumentFragment();
    for (const i of fatia) {
      const l = linhas[i];
      const tr = document.createElement('tr');
      for (const c of colunas) {
        const td = document.createElement('td');
        if (c.numerica) td.className = 'tabela__num';
        if (c.html) td.innerHTML = c.html(l);
        else td.textContent = c.fmt(l[c.chave], l);
        tr.append(td);
      }
      frag.append(tr);
    }
    tbody.replaceChildren(frag);
    if (!total) {
      const tr = tbody.insertRow();
      const td = tr.insertCell();
      td.colSpan = colunas.length;
      td.className = 'tabela__vazio';
      td.textContent = 'Nenhuma linha corresponde ao filtro.';
    }

    const n = new Intl.NumberFormat('pt-BR');
    info.textContent = termo
      ? `${n.format(total)} de ${n.format(linhas.length)} linhas`
      : `${n.format(total)} linhas`;

    pag.replaceChildren();
    if (porPagina && paginas > 1) {
      const btn = (txt, alvoPag, desab) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'botao';
        b.textContent = txt;
        b.disabled = desab;
        b.addEventListener('click', () => { pagina = alvoPag; desenhar(); });
        return b;
      };
      const st = document.createElement('span');
      st.className = 'tabela__info';
      st.textContent = `página ${pagina + 1} de ${paginas}`;
      pag.append(btn('« anterior', pagina - 1, pagina === 0), st, btn('próxima »', pagina + 1, pagina >= paginas - 1));
    }
  }

  let t;
  entrada?.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => { termo = entrada.value.trim(); pagina = 0; desenhar(); }, 150);
  });

  desenhar();
  return {
    atualizar(novas) {
      linhas = novas;
      indiceBusca = linhas.map((l) => norm(colunas.map((c) => l[c.chave]).join(' ')));
      desenhar();
    },
  };
}
