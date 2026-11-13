import { Bell, Coins, MousePointerClick, Target } from "lucide-react";
import { describe, expect, it } from "vitest";
import { aparenciaDaRegra } from "./aparencia";

describe("aparenciaDaRegra", () => {
  it.each([
    ["R1", "r1", "CTR baixo", MousePointerClick],
    ["R2", "r2", "CPC alto", Coins],
    ["R3", "r3", "Custo sem conversão", Target],
  ] as const)("%s → tom %s, nome '%s' e ícone próprio", (codigo, tom, nome, Icone) => {
    const a = aparenciaDaRegra(codigo);
    expect(a.codigo).toBe(codigo);
    expect(a.tom).toBe(tom);
    expect(a.nomePadrao).toBe(nome);
    expect(a.Icone).toBe(Icone);
    expect(a.classes).toEqual({ texto: `text-regra-${tom}`, fundo: `bg-regra-${tom}-suave` });
    expect(a.corCss).toBe(`var(--regra-${tom})`);
  });

  it("as três regras padrão têm ícones e cores diferentes entre si", () => {
    const tres = ["R1", "R2", "R3"].map(aparenciaDaRegra);
    expect(new Set(tres.map((a) => a.Icone)).size).toBe(3);
    expect(new Set(tres.map((a) => a.corCss)).size).toBe(3);
  });

  it.each(["R4", "r1", "", " R1", "R1 ", "toString", "__proto__", "constructor"])(
    "código desconhecido %j → neutro com sino, sem nome padrão, código preservado",
    (codigo) => {
      const a = aparenciaDaRegra(codigo);
      expect(a.tom).toBe("outra");
      expect(a.Icone).toBe(Bell);
      expect(a.nomePadrao).toBeNull();
      expect(a.codigo).toBe(codigo);
      expect(a.classes).toEqual({ texto: "text-regra-outra", fundo: "bg-regra-outra-suave" });
    },
  );
});
