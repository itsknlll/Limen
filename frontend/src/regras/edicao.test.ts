import { describe, expect, it } from "vitest";
import { ErroApi } from "@/api/erros";
import { lerIdCampanha } from "@/campanhas/dados";
import { focoDaNovaCondicao, regraNaoEncontrada } from "./edicao";

const erro = (status: number | null, tipo: string) => new ErroApi({ status, tipo });

describe("regraNaoEncontrada", () => {
  it.each(["abc", "nova", "0", "007", undefined])("id da URL %j inválido → não encontrada, sem erro da API", (param) => {
    expect(regraNaoEncontrada(lerIdCampanha(param), null)).toBe(true);
  });

  it("404 da API (tipo nao_encontrado) → não encontrada", () => {
    expect(regraNaoEncontrada(7, erro(404, "nao_encontrado"))).toBe(true);
  });

  it.each([
    ["carregando ou carregada", null],
    ["servidor (500)", erro(500, "erro_http")],
    ["sem conexão", erro(null, "sem_conexao")],
    ["sessão (401)", erro(401, "nao_autenticado")],
    ["erro que não é da API", new Error("falha")],
  ])("id válido e %s → não é 'não encontrada'", (_, e) => {
    expect(regraNaoEncontrada(7, e)).toBe(false);
  });
});

describe("focoDaNovaCondicao", () => {
  it.each([
    [1, "condicoes.1.metrica"],
    [9, "condicoes.9.metrica"],
  ])("com %i condições, foca a Métrica da nova: %s", (n, esperado) => {
    expect(focoDaNovaCondicao(n)).toBe(esperado);
  });

  it("o prefixo não casa com a condição 10 (o react-hook-form compara com startsWith)", () => {
    expect("condicoes.10.metrica".startsWith(focoDaNovaCondicao(1))).toBe(false);
  });
});
