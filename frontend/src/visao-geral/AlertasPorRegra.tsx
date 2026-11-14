import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatarInteiro } from "@/lib/formatar";
import { SeloRegra } from "@/regras/SeloRegra";
import { textoAlertas, type Resumo } from "./dados";

/**
 * Total de alertas por regra. Regras sem alerta aparecem com 0 (o backend as manda:
 * LEFT JOIN): "existe e não disparou" é informação. <dl>: o leitor de tela ouve cada
 * par regra → total.
 */
export function AlertasPorRegra({ resumo, className }: { resumo: Resumo; className?: string }) {
  const { alertas } = resumo;
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>
          <h2>Alertas por regra</h2>
        </CardTitle>
        <CardDescription>
          {formatarInteiro(alertas.total)} no total, {textoAlertas(alertas)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {alertas.por_regra.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhuma regra cadastrada.</p>
        ) : (
          <dl className="flex flex-col divide-y">
            {alertas.por_regra.map((regra) => (
              <div key={regra.regra_id} className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
                <dt className="flex min-w-0 flex-wrap items-center gap-2">
                  <SeloRegra codigo={regra.codigo} nome={regra.nome} comNome />
                  {!regra.ativa && <Badge variant="outline">desativada</Badge>}
                </dt>
                <dd className="text-lg font-semibold tabular-nums">{formatarInteiro(regra.total)}</dd>
              </div>
            ))}
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
