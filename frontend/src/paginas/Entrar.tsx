import { Info, LogIn } from "lucide-react";
import { Navigate, useLocation } from "react-router";
import { URL_LOGIN_GOOGLE } from "@/api/cliente";
import { ehNaoAutenticado, useEu } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Marca } from "@/layout/Marca";
import { SeloOrigemDados } from "@/layout/SeloOrigemDados";
import { TituloPagina } from "@/layout/TituloPagina";
import { ROTAS } from "@/rotas";
import type { EstadoEntrar } from "@/sessao/RotaProtegida";
import { SeletorTema } from "@/tema/SeletorTema";

/**
 * Login com Google (OAuth real, CSRF + PKCE no backend). O botão é um link de página
 * inteira para GET /api/oauth/google/login; o Google volta no callback do 8080, que
 * redireciona para "/". Limitação: volta sempre para "/", não para a tela em que a
 * pessoa estava (o destino vem só da configuração, para evitar redirecionamento aberto).
 */
export function Entrar() {
  const eu = useEu();
  const { state } = useLocation();

  // Já tem sessão: não há o que fazer aqui.
  if (eu.isSuccess) return <Navigate to={ROTAS.visaoGeral} replace />;

  const sessaoEncerrada = (state as EstadoEntrar | null)?.sessaoEncerrada === true;
  // 401 é o esperado nesta tela; qualquer outro erro (ex.: backend parado) é mostrado,
  // porque o login também falharia.
  const erroDoServidor = eu.isError && !ehNaoAutenticado(eu.error) ? eu.error : null;

  return (
    <div className="relative grid min-h-svh place-items-center bg-background px-4 py-10 text-foreground">
      <div className="absolute top-3 right-3">
        <SeletorTema />
      </div>
      <main id="conteudo" className="flex w-full max-w-sm flex-col gap-4">
        <Card>
          <CardHeader className="gap-4">
            <Marca />
            <div className="flex flex-col gap-1.5">
              <TituloPagina documento="Entrar">Entrar no Limen</TituloPagina>
              <CardDescription>
                Alertas sobre as métricas das suas campanhas do Google Ads, gerados por um motor de regras.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {sessaoEncerrada && (
              <p role="status" className="flex items-start gap-2 rounded-lg bg-muted p-3 text-sm">
                <Info aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
                Sua sessão terminou. Entre novamente para continuar.
              </p>
            )}
            {erroDoServidor && (
              <EstadoErro erro={erroDoServidor} aoTentarNovamente={() => void eu.refetch()} tentando={eu.isFetching} />
            )}
            <Button asChild size="lg" className="w-full">
              <a href={URL_LOGIN_GOOGLE}>
                <LogIn aria-hidden />
                Entrar com Google
              </a>
            </Button>
            <p className="text-xs text-muted-foreground">
              Você vai para o Google autorizar o acesso às suas campanhas (Google Ads) e depois volta para a visão
              geral.
            </p>
          </CardContent>
        </Card>
        <SeloOrigemDados className="self-center" />
      </main>
    </div>
  );
}
