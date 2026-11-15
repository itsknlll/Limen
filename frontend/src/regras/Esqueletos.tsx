import { Carregando } from "@/componentes/Carregando";
import { Skeleton } from "@/components/ui/skeleton";
import { EsqueletoTabela } from "@/visao-geral/Esqueletos";

// Fallbacks do Suspense das telas de regras. Um único status por tela.

export function EsqueletoRegras() {
  return <EsqueletoTabela linhas={4} texto="Carregando as regras…" />;
}

/** Formulário de nova regra ou de edição (texto diferente em cada caso). */
export function EsqueletoFormulario({ texto }: { texto: string }) {
  return (
    <Carregando texto={texto} comStatus className="flex flex-col gap-4 rounded-xl border bg-card p-4">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-9 w-full max-w-sm" />
      <Skeleton className="h-9 w-full max-w-md" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-9 w-32" />
    </Carregando>
  );
}
