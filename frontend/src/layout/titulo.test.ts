import { describe, expect, it } from "vitest";
import { tituloDoDocumento } from "./titulo";

describe("tituloDoDocumento", () => {
  it.each([
    ["Visão geral", "Visão geral · Limen"],
    ["Entrar", "Entrar · Limen"],
    ["  Regras  ", "Regras · Limen"],
    ["", "Limen"],
    ["   ", "Limen"],
  ])("%j → %j", (pagina, esperado) => {
    expect(tituloDoDocumento(pagina)).toBe(esperado);
  });
});
