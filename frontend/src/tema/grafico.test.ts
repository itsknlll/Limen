import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { deltaEOk, dentroDaGama, lerBloco, lerOklch, oklchParaRgb, razaoContraste, resolver } from "./contraste";

// Oráculo das séries do gráfico: --chart-1..3 (R1 a R3) e --chart-5 (regras criadas
// pelo usuário), lidos de src/index.css como em contraste.test.ts; nenhuma cor é
// repetida aqui. Critérios do validador de paleta da skill dataviz: marca não textual
// ≥ 3:1 (WCAG 1.4.11) e séries a ΔE OKLab ≥ 15 entre si (visão normal).

const css = readFileSync(new URL("../index.css", import.meta.url), "utf8");
const raiz = lerBloco(css, ":root");
const escuro = lerBloco(css, ".dark");

const TEMAS = {
  claro: [raiz],
  escuro: [escuro, raiz], // .dark só redefine; o resto vem do :root
} as const;

const NAO_TEXTO = 3;
const DISTANCIA_MINIMA = 15;
const SERIES = ["chart-1", "chart-2", "chart-3", "chart-5"];
const SUPERFICIES = ["card", "background"];
// Faixa de luminosidade (OKLCH L) para barras, a do validador: fora dela a série pesa
// demais ou some no fundo. Exceção explícita: --chart-5 (cinza das regras do usuário)
// no escuro fica em 0,71, porque nenhum cinza dentro da faixa se separa do R2 sob
// daltonismo (limitação registrada).
const FAIXA_L = { claro: [0.43, 0.77], escuro: [0.48, 0.67] } as const;
const FORA_DA_FAIXA: Record<keyof typeof TEMAS, string[]> = { claro: [], escuro: ["chart-5"] };

describe("deltaEOk", () => {
  it("cor igual = 0 e é simétrica", () => {
    const a = lerOklch("oklch(0.53 0.13 55)");
    const b = lerOklch("oklch(0.55 0.21 355)");
    expect(deltaEOk(a, a)).toBe(0);
    expect(deltaEOk(a, b)).toBe(deltaEOk(b, a));
  });

  it("bate com o validador da skill (R1 × R2 no claro: ΔE 18,5)", () => {
    // Referência externa: saída de validate_palette.js (#a35303 × #c61d78), não desta função.
    expect(deltaEOk(lerOklch("oklch(0.53 0.13 55)"), lerOklch("oklch(0.55 0.21 355)"))).toBeCloseTo(18.5, 0);
  });
});

describe.each(Object.entries(TEMAS))("séries do gráfico, tema %s", (tema, camadas) => {
  const oklch = (token: string) => lerOklch(resolver(token, ...camadas));
  const [minimo, maximo] = FAIXA_L[tema as keyof typeof TEMAS];
  const excecoes = FORA_DA_FAIXA[tema as keyof typeof TEMAS];

  it.each(SERIES.filter((s) => !excecoes.includes(s)))(`--%s com L na faixa ${minimo}–${maximo}`, (serie) => {
    const { l } = oklch(serie);
    expect(l, `--${serie}: L ${l}`).toBeGreaterThanOrEqual(minimo);
    expect(l, `--${serie}: L ${l}`).toBeLessThanOrEqual(maximo);
  });

  it("a exceção da faixa vale só para --chart-5", () => {
    expect(excecoes.every((s) => s === "chart-5")).toBe(true);
  });

  it.each(SERIES)("--%s está dentro da gama sRGB", (serie) => {
    expect(dentroDaGama(oklch(serie)), `--${serie}: ${resolver(serie, ...camadas)}`).toBe(true);
  });

  it.each(SERIES.flatMap((s) => SUPERFICIES.map((f) => [s, f] as const)))(
    "--%s sobre --%s ≥ 3:1",
    (serie, superficie) => {
      const razao = razaoContraste(oklchParaRgb(oklch(serie)), oklchParaRgb(oklch(superficie)));
      expect(razao).toBeGreaterThanOrEqual(NAO_TEXTO);
    },
  );

  const pares = SERIES.flatMap((a, i) => SERIES.slice(i + 1).map((b) => [a, b] as const));
  it.each(pares)("--%s × --%s: ΔE OKLab ≥ 15", (a, b) => {
    expect(deltaEOk(oklch(a), oklch(b))).toBeGreaterThanOrEqual(DISTANCIA_MINIMA);
  });
});
