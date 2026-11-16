import { Carregando } from "@/componentes/Carregando";
import { Skeleton } from "@/components/ui/skeleton";
import { EsqueletoTabela } from "@/visao-geral/Esqueletos";

// Fallback do Suspense da tela Alertas: fica no pedaço principal do build. Um único
// status para a tela (os blocos internos ficam só visuais). Depois que o conteúdo chega,
// a tela tem um role="status" próprio (textoStatusAlertas).

/** Filtros + tabela. Sem o h1: ele fica fora do Suspense. */
export function EsqueletoAlertas() {
  return (
    <Carregando texto="Carregando os alertas…" comStatus className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-xl border bg-card p-4">
        <Skeleton className="h-5 w-32" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
        <Skeleton className="h-9 w-28" />
      </div>
      <EsqueletoTabela linhas={6} comStatus={false} />
    </Carregando>
  );
}
