import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { Vitrine } from "./paginas/Vitrine";
import { ProvedorTema } from "./tema/ProvedorTema";

// Provisório: renderiza a vitrine para aprovação do visual. O roteador, o layout e
// as telas de entrar e visão geral entram na próxima etapa da Fase 1.
createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <ProvedorTema>
      <Vitrine />
    </ProvedorTema>
  </StrictMode>,
);
