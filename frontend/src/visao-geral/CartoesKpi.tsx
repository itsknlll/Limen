import { useId } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatarInteiro } from "@/lib/formatar";
import { CLASSE_NUMERO } from "./classes";
import { textoAlertas, textoCampanhas, textoMetricas, textoRegras, type Resumo } from "./dados";

function Kpi({ titulo, valor, detalhe }: { titulo: string; valor: number; detalhe: string }) {
  const id = useId();
  return (
    <Card size="sm" role="group" aria-labelledby={id}>
      <CardHeader>
        <CardDescription id={id}>{titulo}</CardDescription>
        <CardTitle className={CLASSE_NUMERO}>{formatarInteiro(valor)}</CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{detalhe}</CardContent>
    </Card>
  );
}

/**
 * Os quatro números da visão geral. O de Alertas diz de quantas avaliações vieram
 * (alertas.avaliacoes): o 27 soma duas execuções e não pode ser lido como os 18 da
 * primeira.
 */
export function CartoesKpi({ resumo }: { resumo: Resumo }) {
  const { campanhas, regras, metricas, alertas } = resumo;
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Kpi titulo="Campanhas" valor={campanhas.total} detalhe={textoCampanhas(campanhas.por_status)} />
      <Kpi titulo="Regras" valor={regras.total} detalhe={textoRegras(regras)} />
      <Kpi titulo="Registros de métricas" valor={metricas.registros} detalhe={textoMetricas(metricas)} />
      <Kpi titulo="Alertas" valor={alertas.total} detalhe={textoAlertas(alertas)} />
    </div>
  );
}
