import { MutationObserver, QueryClient, QueryObserver, type QueryKey } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { Esquemas } from "./cliente";
import { chaves, CHAVES_APOS_SINCRONIZAR, criarClienteQuery, opcoesMetricas, opcoesSincronizar } from "./consultas";
import { ErroApi } from "./erros";

// QueryClient de verdade, sem React e sem rede: a chamada à API é trocada por uma função
// falsa (o parâmetro `sincronizar`/`buscar` das opções).

type Saida = Esquemas["SincronizacaoSaida"];

/** Cliente que repetiria tudo, sem espera: prova que o retry: false vem da mutação, não do padrão. */
function clienteQueRepete(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: 3, retryDelay: 0 }, mutations: { retry: 3, retryDelay: 0 } },
  });
}

/** Consultas já em cache (inativas), para ver quais a sincronização invalida. */
const EM_CACHE: QueryKey[] = [
  chaves.eu,
  chaves.resumo,
  chaves.avaliacoes(5),
  chaves.campanhas,
  chaves.metricas(1),
  chaves.metricas(2),
  [...chaves.alertas, { limite: 500 }],
];

function comCache(cliente: QueryClient): QueryClient {
  for (const chave of EM_CACHE) cliente.setQueryData(chave, {});
  return cliente;
}

function invalidadas(cliente: QueryClient): string[] {
  return EM_CACHE.filter((chave) => cliente.getQueryState(chave)?.isInvalidated).map((chave) => JSON.stringify(chave));
}

async function sincronizarCom(cliente: QueryClient, sincronizar: () => Promise<Saida>) {
  const observador = new MutationObserver(cliente, opcoesSincronizar(cliente, sincronizar));
  await observador.mutate().catch(() => undefined);
  return observador.getCurrentResult();
}

const falhaCom = (tipo: string, status: number | null) =>
  vi.fn<() => Promise<Saida>>().mockRejectedValue(new ErroApi({ status, tipo }));

describe("useSincronizar (opcoesSincronizar)", () => {
  it("as chaves invalidadas no sucesso são exatamente campanhas, métricas, resumo e alertas", () => {
    expect(CHAVES_APOS_SINCRONIZAR).toEqual([["campanhas"], ["metricas"], ["resumo"], ["alertas"]]);
  });

  it("sucesso invalida campanhas, as métricas de todas as campanhas, o resumo e os alertas; não toca em /eu nem avaliações", async () => {
    const cliente = comCache(clienteQueRepete());
    const resultado = await sincronizarCom(cliente, () => Promise.resolve({ campanhas_sincronizadas: 3 }));
    expect(resultado.status).toBe("success");
    expect(resultado.data).toEqual({ campanhas_sincronizadas: 3 });
    expect(invalidadas(cliente)).toEqual(['["resumo"]', '["campanhas"]', '["metricas",1]', '["metricas",2]', '["alertas",{"limite":500}]']);
  });

  it.each([
    ["token_google_ausente", 409],
    ["token_google_revogado", 409],
  ])("%s invalida só /eu (google_conectado muda)", async (tipo, status) => {
    const cliente = comCache(clienteQueRepete());
    const resultado = await sincronizarCom(cliente, falhaCom(tipo, status));
    expect(resultado.status).toBe("error");
    expect(invalidadas(cliente)).toEqual(['["eu"]']);
  });

  it.each([
    ["cota_excedida", 503],
    ["google_ads_indisponivel", 503],
    ["google_autenticacao_temporaria", 503],
    ["erro_google_ads", 502],
    ["conflito", 409],
    ["sem_conexao", null],
  ])("%s não invalida nada", async (tipo, status) => {
    const cliente = comCache(clienteQueRepete());
    await sincronizarCom(cliente, falhaCom(tipo, status));
    expect(invalidadas(cliente)).toEqual([]);
  });

  it.each(["google_ads_indisponivel", "google_autenticacao_temporaria", "sem_conexao"])(
    "sem repetição automática: %s (transitório) chama o backend uma vez só, mesmo num cliente que repete",
    async (tipo) => {
      const sincronizar = falhaCom(tipo, tipo === "sem_conexao" ? null : 503);
      await sincronizarCom(clienteQueRepete(), sincronizar);
      expect(sincronizar).toHaveBeenCalledTimes(1);
    },
  );

  it("com o cliente da aplicação, o 401 continua invalidando /eu (MutationCache global)", async () => {
    const cliente = comCache(criarClienteQuery());
    await sincronizarCom(cliente, falhaCom("nao_autenticado", 401));
    expect(invalidadas(cliente)).toEqual(['["eu"]']);
  });
});

describe("useMetricas (opcoesMetricas)", () => {
  type Buscar = (campanhaId: number, signal: AbortSignal) => Promise<Esquemas["MetricaSaida"][]>;

  it("uma chave por campanha", () => {
    expect(opcoesMetricas(1).queryKey).toEqual(["metricas", 1]);
    expect(opcoesMetricas(null).queryKey).toEqual(["metricas", null]);
  });

  it("id inválido (null): consulta desligada e nenhum pedido", async () => {
    const buscar = vi.fn<Buscar>().mockResolvedValue([]);
    const observador = new QueryObserver(clienteQueRepete(), opcoesMetricas(null, buscar));
    const parar = observador.subscribe(() => {});
    await new Promise((resolver) => setTimeout(resolver, 0));
    expect(buscar).not.toHaveBeenCalled();
    const resultado = observador.getCurrentResult();
    expect(resultado.fetchStatus).toBe("idle");
    // A consulta nunca rodou: nem sucesso nem erro, e nenhuma falha contada. Não depende
    // do tempo: com a consulta ligada, a queryFn lança na 1ª tentativa e failureCount ≥ 1.
    expect(resultado.status).toBe("pending");
    expect(resultado.failureCount).toBe(0);
    parar();
  });

  it("id válido: busca uma vez, com o id e o sinal de cancelamento", async () => {
    const buscar = vi.fn<Buscar>().mockResolvedValue([]);
    const observador = new QueryObserver(clienteQueRepete(), opcoesMetricas(7, buscar));
    const parar = observador.subscribe(() => {});
    await vi.waitFor(() => expect(buscar).toHaveBeenCalledTimes(1));
    expect(buscar.mock.calls[0]![0]).toBe(7);
    expect(buscar.mock.calls[0]![1]).toBeInstanceOf(AbortSignal);
    parar();
  });
});
