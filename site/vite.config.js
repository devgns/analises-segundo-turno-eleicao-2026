import { defineConfig } from 'vite';
import { resolve } from 'node:path';

// base './' → os caminhos gerados são relativos, então o site funciona em
// qualquer subcaminho do GitHub Pages (https://usuario.github.io/<repo>/).
// Duas páginas: o relatório (raiz) e o simulador (simulador/).
export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
    target: 'es2022',
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      input: {
        relatorio: resolve(import.meta.dirname, 'index.html'),
        simulador: resolve(import.meta.dirname, 'simulador/index.html'),
      },
    },
  },
  worker: {
    format: 'es',
  },
});
