import { CircleCheck, LogOut, RefreshCw, UserRound } from "lucide-react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { URL_LOGIN_GOOGLE } from "@/api/cliente";
import { useEu, useSair } from "@/api/consultas";
import { mensagemDoErro } from "@/api/erros";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatarIdConta } from "@/lib/formatar";
import { ROTAS } from "@/rotas";

/** Nome, e-mail, estado da conexão com o Google e o botão Sair. */
export function MenuUsuario() {
  const { data: usuario } = useEu();
  const sair = useSair();
  const navegar = useNavigate();

  // A RotaProtegida só renderiza o layout com /eu carregado; isto é só para o tipo.
  if (!usuario) return null;
  const nomeExibido = usuario.nome ?? usuario.email;

  const aoSair = () =>
    sair.mutate(undefined, {
      // useSair já limpou o cache (nada do usuário fica em memória); agora vai para Entrar.
      onSuccess: () => navegar(ROTAS.entrar, { replace: true }),
      onError: (erro) => {
        const m = mensagemDoErro(erro);
        toast.error(`Não foi possível sair: ${m.titulo}`, { description: m.texto });
      },
    });

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2 px-2" aria-label={`Conta de ${nomeExibido}`}>
          <UserRound aria-hidden />
          <span className="hidden max-w-40 truncate lg:inline">{nomeExibido}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="truncate text-sm font-medium text-foreground">{nomeExibido}</span>
          {usuario.nome && <span className="truncate text-xs font-normal text-muted-foreground">{usuario.email}</span>}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          {usuario.google_conectado ? (
            // Informação, não ação: um div fora do roving focus do menu.
            <div className="flex items-start gap-2 px-1.5 py-1 text-sm">
              <CircleCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
              <span className="flex flex-col">
                <span>Google Ads conectado</span>
                {usuario.conta_google_ads && (
                  <span className="text-xs text-muted-foreground">
                    Conta {formatarIdConta(usuario.conta_google_ads.customer_id)}
                  </span>
                )}
              </span>
            </div>
          ) : (
            <DropdownMenuItem asChild>
              <a href={URL_LOGIN_GOOGLE}>
                <RefreshCw aria-hidden />
                Reconectar Google
              </a>
            </DropdownMenuItem>
          )}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" disabled={sair.isPending} onSelect={aoSair}>
          <LogOut aria-hidden />
          {sair.isPending ? "Saindo…" : "Sair"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
