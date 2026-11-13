import { ArrowLeft, SearchX } from "lucide-react";
import { Link, useLocation } from "react-router";
import { Button } from "@/components/ui/button";
import { TituloPagina } from "@/layout/TituloPagina";
import { ROTAS } from "@/rotas";

/** Rota que não existe (dentro do layout: só quem tem sessão chega aqui). */
export function NaoEncontrada() {
  const { pathname } = useLocation();
  return (
    <div className="flex flex-col gap-6">
      <TituloPagina>Página não encontrada</TituloPagina>
      <div className="flex flex-col gap-4 rounded-xl border bg-card p-6 text-sm text-card-foreground">
        <p className="flex items-start gap-3">
          <SearchX aria-hidden className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
          <span>
            Não existe nenhuma tela em <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs break-all">{pathname}</code>.
          </span>
        </p>
        <Button asChild variant="outline" size="sm" className="self-start">
          <Link to={ROTAS.visaoGeral}>
            <ArrowLeft aria-hidden />
            Voltar para a visão geral
          </Link>
        </Button>
      </div>
    </div>
  );
}
