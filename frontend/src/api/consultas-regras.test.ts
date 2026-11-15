// Consultas e mutações de regras e avaliações (Fase 3, etapa 3). QueryClient de verdade e
// cliente openapi-fetch de verdade, com um fetch falso que grava cada pedido (método,
// caminho, corpo) e responde sem rede. Assim o teste vê o pedido que sairia de fato.
import { MutationObserver, type MutationObserverOptions, QueryClient, QueryObserver, type QueryKey } from "@tanstack/react-query";
import createClient from "openapi-fetch";
import { describe, expect, it, vi } from "vitest";
import type { CorpoRegra } from "@/regras/validacao";
import type { Esquemas } from "./cliente";
import {
  CHAVES_APOS_AVALIAR,
  CHAVES_APOS_REGRA,
  chaves,
  criarClienteQuery,
  opcoesAtivarRegra,
  opcoesDesativarRegra,
  opcoesExecutarAvaliacao,
  opcoesRegra,
  opcoesSalvarRegra,
} from "./consultas";
import type { paths } from "./esquema";

interface Pedido {
  metodo: string;
  caminho: string;
  corpo: unknown;
}

function apiFalsa(responder: (pedido: Pedido) => Response) {
  const pedidos: Pedido[] = [];
  const cliente = createClient<paths>({
    baseUrl: "http://limen.teste",
    fetch: async (requisicao) => {
      const texto = await requisicao.text();
      const pedido = { metodo: requisicao.method, caminho: new URL(requisicao.url).pathname, corpo: texto === "" ? null : JSON.parse(texto) };
      pedidos.push(pedido);
      return responder(pedido);
    },
  });
  return { cliente, pedidos };
}

const json = (status: number, corpo: unknown) =>
  new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } });
const erro = (status: number, tipo: string) => json(status, { detail: "frase do backend", tipo });
const semResposta = (): Response => {
  throw new TypeError("Failed to fetch");
};

/** Cliente que repetiria tudo, sem espera: prova que o retry: false vem das opções, não do padrão. */
function clienteQueRepete(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: 3, retryDelay: 0 }, mutations: { retry: 3, retryDelay: 0 } },
  });
}

const EM_CACHE: QueryKey[] = [
  chaves.eu,
  chaves.resumo,
  chaves.campanhas,
  chaves.metricas(1),
  chaves.regras,
  chaves.regra(7),
  chaves.avaliacoes(5),
  chaves.avaliacoes(50),
  [...chaves.alertas, { limite: 500 }],
];

function comCache(cliente: QueryClient): QueryClient {
  for (const chave of EM_CACHE) cliente.setQueryData(chave, {});
  return cliente;
}

function invalidadas(cliente: QueryClient): string[] {
  return EM_CACHE.filter((chave) => cliente.getQueryState(chave)?.isInvalidated).map((chave) => JSON.stringify(chave));
}

async function rodar<TData, TVariaveis>(
  cliente: QueryClient,
  opcoes: MutationObserverOptions<TData, unknown, TVariaveis>,
  variaveis: TVariaveis,
) {
  const observador = new MutationObserver(cliente, opcoes);
  await observador.mutate(variaveis).catch(() => undefined);
  return observador.getCurrentResult();
}

const REGRA_API: Esquemas["RegraSaida"] = {
  id: 7,
  codigo: "R4",
  nome: "CPC muito alto",
  ativa: false,
  referencia: false,
  condicoes: [{ ordem: 1, metrica: "cpc", operador: ">", limiar: "7.500000" }],
};
const CORPO: CorpoRegra = {
  codigo: "R4",
  nome: "CPC muito alto",
  ativa: true,
  condicoes: [{ metrica: "cpc", operador: ">", limiar: "7.5" }],
};
const AVALIACAO: Esquemas["AvaliacaoSaida"] = {
  id: 3,
  iniciada_em: "2026-11-15T12:00:00Z",
  concluida_em: "2026-11-15T12:00:01Z",
  registros_avaliados: 60,
  registros_rejeitados: 0,
  alertas_gerados: 0,
  alertas_ja_existentes: 18,
  duracao_motor_ms: "0.504",
  incluir_pausadas: false,
  campanha_id: null,
  inicio: null,
  fim: null,
};

