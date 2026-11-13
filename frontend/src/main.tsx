import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Ponto de partida provisório: só prova que a instalação compila.
// Tokens, temas, layout e telas entram nas próximas etapas da Fase 1.
createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <p>Limen</p>
  </StrictMode>,
);
