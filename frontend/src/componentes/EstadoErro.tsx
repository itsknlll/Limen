import { AlertTriangle, LogIn, RefreshCw, RotateCw } from "lucide-react";
import { Link } from "react-router";
import { URL_LOGIN_GOOGLE } from "@/api/cliente";
import { mensagemDoErro } from "@/api/erros";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ROTAS } from "@/rotas";

interface Props {
  erro: unknown;
  /** Necessário para a ação "tentar de novo" aparecer (ex.: refetch da consulta). */
  aoTentarNovamente?: () => void;
  tentando?: boolean;
  className?: string;
}

/**
 * Erro em português, decidido pelo `tipo` (mensagemDoErro), com a ação que o tipo pede:
 * tentar de novo, entrar ou reconectar o Google. role="alert": o leitor de tela anuncia.
 */
export function EstadoErro({ erro, aoTentarNovamente, tentando = false, className }: Props) {
  const { titulo, texto, acao, detalhe } = mensagemDoErro(erro);
  return (
    <div
      role="alert"
      className={cn("flex flex-col gap-3 rounded-xl border bg-card p-4 text-sm text-card-foreground", className)}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle aria-hidden className="mt-0.5 size-5 shrink-0 text-destructive" />
        <div className="flex min-w-0 flex-col gap-1">
          <p className="font-semibold">{titulo}</p>
          <p className="text-muted-foreground">{texto}</p>
          {detalhe && detalhe !== texto && <p className="text-xs break-words text-muted-foreground">Detalhe: {detalhe}</p>}
        </div>
      </div>
      {acao === "tentar_novamente" && aoTentarNovamente && (
        <Button variant="outline" size="sm" className="self-start" onClick={aoTentarNovamente} disabled={tentando}>
          <RotateCw aria-hidden className={cn(tentando && "animate-spin")} />
          {tentando ? "Tentando…" : "Tentar de novo"}
        </Button>
      )}
      {acao === "entrar" && (
        <Button asChild variant="outline" size="sm" className="self-start">
          <Link to={ROTAS.entrar}>
            <LogIn aria-hidden />
            Entrar
          </Link>
        </Button>
      )}
      {acao === "reconectar_google" && (
        <Button asChild size="sm" className="self-start">
          <a href={URL_LOGIN_GOOGLE}>
            <RefreshCw aria-hidden />
            Reconectar Google
          </a>
        </Button>
      )}
    </div>
  );
}
