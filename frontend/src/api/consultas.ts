import { MutationCache, QueryCache, QueryClient, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, exigir } from "./cliente";
import { deveRepetir, ErroApi } from "./erros";

// Chaves num lugar só: invalidar ou limpar uma consulta não depende de lembrar o texto.
export const chaves = {
  eu: ["eu"] as const,
  resumo: ["resumo"] as const,
  avaliacoes: (limite: number) => ["avaliacoes", limite] as const,
};

export function ehNaoAutenticado(erro: unknown): boolean {
  return erro instanceof ErroApi && erro.status === 401;
}

export function criarClienteQuery(): QueryClient {
  // Sessão que expira no meio do uso: qualquer 401 invalida a consulta de /eu; ela é
  // refeita, recebe 401 e a RotaProtegida leva para /entrar. invalidate (e não reset)
  // mantém o último usuário em `data`: é assim que a RotaProtegida sabe que havia
  // sessão e a tela Entrar diz "sua sessão terminou" em vez de tratar como primeiro acesso.
  const aoFalhar = (erro: unknown) => {
    if (ehNaoAutenticado(erro)) void cliente.invalidateQueries({ queryKey: chaves.eu });
  };
  const cliente: QueryClient = new QueryClient({
    queryCache: new QueryCache({
      onError: (erro, consulta) => {
        // A própria /eu com 401 já é tratada pela RotaProtegida (evita laço).
        if (consulta.queryKey[0] !== chaves.eu[0]) aoFalhar(erro);
      },
    }),
    mutationCache: new MutationCache({ onError: aoFalhar }),
    defaultOptions: {
      queries: {
        retry: deveRepetir,
        staleTime: 30_000,
        // Os números não mudam sozinhos durante a captura de evidências.
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
  return cliente;
}

export function useEu() {
  return useQuery({
    queryKey: chaves.eu,
    queryFn: ({ signal }) => exigir(api.GET("/eu", { signal })),
  });
}

export function useResumo() {
  return useQuery({
    queryKey: chaves.resumo,
    queryFn: ({ signal }) => exigir(api.GET("/resumo", { signal })),
  });
}

export function useAvaliacoes(limite: number) {
  return useQuery({
    queryKey: chaves.avaliacoes(limite),
    queryFn: ({ signal }) => exigir(api.GET("/avaliacoes", { params: { query: { limite } }, signal })),
  });
}

/** POST /sessao/sair; ao concluir, apaga tudo da memória (nada do usuário anterior fica). */
export function useSair() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: () => exigir(api.POST("/sessao/sair")),
    onSuccess: () => cliente.clear(),
  });
}