describe("chaves", () => {
  it("a regra fica sob o prefixo da lista", () => {
    expect(chaves.regra(7)).toEqual(["regras", 7]);
  });
  it("o que cada mutação invalida", () => {
    expect(CHAVES_APOS_REGRA).toEqual([["regras"], ["resumo"]]);
    expect(CHAVES_APOS_AVALIAR).toEqual([["avaliacoes"], ["resumo"], ["alertas"]]);
  });
});

describe("salvar regra (opcoesSalvarRegra)", () => {
  it("sem id: POST /regras com o corpo", async () => {
    const { cliente, pedidos } = apiFalsa(() => json(201, REGRA_API));
    await rodar(clienteQueRepete(), opcoesSalvarRegra(clienteQueRepete(), cliente), { id: null, corpo: CORPO });
    expect(pedidos).toEqual([{ metodo: "POST", caminho: "/regras", corpo: CORPO }]);
  });

  it("com id: PUT /regras/7 com o corpo", async () => {
    const { cliente, pedidos } = apiFalsa(() => json(200, REGRA_API));
    await rodar(clienteQueRepete(), opcoesSalvarRegra(clienteQueRepete(), cliente), { id: 7, corpo: CORPO });
    expect(pedidos).toEqual([{ metodo: "PUT", caminho: "/regras/7", corpo: CORPO }]);
  });

  it("sucesso invalida a lista, a regra e o resumo, e mais nada", async () => {
    const consultas = comCache(clienteQueRepete());
    const { cliente } = apiFalsa(() => json(200, REGRA_API));
    const resultado = await rodar(consultas, opcoesSalvarRegra(consultas, cliente), { id: 7, corpo: CORPO });
    expect(resultado.status).toBe("success");
    expect(invalidadas(consultas)).toEqual(['["resumo"]', '["regras"]', '["regras",7]']);
  });

  it.each([
    ["409 conflito", () => erro(409, "conflito")],
    ["409 regra_referencia", () => erro(409, "regra_referencia")],
    ["sem resposta (transitório)", semResposta],
  ])("%s: um pedido só, mesmo num cliente que repete, e nada invalidado", async (_, responder) => {
    const consultas = comCache(clienteQueRepete());
    const { cliente, pedidos } = apiFalsa(responder);
    const resultado = await rodar(consultas, opcoesSalvarRegra(consultas, cliente), { id: null, corpo: CORPO });
    expect(resultado.status).toBe("error");
    expect(pedidos).toHaveLength(1);
    expect(invalidadas(consultas)).toEqual([]);
  });

  it("com o cliente da aplicação, o 401 continua invalidando /eu (MutationCache global)", async () => {
    const consultas = comCache(criarClienteQuery());
    const { cliente } = apiFalsa(() => erro(401, "nao_autenticado"));
    await rodar(consultas, opcoesSalvarRegra(consultas, cliente), { id: null, corpo: CORPO });
    expect(invalidadas(consultas)).toEqual(['["eu"]']);
  });
});

describe("ativar regra (opcoesAtivarRegra)", () => {
  it("PUT /regras/7 com a regra inteira, ativa = true e o limiar normalizado", async () => {
    const { cliente, pedidos } = apiFalsa(() => json(200, { ...REGRA_API, ativa: true }));
    const consultas = comCache(clienteQueRepete());
    await rodar(consultas, opcoesAtivarRegra(consultas, cliente), REGRA_API);
    expect(pedidos).toEqual([{ metodo: "PUT", caminho: "/regras/7", corpo: CORPO }]);
    expect(invalidadas(consultas)).toEqual(['["resumo"]', '["regras"]', '["regras",7]']);
  });

  it("regra que não passa na validação (R1) não gera pedido", async () => {
    const { cliente, pedidos } = apiFalsa(() => json(200, REGRA_API));
    const resultado = await rodar(clienteQueRepete(), opcoesAtivarRegra(clienteQueRepete(), cliente), {
      ...REGRA_API,
      codigo: "R1",
      referencia: true,
    });
    expect(resultado.status).toBe("error");
    expect(pedidos).toEqual([]);
  });
});

