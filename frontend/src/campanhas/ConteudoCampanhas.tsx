import { Megaphone } from "lucide-react";
import { generatePath, Link } from "react-router";
import { useCampanhas } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { EstadoVazio } from "@/componentes/EstadoVazio";
import { TabelaRolavel } from "@/componentes/TabelaRolavel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatarInteiro } from "@/lib/formatar";
import { ROTAS } from "@/rotas";
import { EsqueletoTabela } from "@/visao-geral/Esqueletos";
import { formatarOrcamento, textoSincronizacao } from "./dados";
import { SeloStatus } from "./SeloStatus";
import { Sincronizacao } from "./Sincronizacao";

/** Conteúdo da tela Campanhas (pedaço próprio no build; o h1 fica na página). */
export default function ConteudoCampanhas() {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Sincronização</h2>
          </CardTitle>
          <CardDescription>
            Traz nome, status e orçamento das campanhas da conta de teste do Google Ads. As métricas diárias são sintéticas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Sincronizacao />
        </CardContent>
      </Card>
      <ListaCampanhas />
    </div>
  );
}

function ListaCampanhas() {
  const consulta = useCampanhas();

  if (consulta.isPending) return <EsqueletoTabela linhas={3} texto="Carregando a lista de campanhas…" />;
  if (consulta.isError) {
    return <EstadoErro erro={consulta.error} aoTentarNovamente={() => void consulta.refetch()} tentando={consulta.isFetching} />;
  }

  const campanhas = consulta.data;
  if (campanhas.length === 0) {
    return (
      <EstadoVazio
        Icone={Megaphone}
        titulo="Nenhuma campanha ainda"
        texto="Use “Sincronizar com o Google Ads” para trazer as campanhas da conta."
      />
    );
  }

  const quantidade = campanhas.length === 1 ? "1 campanha" : `${formatarInteiro(campanhas.length)} campanhas`;
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Campanhas da conta</h2>
        </CardTitle>
        <CardDescription>{quantidade}, em ordem alfabética. Abra uma campanha para ver as métricas diárias.</CardDescription>
      </CardHeader>
      <CardContent>
        <TabelaRolavel legenda={`Campanhas da conta do Google Ads: ${quantidade}`}>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Campanha</TableHead>
              <TableHead scope="col">Status</TableHead>
              <TableHead scope="col" className="text-right">
                Orçamento diário
              </TableHead>
              <TableHead scope="col">ID no Google Ads</TableHead>
              <TableHead scope="col">Última sincronização</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {campanhas.map((c) => (
              <TableRow key={c.id}>
                <TableHead scope="row" className="font-medium">
                  <Link
                    to={generatePath(ROTAS.campanha, { id: String(c.id) })}
                    className="text-primary underline-offset-4 hover:underline"
                  >
                    {c.nome}
                  </Link>
                </TableHead>
                <TableCell>
                  <SeloStatus status={c.status} />
                </TableCell>
                <TableCell className="text-right whitespace-nowrap tabular-nums">{formatarOrcamento(c.orcamento_micros)}</TableCell>
                <TableCell className="tabular-nums">{c.google_campaign_id}</TableCell>
                <TableCell className="whitespace-nowrap">{textoSincronizacao(c.sincronizada_em)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </TabelaRolavel>
      </CardContent>
    </Card>
  );
}
