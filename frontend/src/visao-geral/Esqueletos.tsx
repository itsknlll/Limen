import { Carregando } from "@/componentes/Carregando";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// Esqueletos com o formato do conteúdo (sem salto de layout quando os dados chegam).
// Os blocos são decorativos (aria-hidden); o leitor de tela ouve só o texto de status.
// Ficam no pedaço principal do build: servem de fallback do Suspense da rota.
//
// Um status por região que carrega: usado sozinho (uma consulta carregando), cada
// esqueleto anuncia o seu. Dentro do EsqueletoVisaoGeral, os internos recebem
// comStatus={false} e a página inteira anuncia uma única mensagem.

interface PropsEsqueleto {
  comStatus?: boolean;
  className?: string;
}

export function EsqueletoKpis({ comStatus = true, className }: PropsEsqueleto) {
  return (
    <Carregando texto="Carregando os números…" comStatus={comStatus} className={cn("grid grid-cols-2 gap-4 lg:grid-cols-4", className)}>
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex flex-col gap-3 rounded-xl border bg-card p-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-3 w-32" />
        </div>
      ))}
    </Carregando>
  );
}

export function EsqueletoGrafico({ comStatus = true, className }: PropsEsqueleto) {
  return (
    <Carregando
      texto="Carregando o gráfico…"
      comStatus={comStatus}
      className={cn("flex flex-col gap-4 rounded-xl border bg-card p-4", className)}
    >
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-4 w-72 max-w-full" />
      <Skeleton className="h-64 w-full" />
    </Carregando>
  );
}

export function EsqueletoTabela({
  linhas = 3,
  texto = "Carregando as avaliações…",
  comStatus = true,
  className,
}: PropsEsqueleto & { linhas?: number; texto?: string }) {
  return (
    <Carregando texto={texto} comStatus={comStatus} className={cn("flex flex-col gap-3 rounded-xl border bg-card p-4", className)}>
      <Skeleton className="h-5 w-48" />
      {Array.from({ length: linhas }, (_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </Carregando>
  );
}

/**
 * Tudo o que vem do GET /resumo (KPIs, gráfico, alertas por regra), com um único
 * status: é uma consulta só. As últimas avaliações têm consulta e esqueleto próprios.
 */
export function EsqueletoResumo() {
  return (
    <Carregando texto="Carregando os números da visão geral…" comStatus className="flex flex-col gap-6">
      <EsqueletoKpis comStatus={false} />
      <div className="grid gap-6 lg:grid-cols-3">
        <EsqueletoGrafico comStatus={false} className="lg:col-span-2" />
        <EsqueletoTabela linhas={3} texto="Carregando os alertas por regra…" comStatus={false} />
      </div>
    </Carregando>
  );
}

/**
 * Tela inteira, com um único status (os esqueletos internos ficam só visuais).
 * Sem o h1: ele fica fora do Suspense, para o foco ao navegar não se perder.
 */
export function EsqueletoVisaoGeral() {
  return (
    <Carregando texto="Carregando a visão geral…" comStatus className="flex flex-col gap-6">
      <EsqueletoKpis comStatus={false} />
      <div className="grid gap-6 lg:grid-cols-3">
        <EsqueletoGrafico comStatus={false} className="lg:col-span-2" />
        <EsqueletoTabela linhas={3} texto="Carregando os alertas por regra…" comStatus={false} />
      </div>
      <EsqueletoTabela linhas={5} comStatus={false} />
    </Carregando>
  );
}
