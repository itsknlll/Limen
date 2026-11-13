import { Navigate, Outlet } from "react-router";
import { ehNaoAutenticado, useEu } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { Skeleton } from "@/components/ui/skeleton";
import { useTituloDocumento } from "@/layout/titulo";
import { ROTAS } from "@/rotas";

/** Estado que a tela Entrar recebe pela navegação. */
export interface EstadoEntrar {
  sessaoEncerrada?: boolean;
}

/**
 * Só deixa passar quem tem sessão no backend (GET /eu).
 * - 401 → Entrar. Se já havia usuário carregado (`data` preenchido, porque um 401 em
 *   outra consulta invalidou /eu), a sessão terminou no meio do uso, e Entrar avisa.
 * - Outro erro (backend parado, 5xx) → tela de erro com "tentar de novo". Não manda
 *   para Entrar: o problema não é falta de login, e o login também falharia.
 */
export function RotaProtegida() {
  const eu = useEu();

  if (eu.isError && ehNaoAutenticado(eu.error)) {
    const estado: EstadoEntrar = { sessaoEncerrada: eu.data !== undefined };
    return <Navigate to={ROTAS.entrar} replace state={estado} />;
  }
  if (eu.isError) return <ErroSessao erro={eu.error} tentar={() => void eu.refetch()} tentando={eu.isFetching} />;
  if (eu.isPending) return <CarregandoSessao />;
  return <Outlet />;
}

function ErroSessao({ erro, tentar, tentando }: { erro: unknown; tentar: () => void; tentando: boolean }) {
  useTituloDocumento("Erro");
  return (
    <main id="conteudo" className="grid min-h-svh place-items-center bg-background px-4">
      <EstadoErro erro={erro} aoTentarNovamente={tentar} tentando={tentando} className="w-full max-w-md" />
    </main>
  );
}

/** Esqueleto com o formato do layout, enquanto /eu responde. */
function CarregandoSessao() {
  return (
    <div role="status" aria-label="Carregando" className="min-h-svh bg-background">
      <div className="fixed inset-y-0 left-0 hidden w-60 flex-col gap-6 border-r bg-sidebar px-3 py-4 md:flex">
        <Skeleton className="h-8 w-36" />
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      </div>
      <div className="md:pl-60">
        <div className="flex h-14 items-center gap-2 border-b px-4 md:px-8">
          <Skeleton className="h-6 w-56" />
          <Skeleton className="ml-auto size-8" />
        </div>
        <div className="flex flex-col gap-4 px-4 py-6 md:px-8 md:py-8">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    </div>
  );
}
