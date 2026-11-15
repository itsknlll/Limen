import { beforeAll, describe, expect, it } from "vitest";
import {
  formatarData,
  formatarDataHora,
  formatarDecimal,
  formatarDiaMes,
  formatarIdConta,
  formatarInteiro,
  formatarPeriodo,
  rotuloStatus,
} from "./formatar";

// Fuso do processo em UTC-3: se formatarData passar a usar `new Date("2026-11-11")`
// (meia-noite UTC), o dia sai 10/11 e o teste reprova, em qualquer máquina.
beforeAll(() => {
  process.env.TZ = "America/Fortaleza";
});

describe("formatarData", () => {
  it.each([
    ["2026-11-11", "11/11/2026"],
    ["2026-10-13", "13/10/2026"],
    ["2026-01-01", "01/01/2026"],
    ["2025-12-31", "31/12/2025"],
  ])("%s → %s (sem deslocamento de fuso)", (texto, esperado) => {
    expect(formatarData(texto)).toBe(esperado);
  });

  it.each(["", "11/11/2026", "2026-11-11T00:00:00Z", "2026-1-1"])("formato inesperado (%j) volta como veio", (texto) => {
    expect(formatarData(texto)).toBe(texto);
  });
});

describe("formatarDiaMes", () => {
  it("2026-11-11 → 11/11", () => expect(formatarDiaMes("2026-11-11")).toBe("11/11"));
  it("formato inesperado volta como veio", () => expect(formatarDiaMes("x")).toBe("x"));
});

describe("formatarPeriodo", () => {
  it.each([
    ["2026-10-13", "2026-11-11", "13/10 a 11/11/2026"],
    ["2025-12-28", "2026-01-03", "28/12/2025 a 03/01/2026"],
    ["2026-11-11", "2026-11-11", "11/11/2026"],
  ])("%s a %s → %s", (inicio, fim, esperado) => {
    expect(formatarPeriodo(inicio, fim)).toBe(esperado);
  });

  it.each([
    [null, "2026-11-11"],
    ["2026-10-13", null],
    [null, null],
  ])("sem início ou fim (%j, %j) → null", (inicio, fim) => {
    expect(formatarPeriodo(inicio, fim)).toBeNull();
  });
});

describe("formatarDataHora", () => {
  it.each([
    ["2026-11-13T15:44:00Z", "UTC", "13/11/2026 às 15:44"],
    ["2026-11-13T15:44:00Z", "America/Fortaleza", "13/11/2026 às 12:44"],
    ["2026-11-13T15:44:07.123456+00:00", "America/Fortaleza", "13/11/2026 às 12:44"],
    // Virada de dia: 00:30 UTC ainda é dia 12 em UTC-3
    ["2026-11-13T00:30:00+00:00", "America/Fortaleza", "12/11/2026 às 21:30"],
    ["2026-11-13T09:05:00-03:00", "America/Fortaleza", "13/11/2026 às 09:05"],
  ])("%s em %s → %s", (texto, fuso, esperado) => {
    expect(formatarDataHora(texto, fuso)).toBe(esperado);
  });

  it("usa o fuso do navegador quando nenhum é pedido", () => {
    expect(formatarDataHora("2026-11-13T15:44:00Z")).toBe("13/11/2026 às 12:44");
  });

  it.each(["2026-11-13T15:44:00", "2026-11-13", "ontem", ""])("sem fuso explícito (%j) volta como veio", (texto) => {
    expect(formatarDataHora(texto, "UTC")).toBe(texto);
  });
});

describe("formatarDecimal (texto, sem float)", () => {
  it.each([
    ["0.504", "0,504"],
    ["1234.50", "1.234,50"],
    ["1234567.1", "1.234.567,1"],
    ["100", "100"],
    ["1000", "1.000"],
    ["1234", "1.234"],
    ["-12.30", "-12,30"],
    // Um float mostraria 0,30000000000000004 ou perderia os zeros; o texto não.
    ["0.30000000000000000001", "0,30000000000000000001"],
    ["5.00", "5,00"],
  ])("%s → %s", (texto, esperado) => {
    expect(formatarDecimal(texto)).toBe(esperado);
  });

  it.each(["", "abc", "1,5", "1.2.3", "NaN", ".5"])("texto inválido (%j) volta como veio", (texto) => {
    expect(formatarDecimal(texto)).toBe(texto);
  });
});

describe("formatarInteiro", () => {
  it.each([
    [0, "0"],
    [90, "90"],
    [999, "999"],
    // 4 dígitos: o ponto do milhar tem de aparecer (há locais em que o Intl só agrupa a partir de 5)
    [1000, "1.000"],
    [1234, "1.234"],
    [10000, "10.000"],
    [1234567, "1.234.567"],
    [-1234, "-1.234"],
  ])("%i → %s", (numero, esperado) => {
    expect(formatarInteiro(numero)).toBe(esperado);
  });

  it.each([1.5, Number.NaN, Number.POSITIVE_INFINITY])("valor que não é inteiro (%s) volta como texto, sem formatar", (numero) => {
    expect(formatarInteiro(numero)).toBe(String(numero));
  });

  it.each([0, 7, 90, 999, 1000, 1234, 9999, 10000, 99999, 100000, 1234567])(
    "%i: formatarInteiro e formatarDecimal dão o mesmo texto",
    (numero) => {
      expect(formatarInteiro(numero)).toBe(formatarDecimal(String(numero)));
    },
  );
});

describe("formatarIdConta", () => {
  it.each([
    ["4327030343", "432-703-0343"],
    ["1137051091", "113-705-1091"],
  ])("%s → %s", (id, esperado) => {
    expect(formatarIdConta(id)).toBe(esperado);
  });

  it.each(["", "432703034", "43270303431", "432-703-0343", "abcdefghij"])("fora do formato (%j) volta como veio", (id) => {
    expect(formatarIdConta(id)).toBe(id);
  });
});

describe("rotuloStatus", () => {
  it.each([
    ["ENABLED", 1, "ativa"],
    ["ENABLED", 2, "ativas"],
    ["PAUSED", 1, "pausada"],
    ["PAUSED", 0, "pausadas"],
    ["REMOVED", 1, "removida"],
    ["REMOVED", 3, "removidas"],
    ["UNKNOWN", 1, "desconhecida"],
  ])("%s × %i → %s", (status, quantidade, esperado) => {
    expect(rotuloStatus(status, quantidade)).toBe(esperado);
  });

  it.each(["enabled", "NOVO_STATUS", "toString", "__proto__"])("status fora da lista (%s) volta como veio", (status) => {
    expect(rotuloStatus(status)).toBe(status);
  });
});
