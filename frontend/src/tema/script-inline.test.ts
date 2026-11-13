import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { describe, expect, it } from "vitest";
import { aplicarTema, CHAVE_TEMA, CONSULTA_ESCURO, lerPreferencia, resolverTema } from "./tema";

// O script anti-flash do index.html repete a lógica de tema.ts. Este teste executa
// o script de verdade num ambiente falso e exige o mesmo resultado das funções TS.

const html = readFileSync(new URL("../../index.html", import.meta.url), "utf8");
const script = /<script id="tema-inicial">([\s\S]*?)<\/script>/.exec(html)?.[1];

type Guardado = string | null | "lanca";

function ambiente(guardado: Guardado, sistemaEscuro: boolean) {
  const classes = new Set<string>();
  const raiz = {
    classList: { toggle: (c: string, f: boolean) => (f ? classes.add(c) : classes.delete(c)) },
    style: { colorScheme: "" },
  };
  const localStorage = {
    // Só responde à chave certa: se o script usar outra chave, os casos "escuro" falham.
    getItem(chave: string) {
      if (guardado === "lanca") throw new Error("SecurityError: armazenamento bloqueado");
      return chave === CHAVE_TEMA ? guardado : null;
    },
  };
  // Idem para a consulta de mídia.
  const matchMedia = (consulta: string) => ({ matches: consulta === CONSULTA_ESCURO && sistemaEscuro });
  return { classes, raiz, contexto: { window: { localStorage, matchMedia }, document: { documentElement: raiz } } };
}

function esperado(guardado: Guardado, sistemaEscuro: boolean) {
  const pref = guardado === "lanca" ? "sistema" : lerPreferencia(guardado);
  const classes = new Set<string>();
  const raiz = {
    classList: { toggle: (c: string, f: boolean) => (f ? classes.add(c) : classes.delete(c)) },
    style: { colorScheme: "" },
  };
  aplicarTema(raiz, resolverTema(pref, sistemaEscuro));
  return { dark: classes.has("dark"), colorScheme: raiz.style.colorScheme };
}

describe("script anti-flash do index.html", () => {
  it("existe e fica no <head>, antes do bundle", () => {
    expect(script).toBeDefined();
    expect(html.indexOf('id="tema-inicial"')).toBeLessThan(html.indexOf("</head>"));
    expect(html.indexOf('id="tema-inicial"')).toBeLessThan(html.indexOf("/src/main.tsx"));
  });

  const guardados: Guardado[] = ["claro", "escuro", "sistema", null, "dark", "lanca"];
  const casos = guardados.flatMap((g) => [false, true].map((s) => [g, s] as const));

  it.each(casos)("guardado %j, sistema escuro=%s: igual a tema.ts", (guardado, sistemaEscuro) => {
    const { classes, raiz, contexto } = ambiente(guardado, sistemaEscuro);
    runInNewContext(script!, contexto);
    expect({ dark: classes.has("dark"), colorScheme: raiz.style.colorScheme }).toEqual(
      esperado(guardado, sistemaEscuro),
    );
  });
});
