import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// Oráculo da regra global de menos movimento em src/index.css (WCAG 2.3.3): com
// prefers-reduced-motion, animações e transições de CSS (ex.: o Sheet do menu do
// celular) ficam praticamente instantâneas. Lê o próprio CSS, como contraste.test.ts.

// Sem comentários: o comentário que explica a regra cita a consulta, e o teste não
// pode passar só por causa dele.
const css = readFileSync(new URL("../index.css", import.meta.url), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
const CONSULTA = "@media (prefers-reduced-motion: reduce)";
const DURACAO_MAXIMA_MS = 0.01;

/** Corpo do bloco que começa em `inicio`, seguindo as chaves aninhadas. */
function corpoDoBloco(texto: string, inicio: number): string {
  const abre = texto.indexOf("{", inicio);
  let profundidade = 0;
  for (let i = abre; i < texto.length; i++) {
    if (texto[i] === "{") profundidade++;
    else if (texto[i] === "}" && --profundidade === 0) return texto.slice(abre + 1, i);
  }
  throw new Error("bloco sem fechamento");
}

function regraDeMenosMovimento(): { seletores: string[]; declaracoes: Map<string, string> } | null {
  const inicio = css.indexOf(CONSULTA);
  if (inicio < 0) return null;
  const corpo = corpoDoBloco(css, inicio);
  const regra = /([^{}]+)\{([^{}]*)\}/.exec(corpo);
  if (!regra) return null;
  const seletores = regra[1]!.split(",").map((s) => s.trim());
  const declaracoes = new Map<string, string>();
  for (const m of regra[2]!.matchAll(/([\w-]+)\s*:\s*([^;]+);/g)) declaracoes.set(m[1]!, m[2]!.trim());
  return { seletores, declaracoes };
}

/** "0.01ms !important" → 0.01; "0s" → 0. Outro formato → NaN (o teste reprova). */
function emMs(valor: string): number {
  const m = /^([\d.]+)(ms|s)\s*!important$/.exec(valor);
  if (!m) return Number.NaN;
  return Number(m[1]) * (m[2] === "s" ? 1000 : 1);
}

describe("regra global de menos movimento (index.css)", () => {
  const regra = regraDeMenosMovimento();

  it(`existe um bloco ${CONSULTA} com uma regra dentro`, () => {
    expect(regra).not.toBeNull();
  });

  it("vale para todos os elementos e pseudo-elementos", () => {
    expect(regra?.seletores).toEqual(expect.arrayContaining(["*", "*::before", "*::after"]));
  });

  it.each(["animation-duration", "transition-duration"])(`%s ≤ ${DURACAO_MAXIMA_MS} ms, com !important`, (propriedade) => {
    const valor = regra?.declaracoes.get(propriedade) ?? "";
    expect(valor, propriedade).toMatch(/!important$/);
    expect(emMs(valor), `${propriedade}: ${valor}`).toBeLessThanOrEqual(DURACAO_MAXIMA_MS);
  });

  it("animation-iteration-count: 1, com !important (animação em laço não se repete)", () => {
    expect(regra?.declaracoes.get("animation-iteration-count")).toBe("1 !important");
  });
});
