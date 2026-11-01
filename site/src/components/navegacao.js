/** Mantém o destino de uma âncora visível enquanto componentes acima carregam. */
export function iniciarNavegacao(raiz = document) {
  let parar = () => {};

  function alinharHash() {
    parar();
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    if (!id) return;
    const alvo = document.getElementById(id);
    if (!alvo) return;

    let quadro = 0;
    let inatividade;
    const encerrar = () => {
      observer.disconnect();
      clearTimeout(inatividade);
      clearTimeout(prazo);
      cancelAnimationFrame(quadro);
      for (const evento of ['wheel', 'touchstart', 'pointerdown', 'keydown']) {
        window.removeEventListener(evento, encerrar);
      }
    };
    const alinhar = () => {
      cancelAnimationFrame(quadro);
      quadro = requestAnimationFrame(() => alvo.scrollIntoView({ block: 'start', behavior: 'instant' }));
      clearTimeout(inatividade);
      inatividade = setTimeout(encerrar, 1800);
    };
    const observer = new ResizeObserver(alinhar);
    const prazo = setTimeout(encerrar, 8000);
    parar = encerrar;
    for (const evento of ['wheel', 'touchstart', 'pointerdown', 'keydown']) {
      window.addEventListener(evento, encerrar, { passive: true, once: true });
    }
    observer.observe(document.body);
    alinhar();
  }

  window.addEventListener('hashchange', alinharHash);
  // Um clique na mesma âncora não dispara hashchange.
  raiz.addEventListener('click', (e) => {
    const link = e.target.closest?.('a[href^="#"]');
    if (link && link.hash === location.hash) requestAnimationFrame(alinharHash);
  });
  alinharHash();
  return alinharHash;
}
