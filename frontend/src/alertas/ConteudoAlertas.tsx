import { useSearchParams } from "react-router";
import { useAlertas, useCampanhas, useRegras } from "@/api/consultas";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FiltrosAlertas } from "./FiltrosAlertas";
import { lerFiltros, listaParaFiltro, montarConsultaAlertas, temFiltro } from "./filtros";
import { faseAlertas, textoStatusAlertas } from "./tabela";
import { TabelaAlertas } from "./TabelaAlertas";

/**
 * Conteúdo da tela Alertas (pedaço próprio no build; o h1 fica na página).
 * A URL é a fonte dos filtros: lerFiltros → montarConsultaAlertas → useAlertas; com URL
 * inválida a consulta fica desligada (nenhum pedido). Os filtros ficam sempre visíveis,
 * inclusive com erro na consulta. Um único role="status" para a tela.
 */
export default function ConteudoAlertas() {
  const [params, setParams] = useSearchParams();
  const filtros = lerFiltros(params);
  const campanhas = useCampanhas();
  const regras = useRegras();
  const resultado = montarConsultaAlertas(filtros, listaParaFiltro(campanhas), listaParaFiltro(regras));
  const alertas = useAlertas(resultado.estado === "pronta" ? resultado.consulta : null);
  const fase = faseAlertas(resultado, alertas);

  return (
    <div className="flex flex-col gap-6">
      <span role="status" className="sr-only">
        {textoStatusAlertas(fase)}
      </span>

      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Filtros</h2>
          </CardTitle>
          <CardDescription>O período filtra pelo dia das métricas que geraram o alerta.</CardDescription>
        </CardHeader>
        <CardContent>
          <FiltrosAlertas
            filtros={filtros}
            erros={resultado.estado === "invalida" ? resultado.erros : {}}
            aoEnviar={(busca) => setParams(busca)}
          />
        </CardContent>
      </Card>

      <TabelaAlertas
        fase={fase}
        comFiltro={temFiltro(filtros)}
        regras={regras.data}
        aoTentarNovamente={() => void alertas.refetch()}
        tentando={alertas.isFetching}
      />
    </div>
  );
}
