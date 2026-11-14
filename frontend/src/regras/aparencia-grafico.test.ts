import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { lerBloco, resolver } from "../tema/contraste";
import { aparenciaDaRegra } from "./aparencia";

// corGrafico: a cor da barra e da amostra da legenda. Os tokens precisam ser os que
// grafico.test.ts confere (gama, contraste ≥ 3:1 e distância ≥ 15), senão a cor de
// alguma regra no gráfico escaparia do oráculo.

const css = readFileSync(new URL("../index.css", import.meta.url), "utf8");
const raiz = lerBloco(css, ":root");
const escuro = lerBloco(css, ".dark");
const SERIES_CONFERIDAS = ["chart-1", "chart-2", "chart-3", "chart-5"];
const token = (cor: string) => /^var\(--([\w-]+)\)$/.exec(cor)?.[1];

describe("aparenciaDaRegra: corGrafico", () => {
  it.each([
    ["R1", "var(--chart-1)"],
    ["R2", "var(--chart-2)"],
    ["R3", "var(--chart-3)"],
    ["R4", "var(--chart-5)"],
    ["r1", "var(--chart-5)"],
    ["toString", "var(--chart-5)"],
  ])("%s → %s", (codigo, cor) => {
    expect(aparenciaDaRegra(codigo).corGrafico).toBe(cor);
  });

  it.each(["R1", "R2", "R3", "R4"])("%s: token existe nos dois temas e está entre as séries conferidas", (codigo) => {
    const nome = token(aparenciaDaRegra(codigo).corGrafico);
    expect(nome).toBeDefined();
    expect(SERIES_CONFERIDAS).toContain(nome);
    expect(() => resolver(nome!, raiz)).not.toThrow();
    expect(() => resolver(nome!, escuro, raiz)).not.toThrow();
  });

  it("barra e texto usam tokens diferentes, e as três regras têm cores de barra distintas", () => {
    const tres = ["R1", "R2", "R3"].map(aparenciaDaRegra);
    for (const a of tres) expect(a.corGrafico).not.toBe(a.corCss);
    expect(new Set(tres.map((a) => a.corGrafico)).size).toBe(3);
  });
});
