import { describe, expect, it, vi } from "vitest";
import { assinarMenosMovimento, CONSULTA_MENOS_MOVIMENTO, prefereMenosMovimento, type MatchMedia } from "./movimento";

/**
 * matchMedia falso: só responde à consulta exata (um erro de digitação nela reprova o
 * teste) e permite trocar a preferência "com a página aberta", disparando "change".
 */
function matchMediaFalso(inicial: boolean) {
  let reduz = inicial;
  const ouvintes = new Set<() => void>();
  const matchMedia: MatchMedia = (consulta) => {
    if (consulta !== CONSULTA_MENOS_MOVIMENTO) throw new Error(`consulta inesperada: ${consulta}`);
    return {
      get matches() {
        return reduz;
      },
      addEventListener: (_tipo: string, ouvinte: () => void) => void ouvintes.add(ouvinte),
      removeEventListener: (_tipo: string, ouvinte: () => void) => void ouvintes.delete(ouvinte),
    } as unknown as MediaQueryList;
  };
  const mudar = (valor: boolean) => {
    reduz = valor;
    for (const ouvinte of ouvintes) ouvinte();
  };
  return { matchMedia, mudar, ouvintes };
}

describe("prefereMenosMovimento", () => {
  it("a consulta é a do padrão CSS", () => {
    expect(CONSULTA_MENOS_MOVIMENTO).toBe("(prefers-reduced-motion: reduce)");
  });

  it.each([true, false])("lê a preferência do sistema (%s)", (valor) => {
    expect(prefereMenosMovimento(matchMediaFalso(valor).matchMedia)).toBe(valor);
  });

  it("sem matchMedia → false", () => {
    expect(prefereMenosMovimento(null)).toBe(false);
  });

  it("matchMedia que lança erro → false, sem propagar", () => {
    expect(prefereMenosMovimento(() => { throw new Error("bloqueado"); })).toBe(false);
  });
});

describe("assinarMenosMovimento", () => {
  it("avisa quando a preferência muda com a página aberta, e o valor novo é lido", () => {
    const { matchMedia, mudar } = matchMediaFalso(false);
    const avisar = vi.fn();
    assinarMenosMovimento(avisar, matchMedia);

    mudar(true);
    expect(avisar).toHaveBeenCalledTimes(1);
    expect(prefereMenosMovimento(matchMedia)).toBe(true);

    mudar(false);
    expect(avisar).toHaveBeenCalledTimes(2);
    expect(prefereMenosMovimento(matchMedia)).toBe(false);
  });

  it("depois de cancelar, não avisa mais e não deixa ouvinte para trás", () => {
    const { matchMedia, mudar, ouvintes } = matchMediaFalso(false);
    const avisar = vi.fn();
    const cancelar = assinarMenosMovimento(avisar, matchMedia);
    expect(ouvintes.size).toBe(1);

    cancelar();
    mudar(true);
    expect(avisar).not.toHaveBeenCalled();
    expect(ouvintes.size).toBe(0);
  });

  it("sem matchMedia → assinatura vazia que pode ser cancelada", () => {
    expect(() => assinarMenosMovimento(() => {}, null)()).not.toThrow();
  });
});
