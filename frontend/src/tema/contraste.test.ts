import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  compor,
  dentroDaGama,
  lerBloco,
  lerOklch,
  oklchParaRgb,
  razaoContraste,
  resolver,
  type Rgb,
} from "./contraste";

// Oráculo da paleta: os tokens são lidos de src/index.css (a fonte da verdade) e
// cada par texto/superfície tem de atingir o mínimo WCAG 2.x. Se alguém mudar uma
// cor e quebrar o contraste, este teste reprova.

const css = readFileSync(new URL("../index.css", import.meta.url), "utf8");
const html = readFileSync(new URL("../../index.html", import.meta.url), "utf8");
const raiz = lerBloco(css, ":root");
const escuro = lerBloco(css, ".dark");

const TEMAS = {
  claro: [raiz],
  escuro: [escuro, raiz], // .dark só redefine; o resto vem do :root
} as const;

const TEXTO = 4.5; // WCAG 1.4.3 (texto normal)
const NAO_TEXTO = 3; // WCAG 1.4.11 (bordas de campo, foco, ícones, séries de gráfico)

const SUPERFICIES = ["background", "card", "popover", "muted"];
const TEXTOS = [
  "foreground",
  "muted-foreground",
  "primary",
  "destructive",
  "regra-r1",
  "regra-r2",
  "regra-r3",
  "regra-outra",
];

describe("razaoContraste", () => {
  it("preto × branco = 21:1 e cor igual = 1:1", () => {
    const branco = oklchParaRgb(lerOklch("oklch(1 0 0)"));
    const preto = oklchParaRgb(lerOklch("oklch(0 0 0)"));
    expect(razaoContraste(branco, preto)).toBeCloseTo(21, 2);
    expect(razaoContraste(branco, branco)).toBe(1);
  });

  it("é simétrica", () => {
    const a = oklchParaRgb(lerOklch("oklch(0.51 0.225 277)"));
    const b = oklchParaRgb(lerOklch("oklch(0.985 0.003 264)"));
    expect(razaoContraste(a, b)).toBe(razaoContraste(b, a));
  });

  it("recusa formato que não é oklch(L C H)", () => {
    expect(() => lerOklch("#ffffff")).toThrow();
    expect(() => lerOklch("oklch(1 0 0 / 10%)")).toThrow();
  });
});

describe.each(Object.entries(TEMAS))("tema %s", (_, camadas) => {
  const cor = (token: string): Rgb => oklchParaRgb(lerOklch(resolver(token, ...camadas)));
  const contraste = (a: string, b: string) => razaoContraste(cor(a), cor(b));

  it("todos os tokens de cor estão dentro da gama sRGB", () => {
    const nomes = Object.keys(camadas[0]).filter((n) => n !== "radius");
    for (const nome of nomes) {
      const valor = resolver(nome, ...camadas);
      expect(dentroDaGama(lerOklch(valor)), `--${nome}: ${valor}`).toBe(true);
    }
  });

  const paresTexto = TEXTOS.flatMap((t) => SUPERFICIES.map((s) => [t, s] as const));
  it.each(paresTexto)("texto --%s sobre --%s ≥ 4,5:1", (texto, superficie) => {
    expect(contraste(texto, superficie)).toBeGreaterThanOrEqual(TEXTO);
  });

  it.each([
    ["primary-foreground", "primary"],
    ["regra-r1", "regra-r1-suave"],
    ["regra-r2", "regra-r2-suave"],
    ["regra-r3", "regra-r3-suave"],
    ["regra-outra", "regra-outra-suave"],
  ])("texto --%s sobre --%s ≥ 4,5:1", (texto, superficie) => {
    expect(contraste(texto, superficie)).toBeGreaterThanOrEqual(TEXTO);
  });

  it.each(["input", "ring"].flatMap((t) => ["background", "card"].map((s) => [t, s] as const)))(
    "--%s sobre --%s ≥ 3:1",
    (token, superficie) => {
      expect(contraste(token, superficie)).toBeGreaterThanOrEqual(NAO_TEXTO);
    },
  );

  // Estilo Nova: botão/selo/item de menu "destructive" = text-destructive sobre
  // bg-destructive/10 (claro) ou /20 (escuro), por cima do fundo.
  it.each(["background", "card"])("text-destructive sobre bg-destructive translúcido em --%s ≥ 4,5:1", (s) => {
    const alfa = camadas.length === 1 ? 0.1 : 0.2;
    const fundo = compor(cor("destructive"), alfa, cor(s));
    expect(razaoContraste(cor("destructive"), fundo)).toBeGreaterThanOrEqual(TEXTO);
  });
});

describe("<style> anti-flash do index.html", () => {
  const estilo = /<style id="fundo-inicial">([\s\S]*?)<\/style>/.exec(html)?.[1] ?? "";
  const fundoDe = (seletor: string) =>
    new RegExp(`(?:^|\\s)${seletor.replace(".", "\\.")}\\s*\\{\\s*background-color:\\s*([^;]+);`).exec(estilo)?.[1];

  it("usa o mesmo --background do CSS nos dois temas", () => {
    expect(fundoDe("html")).toBe(resolver("background", raiz));
    expect(fundoDe("html.dark")).toBe(resolver("background", escuro, raiz));
  });
});
