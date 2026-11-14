import { createBrowserRouter } from "react-router";
import { Layout } from "./layout/Layout";
import { EmConstrucao } from "./paginas/EmConstrucao";
import { Entrar } from "./paginas/Entrar";
import { ErroDeRota } from "./paginas/ErroDeRota";
import { NaoEncontrada } from "./paginas/NaoEncontrada";
import { VisaoGeral } from "./paginas/VisaoGeral";
import { relativo, ROTAS } from "./rotas";
import { RotaProtegida } from "./sessao/RotaProtegida";

// Entrar é a única tela pública. Todas as outras passam pela RotaProtegida (GET /eu)
// e ficam dentro do Layout. A rota "*" também fica dentro: só quem tem sessão vê o
// 404; sem sessão, qualquer endereço leva a Entrar.
// O errorElement da raiz (ErroDeRota) também recebe a falha ao baixar um pedaço de
// código carregado sob demanda (React.lazy da Visão geral): o erro é lançado na
// renderização e sobe até ele, em vez de deixar a tela em branco.
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
              { index: true, element: <VisaoGeral /> },
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
