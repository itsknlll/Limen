import { CalendarX2 } from "lucide-react";
import { useCampanhas, useMetricas } from "@/api/consultas";
import { Carregando } from "@/componentes/Carregando";
import { EstadoErro } from "@/componentes/EstadoErro";
import { EstadoVazio } from "@/componentes/EstadoVazio";
import { TabelaRolavel } from "@/componentes/TabelaRolavel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatarData } from "@/lib/formatar";
import { EsqueletoTabela } from "@/visao-geral/Esqueletos";
import {
  type Campanha,
  type Celula,
  celulaCpc,
  celulaCtr,
  celulaDecimal,
  celulaInteiro,
  celulaMoeda,
  descricaoPeriodo,
  encontrarCampanha,
  formatarOrcamento,
  rotuloOrigem,
  textoAcessivel,
  textoSincronizacao,
} from "./dados";
import { SeloStatus } from "./SeloStatus";

/**
 * Conteúdo da tela Campanha (pedaço próprio no build; o h1 fica na página).
 * O resumo vem da lista de GET /campanhas (não há GET /campanhas/{id}); as métricas
 * diárias, de GET /campanhas/{id}/metricas. As duas consultas correm em paralelo e
 * falham separadas: sem a lista, a tabela continua.
 */
export default function ConteudoCampanha({ campanhaId }: { campanhaId: number }) {
  return (
    <div className="flex flex-col gap-6">
      <ResumoCampanha campanhaId={campanhaId} />
      <MetricasDiarias campanhaId={campanhaId} />
    </div>
  );
}

function ResumoCampanha({ campanhaId }: { campanhaId: number }) {
  const consulta = useCampanhas();

  if (consulta.isPending) {
    return (
      <Carregando texto="Carregando o resumo da campanha…" comStatus className="flex flex-col gap-3 rounded-xl border bg-card p-4">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </Carregando>
    );
  }
  if (consulta.isError) {
    return <EstadoErro erro={consulta.error} aoTentarNovamente={() => void consulta.refetch()} tentando={consulta.isFetching} />;
  }
  // Não encontrada é tratada pela página (ela troca o h1 e não monta este conteúdo).
  const campanha = encontrarCampanha(consulta.data, campanhaId);
  if (campanha === null) return null;
  return <CartaoResumo campanha={campanha} />;
}

function CartaoResumo({ campanha }: { campanha: Campanha }) {
  const itens = [
    ["Status", <SeloStatus key="s" status={campanha.status} />],
    ["Orçamento diário", formatarOrcamento(campanha.orcamento_micros)],
    ["ID no Google Ads", campanha.google_campaign_id],
    ["Última sincronização", textoSincronizacao(campanha.sincronizada_em)],
  ] as const;
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Resumo</h2>
        </CardTitle>
        <CardDescription>Dados da estrutura da campanha, trazidos do Google Ads na sincronização.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          {itens.map(([rotulo, valor]) => (
            <div key={rotulo} className="flex flex-col gap-1">
              <dt className="text-muted-foreground">{rotulo}</dt>
              <dd className="font-medium tabular-nums">{valor}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

/** Célula com "—" ou "N/A": o símbolo fica visível; o leitor de tela ouve o motivo. */
function Valor({ celula }: { celula: Celula }) {
  if (celula.descricao === null) return celula.texto;
  return (
    <>
      <span aria-hidden="true" title={celula.descricao} className="text-muted-foreground">
        {celula.texto}
      </span>
      <span className="sr-only">{textoAcessivel(celula)}</span>
    </>
  );
}

const COLUNAS = ["Impressões", "Cliques", "Custo", "Conversões", "CTR", "CPC"] as const;

function MetricasDiarias({ campanhaId }: { campanhaId: number }) {
  const consulta = useMetricas(campanhaId);

  if (consulta.isPending) return <EsqueletoTabela linhas={8} texto="Carregando as métricas diárias…" />;
  if (consulta.isError) {
    return <EstadoErro erro={consulta.error} aoTentarNovamente={() => void consulta.refetch()} tentando={consulta.isFetching} />;
  }

  const metricas = consulta.data;
  const periodo = descricaoPeriodo(metricas);
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Métricas diárias</h2>
        </CardTitle>
        <CardDescription>
          {periodo === null ? "Nenhum dia registrado." : `${periodo}.`} CTR e CPC calculados pelo banco, com a mesma regra do motor: N/A quando
          indefinidos.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {periodo === null ? (
          <EstadoVazio
            Icone={CalendarX2}
            titulo="Nenhuma métrica para esta campanha"
            texto="Os dias aparecem aqui quando as métricas forem registradas para esta campanha."
          />
        ) : (
          <TabelaRolavel legenda={`Métricas diárias da campanha: ${periodo}`}>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Dia</TableHead>
                {COLUNAS.map((rotulo) => (
                  <TableHead key={rotulo} scope="col" className="text-right">
                    {rotulo}
                  </TableHead>
                ))}
                <TableHead scope="col">Origem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {metricas.map((m) => {
                const celulas = [
                  celulaInteiro(m.impressoes),
                  celulaInteiro(m.cliques),
                  celulaMoeda(m.custo),
                  celulaDecimal(m.conversoes),
                  celulaCtr(m),
                  celulaCpc(m),
                ];
                return (
                  <TableRow key={m.data}>
                    <TableHead scope="row" className="font-medium whitespace-nowrap tabular-nums">
                      {formatarData(m.data)}
                    </TableHead>
                    {celulas.map((celula, i) => (
                      <TableCell key={COLUNAS[i]} className="text-right whitespace-nowrap tabular-nums">
                        <Valor celula={celula} />
                      </TableCell>
                    ))}
                    <TableCell>{rotuloOrigem(m.origem)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </TabelaRolavel>
        )}
      </CardContent>
    </Card>
  );
}
