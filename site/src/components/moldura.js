/**
 * Moldura comum às páginas do site (relatório e simulador): abas na barra superior, convite para a estrela no GitHub
 * e rodapé. Cada página chama montarMoldura() com o nome da aba atual e o caminho até a raiz
 * do site ('./' na raiz, '../' nas páginas em subpasta), para os links funcionarem em qualquer
 * subcaminho do GitHub Pages.
 *
 * @example
 * montarMoldura({ pagina: 'simulador', raiz: '../' });
 */
import { iniciarTema } from '../lib/tema.js';
import { REPOSITORIO } from '../lib/dados.js';

const ABAS = [
  { id: 'relatorio', rotulo: 'Relatório', caminho: '' },
  { id: 'simulador', rotulo: 'Simulador', caminho: 'simulador/' },
];

function el(tag, classe, html) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

/** Caixa "deixe uma estrela no GitHub". */
export function criarEstrela(classeExtra = '') {
  const caixa = el('aside', `estrela ${classeExtra}`.trim());
  caixa.setAttribute('aria-label', 'Apoie o projeto');
  caixa.append(
    el('p', '', 'Se você gostou deste tipo de análise e conteúdo, deixe uma estrela no GitHub. Isso ajuda o projeto a chegar a mais gente.'),
  );
  const a = el('a', '', '<span aria-hidden="true">★</span> Dar uma estrela');
  a.href = REPOSITORIO;
  a.target = '_blank';
  a.rel = 'noopener';
  caixa.append(a);
  return caixa;
}

function criarAbas(pagina, raiz) {
  const nav = el('nav', 'abas');
  nav.setAttribute('aria-label', 'Páginas do site');
  for (const aba of ABAS) {
    const a = el('a', '', aba.rotulo);
    a.href = raiz + aba.caminho;
    if (aba.id === pagina) a.setAttribute('aria-current', 'page');
    nav.append(a);
  }
  return nav;
}

/**
 * Monta a moldura. Usa a barra `.topo` e o rodapé `.rodape` da página se existirem; senão,
 * cria os dois (caso do simulador, cujo HTML é gerado por scripts/gerar_simulador.py).
 * @param {{ pagina: 'relatorio'|'simulador', raiz: string, estrelaNoTopo?: Element|null }} op
 */
export function montarMoldura({ pagina, raiz, estrelaNoTopo = null }) {
  let topo = document.querySelector('header.topo');
  if (!topo) {
    topo = el('header', 'topo');
    const marca = el('a', 'topo__marca', 'Urnas 2026');
    marca.href = raiz;
    const tema = el('button', 'botao');
    tema.type = 'button';
    topo.append(marca, tema);
    document.body.prepend(topo);
    iniciarTema(tema);
  }
  const botaoTema = topo.querySelector('#botao-tema, .botao:last-child');
  topo.insertBefore(criarAbas(pagina, raiz), botaoTema);

  if (estrelaNoTopo) estrelaNoTopo.replaceWith(criarEstrela('estrela--topo'));

  let rodape = document.querySelector('footer.rodape');
  if (!rodape) {
    rodape = el('footer', 'rodape');
    document.body.append(rodape);
  }
  rodape.replaceChildren(
    criarEstrela(),
    el('p', '', `Estudo exploratório independente, baseado em dados públicos e aberto a revisão. Não afirma nem sugere fraude. <a href="${REPOSITORIO}" target="_blank" rel="noopener">Código, dados derivados e instruções no GitHub</a>.`),
  );
}
