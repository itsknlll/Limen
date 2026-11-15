import { LogIn, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { URL_LOGIN_GOOGLE } from "@/api/cliente";
import { useEu, useSincronizar } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { mensagemSincronizacao } from "./dados";

/**
 * Botão "Sincronizar com o Google Ads" (POST /campanhas/sincronizar) e os erros dele.
 * - aria-disabled em vez de disabled durante o pedido: um botão focado que vira disabled
 *   perde o foco (vai para o <body>). O clique repetido é ignorado aqui.
 * - O role="status" existe sempre (vazio fora do pedido): uma região viva criada junto
 *   com o texto nem sempre é anunciada.
 * - Erro: EstadoErro com a ação que o tipo pede (cota com o Retry-After real, revogado com
 *   "Reconectar Google"). Sem Google conectado e com erro, só o EstadoErro aparece: ele já
 *   tem a ação de reconectar, e o motivo não some quando o /eu muda.
 */
export function Sincronizacao() {
  const { data: usuario } = useEu();
  const sincronizar = useSincronizar();
  const pendente = sincronizar.isPending;
  const conectado = usuario?.google_conectado ?? true;

  const aoClicar = () => {
    if (pendente) return;
    sincronizar.mutate(undefined, {
      onSuccess: (resposta) => toast.success(mensagemSincronizacao(resposta.campanhas_sincronizadas)),
    });
  };

  return (
    <div className="flex flex-col items-start gap-3">
      {conectado ? (
        <Button onClick={aoClicar} aria-disabled={pendente} className="aria-disabled:cursor-wait aria-disabled:opacity-70">
          <RefreshCw aria-hidden className={cn(pendente && "animate-spin")} />
          {pendente ? "Sincronizando…" : "Sincronizar com o Google Ads"}
        </Button>
      ) : (
        !sincronizar.isError && (
          <div className="flex flex-col items-start gap-2 text-sm">
            <p className="text-muted-foreground">O Limen não tem acesso à sua conta do Google Ads. Conecte para trazer as campanhas.</p>
            <Button asChild>
              <a href={URL_LOGIN_GOOGLE}>
                <LogIn aria-hidden />
                Conectar Google
              </a>
            </Button>
          </div>
        )
      )}
      <span role="status" className="sr-only">
        {pendente ? "Sincronizando as campanhas com o Google Ads…" : ""}
      </span>
      {sincronizar.isError && <EstadoErro erro={sincronizar.error} className="w-full" />}
    </div>
  );
}
