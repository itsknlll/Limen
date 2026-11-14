import { TableIcon } from "lucide-react";
import { useId, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Rectangle,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type BarShapeProps,
  type TooltipContentProps,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatarData, formatarDiaMes, formatarInteiro, formatarPeriodo } from "@/lib/formatar";
import { usePrefereMenosMovimento } from "@/lib/movimento";
import { aparenciaDaRegra } from "@/regras/aparencia";
import { SeloRegra } from "@/regras/SeloRegra";
import { codigoNoTopo, codigosDaSerie, descricaoGrafico, serieAlertasPorDia, type PontoSerie, type Resumo } from "./dados";

// Alertas por dia, empilhados por regra. Acessibilidade: o SVG fica aria-hidden (e sem
// o accessibilityLayer do Recharts, que o tornaria focável dentro de uma área escondida);
// quem não vê o gráfico tem a descrição em texto e a tabela com os mesmos números.
// Marcas conforme a skill dataviz: barra ≤ 24 px, 2 px de fundo entre segmentos,
// canto de 4 px só na ponta da pilha, eixo Y só com inteiros, grade discreta.

const COR_EIXO = "var(--muted-foreground)";
const COR_GRADE = "var(--border)";
const COR_SUPERFICIE = "var(--card)"; // o "vão" de 2 px entre segmentos tem a cor do cartão

function Segmento({ x, y, width, height, fill, topo }: BarShapeProps & { topo: boolean }) {
  return (
    <Rectangle
      x={x}
      y={y}
      width={width}
      height={height}
      fill={fill}
      radius={topo ? [4, 4, 0, 0] : 0}
      stroke={COR_SUPERFICIE}
      strokeWidth={2}
    />
  );
}

function DicaDoDia({
  active,
  payload,
  codigos,
  nomes,
}: Pick<TooltipContentProps, "active" | "payload"> & { codigos: string[]; nomes: Record<string, string> }) {
  const ponto = payload?.[0]?.payload as PontoSerie | undefined;
  if (!active || !ponto) return null;
  return (
    <div className="flex min-w-40 flex-col gap-1.5 rounded-lg border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <p className="font-medium">{formatarData(ponto.data)}</p>
      <ul className="flex flex-col gap-1">
        {codigos.map((codigo) => (
          <li key={codigo} className="flex items-center gap-2">
            <span aria-hidden className="h-0.5 w-3 shrink-0 rounded-full" style={{ background: aparenciaDaRegra(codigo).corGrafico }} />
            <span className="w-5 font-semibold tabular-nums">{formatarInteiro(ponto.valores[codigo] ?? 0)}</span>
            <span className="text-muted-foreground">
              {codigo}
              {nomes[codigo] ? ` · ${nomes[codigo]}` : ""}
            </span>
          </li>
        ))}
      </ul>
      <p className="border-t pt-1.5 text-muted-foreground">
        Total: <span className="font-semibold text-popover-foreground tabular-nums">{formatarInteiro(ponto.total)}</span>
      </p>
    </div>
  );
}

function Legenda({ codigos, nomes }: { codigos: string[]; nomes: Record<string, string> }) {
  return (
    <ul aria-label="Legenda" className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs">
      {codigos.map((codigo) => {
        const { Icone, corCss, corGrafico, nomePadrao } = aparenciaDaRegra(codigo);
        const nome = nomes[codigo] ?? nomePadrao;
        return (
          <li key={codigo} className="flex items-center gap-1.5">
            {/* Amostra = a cor da barra (corGrafico); o texto usa a cor de texto (corCss). */}
            <span aria-hidden className="size-3 shrink-0 rounded-[3px]" style={{ background: corGrafico }} />
            <span className="flex items-center gap-1" style={{ color: corCss }}>
              <Icone aria-hidden className="size-3.5 shrink-0" />
              <span className="font-semibold">{codigo}</span>
              {nome && <span>{nome}</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function GraficoAlertasPorDia({ resumo, className }: { resumo: Resumo; className?: string }) {
  const menosMovimento = usePrefereMenosMovimento();
  const [mostrarTabela, setMostrarTabela] = useState(false);
  const idTabela = useId();

  const { alertas, metricas } = resumo;
  const codigos = codigosDaSerie(alertas.por_regra, alertas.por_dia);
  const serie = serieAlertasPorDia(alertas.por_dia, metricas.inicio, metricas.fim, codigos);
  const nomes = Object.fromEntries(alertas.por_regra.map((r) => [r.codigo, r.nome]));
  const periodo = formatarPeriodo(metricas.inicio, metricas.fim);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>
          <h2>Alertas por dia</h2>
        </CardTitle>
        <CardDescription>{descricaoGrafico(resumo)}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Legenda codigos={codigos} nomes={nomes} />

        <div aria-hidden="true" className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={serie} accessibilityLayer={false} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke={COR_GRADE} />
              <XAxis
                dataKey="data"
                tickFormatter={formatarDiaMes}
                tickLine={false}
                axisLine={{ stroke: COR_GRADE }}
                tick={{ fill: COR_EIXO, fontSize: 12 }}
                minTickGap={16}
              />
              <YAxis
                allowDecimals={false}
                tickLine={false}
                axisLine={false}
                tick={{ fill: COR_EIXO, fontSize: 12 }}
                width={40}
              />
              <Tooltip
                cursor={{ fill: "var(--muted)", opacity: 0.6 }}
                isAnimationActive={!menosMovimento}
                content={({ active, payload }) => (
                  <DicaDoDia active={active} payload={payload} codigos={codigos} nomes={nomes} />
                )}
              />
              {codigos.map((codigo) => (
                <Bar
                  key={codigo}
                  name={codigo}
                  dataKey={(ponto: PontoSerie) => ponto.valores[codigo] ?? 0}
                  stackId="alertas"
                  fill={aparenciaDaRegra(codigo).corGrafico}
                  maxBarSize={24}
                  isAnimationActive={!menosMovimento}
                  shape={(props: BarShapeProps) => (
                    <Segmento {...props} topo={codigoNoTopo((props.payload as PontoSerie).valores, codigos) === codigo} />
                  )}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="self-start"
          aria-expanded={mostrarTabela}
          aria-controls={idTabela}
          onClick={() => setMostrarTabela((v) => !v)}
        >
          <TableIcon aria-hidden />
          {mostrarTabela ? "Ocultar tabela" : "Ver dados em tabela"}
        </Button>

        {/* Sempre no DOM (hidden quando fechada), para o aria-controls apontar para algo que existe. */}
        <div id={idTabela} hidden={!mostrarTabela}>
          <Table>
            <caption className="sr-only">Alertas por dia e por regra{periodo ? `, ${periodo}` : ""}</caption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Dia</TableHead>
                {codigos.map((codigo) => (
                  <TableHead key={codigo} scope="col" className="text-right">
                    <SeloRegra codigo={codigo} />
                  </TableHead>
                ))}
                <TableHead scope="col" className="text-right">
                  Total
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {serie.map((ponto) => (
                <TableRow key={ponto.data}>
                  <TableHead scope="row" className="font-normal">
                    {formatarData(ponto.data)}
                  </TableHead>
                  {codigos.map((codigo) => (
                    <TableCell key={codigo} className="text-right tabular-nums">
                      {formatarInteiro(ponto.valores[codigo] ?? 0)}
                    </TableCell>
                  ))}
                  <TableCell className="text-right font-medium tabular-nums">{formatarInteiro(ponto.total)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
