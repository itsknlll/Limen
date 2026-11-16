import { createBrowserRouter } from "react-router";
import { Layout } from "./layout/Layout";
import { Alertas } from "./paginas/Alertas";
import { Avaliacoes } from "./paginas/Avaliacoes";
import { Campanha } from "./paginas/Campanha";
import { Campanhas } from "./paginas/Campanhas";
import { Entrar } from "./paginas/Entrar";
import { ErroDeRota } from "./paginas/ErroDeRota";
import { NaoEncontrada } from "./paginas/NaoEncontrada";
import { RegraEditar } from "./paginas/RegraEditar";
import { RegraNova } from "./paginas/RegraNova";
import { Regras } from "./paginas/Regras";
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
              { path: relativo(ROTAS.campanhas), element: <Campanhas /> },
              { path: relativo(ROTAS.campanha), element: <Campanha /> },
              { path: relativo(ROTAS.regras), element: <Regras /> },
              { path: relativo(ROTAS.regraNova), element: <RegraNova /> },
              { path: relativo(ROTAS.regraEditar), element: <RegraEditar /> },
              { path: relativo(ROTAS.avaliacoes), element: <Avaliacoes /> },
              { path: relativo(ROTAS.alertas), element: <Alertas /> },
              { path: "*", element: <NaoEncontrada /> },
            ],
          },
        ],
      },
    ],
  },
]);
