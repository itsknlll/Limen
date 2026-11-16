import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FormularioAvaliacao } from "./FormularioAvaliacao";
import { HistoricoAvaliacoes } from "./HistoricoAvaliacoes";

/**
 * Conteúdo da tela Avaliações (pedaço próprio no build; o h1 fica na página).
 * Formulário e histórico são independentes: um erro em um não esconde o outro.
 */
export default function ConteudoAvaliacoes() {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Executar avaliação</h2>
          </CardTitle>
          <CardDescription>
            O motor avalia as métricas diárias com as regras ativas. Um alerta já gerado não se repete.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FormularioAvaliacao />
        </CardContent>
      </Card>
      <HistoricoAvaliacoes />
    </div>
  );
}
