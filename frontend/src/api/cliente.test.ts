import { describe, expect, it } from "vitest";
import { exigir } from "./cliente";
import { ErroApi } from "./erros";

// `exigir` recebe o que o openapi-fetch devolve. Aqui as respostas são montadas à mão
// (Response do próprio Node): sem rede e sem backend.

const json = (status: number, corpo: unknown, cabecalhos: Record<string, string> = {}) =>
  new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json", ...cabecalhos } });

describe("exigir", () => {
  it("resposta ok devolve os dados", async () => {
    const dados = { id: 1, email: "x@y" };
    await expect(exigir(Promise.resolve({ data: dados, response: json(200, dados) }))).resolves.toBe(dados);
  });

  it("204 devolve undefined", async () => {
    await expect(exigir(Promise.resolve({ response: new Response(null, { status: 204 }) }))).resolves.toBeUndefined();
  });

  it("erro do backend vira ErroApi com o tipo e o Retry-After", async () => {
    const corpo = { detail: "Cota excedida; tente novamente em 1 hora.", tipo: "cota_excedida" };
    const chamada = exigir(Promise.resolve({ error: corpo, response: json(503, corpo, { "Retry-After": "3600" }) }));
    await expect(chamada).rejects.toBeInstanceOf(ErroApi);
    await expect(chamada).rejects.toMatchObject({ status: 503, tipo: "cota_excedida", retryAfter: 3600 });
  });

  it("401 vira nao_autenticado", async () => {
    const corpo = { detail: "Faça login para continuar", tipo: "nao_autenticado" };
    await expect(exigir(Promise.resolve({ error: corpo, response: json(401, corpo) }))).rejects.toMatchObject({
      status: 401,
      tipo: "nao_autenticado",
    });
  });

  it("fetch que lança vira sem_conexao", async () => {
    await expect(exigir(Promise.reject(new TypeError("Failed to fetch")))).rejects.toMatchObject({
      status: null,
      tipo: "sem_conexao",
    });
  });

  it("cancelamento sai como veio (o TanStack Query reconhece o AbortError)", async () => {
    const cancelamento = new DOMException("cancelado", "AbortError");
    await expect(exigir(Promise.reject(cancelamento))).rejects.toBe(cancelamento);
  });
});
