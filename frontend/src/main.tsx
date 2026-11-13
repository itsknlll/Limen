import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";
import "./index.css";
import { criarClienteQuery } from "./api/consultas";
import { Notificacoes } from "./componentes/Notificacoes";
import { roteador } from "./roteador";
import { ProvedorTema } from "./tema/ProvedorTema";

const clienteQuery = criarClienteQuery();

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <ProvedorTema>
      <QueryClientProvider client={clienteQuery}>
        <RouterProvider router={roteador} />
        <Notificacoes />
      </QueryClientProvider>
    </ProvedorTema>
  </StrictMode>,
);
