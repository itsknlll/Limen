// Consulta de alertas (Fase 4). QueryClient de verdade e cliente openapi-fetch de verdade,
// com um fetch falso que grava o caminho e a query de cada pedido e responde sem rede.
import { QueryClient, QueryObserver } from "@tanstack/react-query";
import createClient from "openapi-fetch";
import { describe, expect, it, vi } from "vitest";
import type { ConsultaAlertas } from "@/alertas/filtros";
import { chaves, opcoesAlertas } from "./consultas";
import type { paths } from "./esquema";

function apiFalsa() {
  const pedidos: string[] = [];
  const cliente = createClient<paths>({
    baseUrl: "http://limen.teste",
    fetch: async (requisicao) => {
      const url = new URL(requisicao.url);
      pedidos.push(`${requisicao.method} ${url.pathname}${url.search}`);
      return new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } });
    },
  });
  return { cliente, pedidos };
}

/** Cliente que repetiria tudo, sem espera: a consulta desligada não pode depender do padrão. */
function clienteQueRepete(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: 3, retryDelay: 0 } } });
}

async function buscar(consulta: ConsultaAlertas) {
  const { cliente, pedidos } = apiFalsa();
  const observador = new QueryObserver(clienteQueRepete(), opcoesAlertas(consulta, cliente));
  const parar = observador.subscribe(() => {});
  await vi.waitFor(() => expect(observador.getCurrentResult().status).toBe("success"));
  parar();
  return pedidos;
}

describe("alertas (opcoesAlertas)", () => {
  it("filtros viram a query de GET /alertas, um pedido só", async () => {
    const pedidos = await buscar({ campanha_id: 2, inicio: "2026-10-13", fim: "2026-11-11", limite: 500 });
    expect(pedidos).toEqual(["GET /alertas?campanha_id=2&inicio=2026-10-13&fim=2026-11-11&limite=500"]);
  });

  it("sem filtros: só o limite", async () => {
    expect(await buscar({ limite: 500 })).toEqual(["GET /alertas?limite=500"]);
  });

  it("consulta null (URL inválida): desligada e nenhum pedido, mesmo num cliente que repete", async () => {
    const { cliente, pedidos } = apiFalsa();
    const observador = new QueryObserver(clienteQueRepete(), opcoesAlertas(null, cliente));
    const parar = observador.subscribe(() => {});
    await new Promise((resolver) => setTimeout(resolver, 0));
    const resultado = observador.getCurrentResult();
    expect(pedidos).toEqual([]);
    expect(resultado.fetchStatus).toBe("idle");
    expect(resultado.status).toBe("pending");
    // A queryFn com null lança antes do fetch: só o failureCount mostra que ela rodou.
    expect(resultado.failureCount).toBe(0);
    parar();
  });

  it("a chave fica sob o prefixo alertas: invalidar o prefixo atinge todos os filtros", async () => {
    const cliente = clienteQueRepete();
    const comFiltro = chaves.alertasFiltrados({ campanha_id: 2, limite: 500 });
    const semFiltro = chaves.alertasFiltrados({ limite: 500 });
    cliente.setQueryData(comFiltro, []);
    cliente.setQueryData(semFiltro, []);
    await cliente.invalidateQueries({ queryKey: chaves.alertas });
    expect(cliente.getQueryState(comFiltro)?.isInvalidated).toBe(true);
    expect(cliente.getQueryState(semFiltro)?.isInvalidated).toBe(true);
  });
});