describe("desativar regra (opcoesDesativarRegra)", () => {
  it("DELETE /regras/7 sem corpo; sucesso invalida a lista, a regra e o resumo", async () => {
    const { cliente, pedidos } = apiFalsa(() => new Response(null, { status: 204 }));
    const consultas = comCache(clienteQueRepete());
    const resultado = await rodar(consultas, opcoesDesativarRegra(consultas, cliente), 7);
    expect(resultado.status).toBe("success");
    expect(pedidos).toEqual([{ metodo: "DELETE", caminho: "/regras/7", corpo: null }]);
    expect(invalidadas(consultas)).toEqual(['["resumo"]', '["regras"]', '["regras",7]']);
  });

  it("409 regra_referencia: um pedido só e nada invalidado", async () => {
    const { cliente, pedidos } = apiFalsa(() => erro(409, "regra_referencia"));
    const consultas = comCache(clienteQueRepete());
    await rodar(consultas, opcoesDesativarRegra(consultas, cliente), 1);
    expect(pedidos).toHaveLength(1);
    expect(invalidadas(consultas)).toEqual([]);
  });
});

describe("executar avaliação (opcoesExecutarAvaliacao)", () => {
  const corpo = { campanha_id: 1, inicio: "2026-10-13", fim: "2026-11-11", incluir_pausadas: true };

  it("POST /avaliacoes com o corpo exato e devolve a avaliação", async () => {
    const { cliente, pedidos } = apiFalsa(() => json(201, AVALIACAO));
    const resultado = await rodar(clienteQueRepete(), opcoesExecutarAvaliacao(clienteQueRepete(), cliente), corpo);
    expect(pedidos).toEqual([{ metodo: "POST", caminho: "/avaliacoes", corpo }]);
    expect(resultado.data).toEqual(AVALIACAO);
  });

  it("sucesso invalida o histórico de todos os limites, o resumo e os alertas; não toca em regras, campanhas e /eu", async () => {
    const consultas = comCache(clienteQueRepete());
    const { cliente } = apiFalsa(() => json(201, AVALIACAO));
    await rodar(consultas, opcoesExecutarAvaliacao(consultas, cliente), corpo);
    expect(invalidadas(consultas)).toEqual([
      '["resumo"]',
      '["avaliacoes",5]',
      '["avaliacoes",50]',
      '["alertas",{"limite":500}]',
    ]);
  });

  it.each([
    ["sem resposta (transitório)", semResposta],
    ["400 validacao", () => erro(400, "validacao")],
  ])("%s: um pedido só, mesmo num cliente que repete, e nada invalidado", async (_, responder) => {
    const consultas = comCache(clienteQueRepete());
    const { cliente, pedidos } = apiFalsa(responder);
    const resultado = await rodar(consultas, opcoesExecutarAvaliacao(consultas, cliente), corpo);
    expect(resultado.status).toBe("error");
    expect(pedidos).toHaveLength(1);
    expect(invalidadas(consultas)).toEqual([]);
  });
});

describe("uma regra (opcoesRegra)", () => {
  it("id inválido (null): consulta desligada e nenhum pedido", async () => {
    const { cliente, pedidos } = apiFalsa(() => json(200, REGRA_API));
    const observador = new QueryObserver(clienteQueRepete(), opcoesRegra(null, cliente));
    const parar = observador.subscribe(() => {});
    await new Promise((resolver) => setTimeout(resolver, 0));
    const resultado = observador.getCurrentResult();
    expect(pedidos).toEqual([]);
    expect(resultado.fetchStatus).toBe("idle");
    expect(resultado.failureCount).toBe(0);
    parar();
  });

  it("id válido: GET /regras/7 uma vez", async () => {
    const { cliente, pedidos } = apiFalsa(() => json(200, REGRA_API));
    const observador = new QueryObserver(clienteQueRepete(), opcoesRegra(7, cliente));
    const parar = observador.subscribe(() => {});
    await vi.waitFor(() => expect(observador.getCurrentResult().status).toBe("success"));
    expect(pedidos).toEqual([{ metodo: "GET", caminho: "/regras/7", corpo: null }]);
    parar();
  });
});
