/**
 * Ponto de entrada. Ordem: tema → capítulos (HTML) → sumário → placar → fontes.
 * Gráficos, tabelas e simuladores de cada capítulo são hidratados depois, sob demanda
 * (components/capitulos.js).
 */
import '@fontsource-variable/source-serif-4/opsz.css';
import '@fontsource-variable/source-serif-4/opsz-italic.css';
import '@fontsource-variable/inter/index.css';
import './styles/tokens.css';
import './styles/base.css';
import './styles/componentes.css';
import './styles/moldura.css';

import { iniciarTema } from './lib/tema.js';
import { montarMoldura } from './components/moldura.js';
import { inserirCapitulos } from './components/capitulos.js';
import { montarSumario } from './components/sumario.js';
import { montarPlacar } from './components/placar.js';
import { iniciarFontes } from './components/fontes.js';
import { iniciarNavegacao } from './components/navegacao.js';
import { hidratarKpis } from './components/kpi.js';
import { VEREDITOS, seloVeredito } from './components/veredito.js';

iniciarTema(document.getElementById('botao-tema'));
montarMoldura({ pagina: 'relatorio', raiz: './', estrelaNoTopo: document.getElementById('estrela-topo') });

// legenda de vereditos em "Como ler"
const legenda = document.getElementById('legenda-vereditos');
for (const [k, v] of Object.entries(VEREDITOS)) {
  if (k === 'pendente') continue;
  const li = document.createElement('li');
  const d = document.createElement('div');
  d.append(seloVeredito(k));
  const p = document.createElement('span');
  p.textContent = v.descricao;
  li.append(d, p);
  legenda.append(li);
}

hidratarKpis(document.getElementById('capa'));

const capitulos = inserirCapitulos(document.getElementById('capitulos'));

montarSumario(
  [...document.querySelectorAll('#sumario-lateral ol, #sumario-movel ol')],
  [
    { id: 'capa', rotulo: 'Início', n: '' },
    { id: 'resumo', rotulo: 'Resumo em 1 minuto', n: '' },
    { id: 'como-ler', rotulo: 'Como ler este relatório', n: '' },
    { id: 'placar', rotulo: 'Placar das alegações', n: '' },
    ...capitulos.map((c) => ({ id: c.id, rotulo: c.curto, n: String(c.numero) })),
  ],
  document.getElementById('sumario-movel'),
);

montarPlacar(document.getElementById('placar-grade'), capitulos);
const alinharHash = iniciarNavegacao(document);
// Fontes são criadas assincronamente, inclusive seus destinos #fonte-….
iniciarFontes(document).then(() => { if (location.hash) alinharHash(); });
