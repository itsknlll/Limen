import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// Em XML (e SVG é XML), "--" é proibido dentro de comentário: o navegador recusa o
// arquivo inteiro ("Comment must not contain '--'"). Aconteceu ao citar um token CSS.
const svg = readFileSync(new URL("../public/favicon.svg", import.meta.url), "utf8");
const comentarios = [...svg.matchAll(/<!--([\s\S]*?)-->/g)].map((m) => m[1]!);

describe("public/favicon.svg", () => {
  it("é um SVG", () => {
    expect(svg.trimStart().startsWith("<svg")).toBe(true);
  });

  it("nenhum comentário contém '--'", () => {
    for (const comentario of comentarios) expect(comentario).not.toContain("--");
  });

  it("todo comentário aberto foi fechado", () => {
    expect(svg.split("<!--").length).toBe(svg.split("-->").length);
  });
});
