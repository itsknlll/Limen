import { describe, expect, it } from "vitest";
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
    ["/", ""],
  ] as const)("%s → %j", (rota, esperado) => {
    expect(relativo(rota)).toBe(esperado);
  });
});
