import { Carregando } from "@/componentes/Carregando";
import { Skeleton } from "@/components/ui/skeleton";
import { EsqueletoTabela } from "@/visao-geral/Esqueletos";

// Fallbacks do Suspense das telas Campanhas e Campanha: ficam no pedaço principal do
// build. Um único status por tela (os blocos internos ficam só visuais).

function EsqueletoCartao() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-4 w-80 max-w-full" />
      <Skeleton className="h-9 w-56" />
    </div>
  );
}

/** Tela Campanhas: cartão de sincronização + lista. */
export function EsqueletoCampanhas() {
  return (
    <Carregando texto="Carregando as campanhas…" comStatus className="flex flex-col gap-6">
      <EsqueletoCartao />
      <EsqueletoTabela linhas={3} comStatus={false} />
    </Carregando>
  );
}

/** Tela Campanha: resumo da campanha + tabela diária. */
export function EsqueletoCampanha() {
  return (
    <Carregando texto="Carregando a campanha…" comStatus className="flex flex-col gap-6">
      <EsqueletoCartao />
      <EsqueletoTabela linhas={8} comStatus={false} />
    </Carregando>
  );
}
