import { RotateCw } from "lucide-react";
import { useEffect } from "react";
import { useRouteError } from "react-router";
import { Button } from "@/components/ui/button";
import { useTituloDocumento } from "@/layout/titulo";

/**
 * errorElement do roteador: erro inesperado ao renderizar uma tela (bug no frontend).
 * Substitui a página padrão do React Router, que é em inglês. O erro vai para o
 * console para depuração; a tela só oferece recarregar.
 */
export function ErroDeRota() {
  const erro = useRouteError();
  useTituloDocumento("Erro");
  useEffect(() => console.error(erro), [erro]);
  return (
    <main id="conteudo" className="grid min-h-svh place-items-center bg-background px-4 text-foreground">
      <div role="alert" className="flex w-full max-w-md flex-col gap-3 rounded-xl border bg-card p-6 text-sm">
        <h1 className="text-lg font-semibold">Algo deu errado nesta tela</h1>
        <p className="text-muted-foreground">
          Um erro inesperado impediu a página de abrir. Recarregue; se continuar, o detalhe está no console do
          navegador.
        </p>
        <Button variant="outline" size="sm" className="self-start" onClick={() => window.location.reload()}>
          <RotateCw aria-hidden />
          Recarregar
        </Button>
      </div>
    </main>
  );
}
