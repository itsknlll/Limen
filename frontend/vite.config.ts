/// <reference types="vitest/config" />
import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const BACKEND = "http://localhost:8080";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "src") },
  },
  server: {
    port: 5173,
    strictPort: true,
    // A ordem importa: o Vite usa a primeira chave que casar com a URL.
    proxy: {
      // OAuth: o caminho é o mesmo no backend (bate com a URI cadastrada no Google).
      "/api/oauth": { target: BACKEND },
      // Demais rotas: o backend não tem o prefixo /api; ele existe só para não
      // colidir com as rotas do React (ex.: /alertas é tela e também endpoint).
      "/api": {
        target: BACKEND,
        rewrite: (caminho) => caminho.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    // Só funções puras: sem DOM, sem rede.
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
