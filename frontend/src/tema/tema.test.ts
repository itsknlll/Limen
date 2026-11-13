import { describe, expect, it } from "vitest";
import { aplicarTema, lerPreferencia, resolverTema, type TemaResolvido } from "./tema";

describe("lerPreferencia", () => {
  it.each(["claro", "escuro", "sistema"] as const)("aceita %s", (valor) => {
    expect(lerPreferencia(valor)).toBe(valor);
  });

  it.each([null, undefined, "", "dark", "light", "ESCURO", " escuro", "escuro "])(
    "valor inválido %j vira sistema",
    (valor) => {
      expect(lerPreferencia(valor)).toBe("sistema");
    },
  );
});

describe("resolverTema", () => {
  it.each([
    ["claro", false, "claro"],
    ["claro", true, "claro"],
    ["escuro", false, "escuro"],
    ["escuro", true, "escuro"],
    ["sistema", false, "claro"],
    ["sistema", true, "escuro"],
  ] as const)("preferência %s com sistema escuro=%s → %s", (pref, sistemaEscuro, esperado) => {
    expect(resolverTema(pref, sistemaEscuro)).toBe(esperado);
  });
});

describe("aplicarTema", () => {
  function raizFalsa(comDark: boolean) {
    const classes = new Set(comDark ? ["dark"] : []);
    return {
      classes,
      classList: { toggle: (c: string, f: boolean) => (f ? classes.add(c) : classes.delete(c)) },
      style: { colorScheme: "" },
    };
  }

  it.each([
    ["escuro", false, true, "dark"],
    ["escuro", true, true, "dark"],
    ["claro", false, false, "light"],
    ["claro", true, false, "light"],
  ] as const)(
    "tema %s (classe dark antes=%s) → dark=%s, color-scheme %s",
    (tema: TemaResolvido, antes, depois, esquema) => {
      const raiz = raizFalsa(antes);
      aplicarTema(raiz, tema);
      expect(raiz.classes.has("dark")).toBe(depois);
      expect(raiz.style.colorScheme).toBe(esquema);
    },
  );
});
