import { createBrowserRouter } from "react-router";
import { Layout } from "./layout/Layout";
import { EmConstrucao } from "./paginas/EmConstrucao";
import { Entrar } from "./paginas/Entrar";
import { ErroDeRota } from "./paginas/ErroDeRota";
import { NaoEncontrada } from "./paginas/NaoEncontrada";
import { relativo, ROTAS } from "./rotas";
import { RotaProtegida } from "./sessao/RotaProtegida";

// Entrar é a única tela pública. Todas as outras passam pela RotaProtegida (GET /eu)
// e ficam dentro do Layout. A rota "*" também fica dentro: só quem tem sessão vê o
// 404; sem sessão, qualquer endereço leva a Entrar.
export const roteador = createBrowserRouter([
  {
    errorElement: <ErroDeRota />,
    children: [
      { path: ROTAS.entrar, element: <Entrar /> },
      {
        element: <RotaProtegida />,
        children: [
          {
            element: <Layout />,
            children: [
              // Provisório: a Visão geral entra na etapa 4 desta fase.
              { index: true, element: <EmConstrucao titulo="Visão geral" previsao="etapa 4 da Fase 1" /> },
              { path: relativo(ROTAS.campanhas), element: <EmConstrucao titulo="Campanhas" previsao="Fase 2" /> },
              { path: relativo(ROTAS.campanha), element: <EmConstrucao titulo="Campanha" previsao="Fase 2" /> },
              { path: relativo(ROTAS.regras), element: <EmConstrucao titulo="Regras" previsao="Fase 3" /> },
              { path: relativo(ROTAS.avaliacoes), element: <EmConstrucao titulo="Avaliações" previsao="Fase 3" /> },
              { path: relativo(ROTAS.alertas), element: <EmConstrucao titulo="Alertas" previsao="Fase 4" /> },
              { path: "*", element: <NaoEncontrada /> },
            ],
          },
        ],
      },
    ],
  },
]);
