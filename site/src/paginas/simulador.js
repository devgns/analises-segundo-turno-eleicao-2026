/**
 * Página do simulador (site/simulador/index.html, gerada por scripts/gerar_simulador.py).
 * O simulador traz CSS e JS próprios embutidos; aqui só entram a moldura do site
 * (abas, tema, estrela, rodapé) e seus estilos, que não dependem de base.css.
 */
import '@fontsource-variable/inter/index.css';
import '../styles/tokens.css';
import '../styles/moldura.css';
import { montarMoldura } from '../components/moldura.js';

montarMoldura({ pagina: 'simulador', raiz: '../' });
