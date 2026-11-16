import { Carregando } from "@/componentes/Carregando";
import { Skeleton } from "@/components/ui/skeleton";
import { EsqueletoTabela } from "@/visao-geral/Esqueletos";

// Fallback do Suspense da tela Avaliações: fica no pedaço principal do build. Um único
// status para a tela (os blocos internos ficam só visuais). Depois que o conteúdo chega,
// o histórico tem esqueleto e status próprios (uma consulta, um status).

/** Formulário de execução + histórico. Sem o h1: ele fica fora do Suspense. */
export function EsqueletoAvaliacoes() {
  return (
    <Carregando texto="Carregando as avaliações…" comStatus className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-xl border bg-card p-4">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-96 max-w-full" />
        <Skeleton className="h-9 w-full max-w-md" />
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
        <Skeleton className="h-5 w-56" />
        <Skeleton className="h-9 w-40" />
      </div>
      <EsqueletoTabela linhas={5} comStatus={false} />
    </Carregando>
  );
}
