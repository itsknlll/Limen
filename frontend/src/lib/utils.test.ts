import { describe, expect, it } from "vitest";
import { cn } from "./utils";

// Guarda do pacote `cn` (0.5.2, novo): o que os componentes do shadcn esperam dele.
describe("cn", () => {
  it("a última classe conflitante do Tailwind vence", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("ignora valores falsos, como o clsx", () => {
    expect(cn("a", false, undefined, null, "", "b")).toBe("a b");
  });

  it("variante só é substituída pela mesma variante (causa do KPI com 14 px)", () => {
    const titulo = "text-base leading-snug group-data-[size=sm]/card:text-sm"; // CardTitle
    expect(cn(titulo, "text-3xl")).toContain("group-data-[size=sm]/card:text-sm");
    expect(cn(titulo, "text-3xl group-data-[size=sm]/card:text-3xl")).not.toContain(
      "group-data-[size=sm]/card:text-sm",
    );
  });

  it("className passado por fora sobrescreve a cor padrão do componente", () => {
    expect(cn("bg-primary text-primary-foreground", "bg-regra-r1-suave")).toBe(
      "text-primary-foreground bg-regra-r1-suave",
    );
  });
});
