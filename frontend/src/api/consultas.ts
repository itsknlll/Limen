import {
  MutationCache,
  type MutationObserverOptions,
  QueryCache,
  QueryClient,
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api, type Esquemas, exigir } from "./cliente";
import { deveRepetir, ErroApi } from "./erros";

// Chaves num lugar só: invalidar ou limpar uma consulta não depende de lembrar o texto.
export const chaves = {
  eu: ["eu"] as const,
  resumo: ["resumo"] as const,
  avaliacoes: (limite: number) => ["avaliacoes", limite] as const,
  campanhas: ["campanhas"] as const,
  metricas: (campanhaId: number | null) => ["metricas", campanhaId] as const,
  /** Prefixo de todas as métricas: invalidar com ele atinge as de qualquer campanha. */
  todasAsMetricas: ["metricas"] as const,
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

export function useCampanhas() {
  return useQuery({
    queryKey: chaves.campanhas,
    queryFn: ({ signal }) => exigir(api.GET("/campanhas", { signal })),
  });
}

type BuscarMetricas = (campanhaId: number, signal: AbortSignal) => Promise<Esquemas["MetricaSaida"][]>;

const buscarMetricas: BuscarMetricas = (campanhaId, signal) =>
  exigir(api.GET("/campanhas/{campanha_id}/metricas", { params: { path: { campanha_id: campanhaId } }, signal }));

/**
 * Métricas diárias de uma campanha. Com id inválido (null, de lerIdCampanha), a consulta
 * fica desligada (enabled: false): /campanhas/abc não faz pedido nenhum.
 * `buscar` é trocável só para o teste (sem rede).
 */
export function opcoesMetricas(campanhaId: number | null, buscar: BuscarMetricas = buscarMetricas) {
  return queryOptions({
    queryKey: chaves.metricas(campanhaId),
    queryFn: ({ signal }) => {
      // Não deveria rodar com null (enabled: false); se rodar, falha em vez de pedir /campanhas/null.
      if (campanhaId === null) throw new Error("consulta de métricas sem id de campanha");
      return buscar(campanhaId, signal);
    },
    enabled: campanhaId !== null,
  });
}

export function useMetricas(campanhaId: number | null) {
  return useQuery(opcoesMetricas(campanhaId));
}

/** O que a sincronização pode ter mudado: lista, métricas (campanha removida) e números da visão geral. */
export const CHAVES_APOS_SINCRONIZAR = [chaves.campanhas, chaves.todasAsMetricas, chaves.resumo] as const;

/** Erros em que o backend mudou (ou constatou) a conexão com o Google: /eu.google_conectado muda. */
const TIPOS_DA_CONEXAO_GOOGLE = new Set(["token_google_ausente", "token_google_revogado"]);

type Sincronizar = () => Promise<Esquemas["SincronizacaoSaida"]>;

/**
 * POST /campanhas/sincronizar.
 * - retry: false explícito (não depende do padrão do cliente): o backend já repete o que é
 *   transitório (IN-05) e não repete a cota (IN-06); repetir aqui multiplicaria as chamadas.
 * - Sucesso: invalida campanhas, métricas e resumo. O onSuccess devolve a promessa, então o
 *   botão continua em "Sincronizando…" até as consultas ativas voltarem com os dados novos.
 * - Token ausente ou revogado: invalida /eu (o backend apaga o token no revogado, IN-04),
 *   e a tela troca "Sincronizar" por "Conectar Google".
 * `sincronizar` é trocável só para o teste (sem rede).
 */
export function opcoesSincronizar(
  cliente: QueryClient,
  sincronizar: Sincronizar = () => exigir(api.POST("/campanhas/sincronizar")),
): MutationObserverOptions<Esquemas["SincronizacaoSaida"], unknown, void> {
  return {
    mutationFn: sincronizar,
    retry: false,
    onSuccess: () => Promise.all(CHAVES_APOS_SINCRONIZAR.map((queryKey) => cliente.invalidateQueries({ queryKey }))),
    onError: (erro) => {
      if (erro instanceof ErroApi && TIPOS_DA_CONEXAO_GOOGLE.has(erro.tipo)) {
        void cliente.invalidateQueries({ queryKey: chaves.eu });
      }
    },
  };
}

export function useSincronizar() {
  const cliente = useQueryClient();
  return useMutation(opcoesSincronizar(cliente));
}

/** POST /sessao/sair; ao concluir, apaga tudo da memória (nada do usuário anterior fica). */
export function useSair() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: () => exigir(api.POST("/sessao/sair")),
    onSuccess: () => cliente.clear(),
  });
}
