import { ListChecks } from "lucide-react";
import { useAvaliacoes, useCampanhas } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { EstadoVazio } from "@/componentes/EstadoVazio";
import { TabelaRolavel } from "@/componentes/TabelaRolavel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EsqueletoTabela } from "@/visao-geral/Esqueletos";
import { celulasHistorico } from "./historico";

const LIMITE = 50;
const AUSENTE = "text-muted-foreground italic";

/**
 * Histórico de GET /avaliacoes, com consulta própria: se falhar, o formulário continua.
 * O nome da campanha vem de GET /campanhas (já em cache pelo formulário); se a lista não
 * vier, a célula mostra o número. Parâmetros anteriores à 0003: "não registrado", em itálico.
 */
export function HistoricoAvaliacoes() {
  const consulta = useAvaliacoes(LIMITE);
  const campanhas = useCampanhas();

  if (consulta.isPending) return <EsqueletoTabela linhas={5} texto="Carregando o histórico das avaliações…" />;
  if (consulta.isError) {
    return (
      <EstadoErro erro={consulta.error} aoTentarNovamente={() => void consulta.refetch()} tentando={consulta.isFetching} />
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Histórico</h2>
        </CardTitle>
        <CardDescription>As {LIMITE} execuções mais recentes, da mais nova para a mais antiga.</CardDescription>
      </CardHeader>
      <CardContent>
        {consulta.data.length === 0 ? (
          <EstadoVazio
            Icone={ListChecks}
            titulo="Nenhuma avaliação ainda"
            texto="Execute a primeira avaliação no formulário acima: cada execução aparece aqui com os números dela."
          />
        ) : (
          <TabelaRolavel legenda="Histórico das avaliações do motor de regras">
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Nº</TableHead>
                <TableHead scope="col">Data</TableHead>
                <TableHead scope="col">Período</TableHead>
                <TableHead scope="col">Campanha</TableHead>
                <TableHead scope="col">Incluiu pausadas</TableHead>
                <TableHead scope="col" className="text-right">
                  Alertas novos
                </TableHead>
                <TableHead scope="col" className="text-right">
                  Já existentes
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {consulta.data.map((a) => {
                const c = celulasHistorico(a, campanhas.data);
                const ausente = c.parametrosAusentes ? AUSENTE : undefined;
                return (
                  <TableRow key={a.id}>
                    <TableHead scope="row" className="font-medium tabular-nums">
                      {a.id}
                    </TableHead>
                    <TableCell className="whitespace-nowrap">{c.data}</TableCell>
                    <TableCell className={ausente}>{c.periodo}</TableCell>
                    <TableCell className={ausente}>{c.campanha}</TableCell>
                    <TableCell className={ausente}>{c.pausadas}</TableCell>
                    <TableCell className="text-right tabular-nums">{c.alertasGerados}</TableCell>
                    <TableCell className="text-right tabular-nums">{c.alertasJaExistentes}</TableCell>
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
