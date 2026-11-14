import { ListChecks } from "lucide-react";
import { Link } from "react-router";
import { useAvaliacoes } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { EstadoVazio } from "@/componentes/EstadoVazio";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatarDataHora, formatarInteiro } from "@/lib/formatar";
import { ROTAS } from "@/rotas";
import { textoDuracao, textoParametros } from "./dados";
import { EsqueletoTabela } from "./Esqueletos";

const LIMITE = 5;

const COLUNAS_NUMERICAS = [
  ["registros_avaliados", "Avaliados"],
  ["registros_rejeitados", "Rejeitados"],
  ["alertas_gerados", "Gerados"],
  ["alertas_ja_existentes", "Já existentes"],
] as const;

/**
 * As últimas avaliações, com consulta própria: se ela falhar, KPIs e gráfico continuam.
 * Parâmetros NULL (antes da migração 0003) aparecem como "não registrado".
 */
export function UltimasAvaliacoes({ className }: { className?: string }) {
  const consulta = useAvaliacoes(LIMITE);

  if (consulta.isPending) return <EsqueletoTabela linhas={LIMITE} className={className} />;
  if (consulta.isError) {
    return (
      <EstadoErro
        erro={consulta.error}
        aoTentarNovamente={() => void consulta.refetch()}
        tentando={consulta.isFetching}
        className={className}
      />
    );
  }

  const avaliacoes = consulta.data;
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>
          <h2>Últimas avaliações</h2>
        </CardTitle>
        <CardDescription>As {LIMITE} mais recentes, da mais nova para a mais antiga.</CardDescription>
        <CardAction>
          <Button asChild variant="link" size="sm">
            <Link to={ROTAS.avaliacoes}>Ver todas</Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {avaliacoes.length === 0 ? (
          <EstadoVazio
            Icone={ListChecks}
            titulo="Nenhuma avaliação ainda"
            texto="Quando o motor de regras for executado, cada execução aparece aqui com os números dela."
            acao={{ rotulo: "Ir para Avaliações", para: ROTAS.avaliacoes }}
          />
        ) : (
          <Table>
            <caption className="sr-only">Últimas avaliações do motor de regras</caption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Nº</TableHead>
                <TableHead scope="col">Início</TableHead>
                {COLUNAS_NUMERICAS.map(([, rotulo]) => (
                  <TableHead key={rotulo} scope="col" className="text-right">
                    {rotulo}
                  </TableHead>
                ))}
                <TableHead scope="col" className="text-right">
                  Motor
                </TableHead>
                <TableHead scope="col">Parâmetros</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {avaliacoes.map((a) => (
                <TableRow key={a.id}>
                  <TableHead scope="row" className="font-medium tabular-nums">
                    {a.id}
                  </TableHead>
                  <TableCell className="whitespace-nowrap">{formatarDataHora(a.iniciada_em)}</TableCell>
                  {COLUNAS_NUMERICAS.map(([campo]) => (
                    <TableCell key={campo} className="text-right tabular-nums">
                      {formatarInteiro(a[campo])}
                    </TableCell>
                  ))}
                  <TableCell className="text-right whitespace-nowrap tabular-nums">{textoDuracao(a.duracao_motor_ms)}</TableCell>
                  <TableCell className={a.incluir_pausadas === null ? "text-muted-foreground italic" : undefined}>
                    {textoParametros(a)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
