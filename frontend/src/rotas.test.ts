import { describe, expect, it } from "vitest";
import { matchPath } from "react-router";
import { lerIdCampanha } from "./campanhas/dados";
import { ITENS_NAVEGACAO, relativo, ROTAS } from "./rotas";

// string[] (e não os tipos literais): o TypeScript já sabe que nenhum é "/api" e
// recusaria a comparação; o teste existe para pegar quem mudar ROTAS sem perceber.
const caminhos: string[] = Object.values(ROTAS);

describe("ROTAS", () => {
  it.each(caminhos)("%s não colide com o proxy /api do Vite", (caminho) => {
    expect(caminho === "/api" || caminho.startsWith("/api/")).toBe(false);
  });

  it.each(caminhos)("%s é absoluto", (caminho) => {
    expect(caminho.startsWith("/")).toBe(true);
  });

  it("não há caminho repetido", () => {
    expect(new Set(caminhos).size).toBe(caminhos.length);
  });
});

describe("ITENS_NAVEGACAO", () => {
  it("os cinco itens do plano, na ordem", () => {
    expect(ITENS_NAVEGACAO.map((i) => i.rotulo)).toEqual(["Visão geral", "Campanhas", "Regras", "Avaliações", "Alertas"]);
  });

  it("nenhum item leva a uma rota com parâmetro ou à tela pública de entrar", () => {
    for (const { rota } of ITENS_NAVEGACAO) {
      expect(rota).not.toContain(":");
      expect(rota).not.toBe(ROTAS.entrar);
    }
  });
});

describe("relativo", () => {
  it.each([
    ["/campanhas", "campanhas"],
    ["/campanhas/:id", "campanhas/:id"],
    ["/regras/nova", "regras/nova"],
    ["/regras/:id/editar", "regras/:id/editar"],
    ["/", ""],
  ] as const)("%s → %j", (rota, esperado) => {
    expect(relativo(rota)).toBe(esperado);
  });
});

describe("rotas das regras", () => {
  it("/regras/nova não casa com a rota de edição", () => {
    expect(matchPath(ROTAS.regraEditar, ROTAS.regraNova)).toBeNull();
  });

  it("/regras/7/editar casa, e o id sai como texto", () => {
    expect(matchPath(ROTAS.regraEditar, "/regras/7/editar")?.params.id).toBe("7");
  });

  it('"nova" não é id: lerIdCampanha (reaproveitado da Fase 2) recusa', () => {
    expect(lerIdCampanha("nova")).toBeNull();
  });
});
