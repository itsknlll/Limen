import { describe, expect, it } from "vitest";
import {
  arredondarDecimal,
  EXPOENTE_MAXIMO,
  formatarDecimalCurto,
  formatarMoeda,
  formatarPercentual,
  normalizarDecimal,
} from "./decimal";

// Oráculo: respostas do PostgreSQL 16 (container limen-db, banco limen_teste, 14/11/2026),
// copiadas como vieram. Nenhum valor esperado foi calculado à mão.
//   SELECT x, c, round(x::numeric, c)::text FROM (VALUES ...) AS t(x, c);
const ROUND_DO_POSTGRES: [string, number, string][] = [
  ["3.3333333333333333", 2, "3.33"],
  ["2.345", 2, "2.35"],
  ["-2.345", 2, "-2.35"],
  ["2.355", 2, "2.36"],
  ["0.005", 2, "0.01"],
  ["0.0049999", 2, "0.00"],
  ["9.995", 2, "10.00"],
  ["99.999", 2, "100.00"],
  ["0E-16", 2, "0.00"],
  ["0", 2, "0.00"],
  ["1.5", 0, "2"],
  ["2.5", 0, "3"],
  ["-2.5", 0, "-3"],
  ["-0.004", 2, "0.00"],
  ["1.2", 4, "1.2000"],
  ["1.5E+2", 2, "150.00"],
  ["1.25E-1", 2, "0.13"],
  ["12345678.905", 2, "12345678.91"],
  ["100.00000000000000000000", 2, "100.00"],
  ["0.5", 2, "0.50"],
  ["7", 2, "7.00"],
  ["0.125", 1, "0.1"],
  ["-0.0", 2, "0.00"],
  // Grande demais para float: (x::float8)::numeric dá 12345678901234600000.
  ["12345678901234567890.125", 2, "12345678901234567890.13"],
];

//   SELECT x, trim_scale(x::numeric)::text FROM (VALUES ...) AS t(x);
const TRIM_SCALE_DO_POSTGRES: [string, string][] = [
  ["0E-16", "0"],
  ["3.3333333333333333", "3.3333333333333333"],
  ["100.00000000000000000000", "100"],
  ["1.2300000000000000", "1.23"],
  ["1.5E+2", "150"],
  ["-0.0", "0"],
  ["-2.50", "-2.5"],
  ["7", "7"],
  ["0.000001", "0.000001"],
  ["1.25E-1", "0.125"],
  ["1E+3", "1000"],
  ["12345678901234567890.1250", "12345678901234567890.125"],
];

const INVALIDOS = ["", " ", "abc", "1,5", "1.2.3", ".5", "E5", "1e", "NaN", "Infinity", "--1", "0x10"];

describe("arredondarDecimal (oráculo: round() do PostgreSQL)", () => {
  it.each(ROUND_DO_POSTGRES)("round(%s, %i) = %s", (texto, casas, esperado) => {
    expect(arredondarDecimal(texto, casas)).toBe(esperado);
  });

  it("empate vai para longe do zero, não para o par (2.5 → 3, como o PostgreSQL)", () => {
    expect([arredondarDecimal("2.5", 0), arredondarDecimal("3.5", 0)]).toEqual(["3", "4"]);
  });

  it.each(INVALIDOS)("texto inválido %j → null", (texto) => {
    expect(arredondarDecimal(texto, 2)).toBeNull();
  });

  it("expoente acima do limite → null (não monta texto gigante)", () => {
    expect(arredondarDecimal(`1E+${EXPOENTE_MAXIMO + 1}`, 2)).toBeNull();
    expect(arredondarDecimal(`1E-${EXPOENTE_MAXIMO + 1}`, 2)).toBeNull();
    expect(arredondarDecimal(`1E+${EXPOENTE_MAXIMO}`, 0)).toBe(`1${"0".repeat(EXPOENTE_MAXIMO)}`);
  });

  it.each([-1, 1.5, Number.NaN])("casas inválidas (%s) é erro de programação", (casas) => {
    expect(() => arredondarDecimal("1", casas)).toThrow(RangeError);
  });
});

describe("normalizarDecimal (oráculo: trim_scale() do PostgreSQL)", () => {
  it.each(TRIM_SCALE_DO_POSTGRES)("trim_scale(%s) = %s", (texto, esperado) => {
    expect(normalizarDecimal(texto)).toBe(esperado);
  });

  it.each(INVALIDOS)("texto inválido %j → null", (texto) => {
    expect(normalizarDecimal(texto)).toBeNull();
  });
});

describe("formatação para a tela", () => {
  it.each([
    ["3.3333333333333333", "3,33%"],
    ["0E-16", "0,00%"], // o CTR zero que a API realmente manda
    ["100.00000000000000000000", "100,00%"],
    ["2.345", "2,35%"],
  ])("formatarPercentual(%s) = %s", (texto, esperado) => {
    expect(formatarPercentual(texto)).toBe(esperado);
  });

  it.each([
    ["1234.5", "R$\u00A01.234,50"],
    ["0.125", "R$\u00A00,13"],
    ["12345678.905", "R$\u00A012.345.678,91"],
    ["0E-16", "R$\u00A00,00"],
  ])("formatarMoeda(%s) = %s", (texto, esperado) => {
    expect(formatarMoeda(texto)).toBe(esperado);
  });

  it("moeda usa espaço inseparável entre R$ e o número (não quebra a linha)", () => {
    expect(formatarMoeda("1")).not.toContain(" ");
  });

  it.each([
    ["1.500000", "1,5"],
    ["0E-16", "0"],
    ["1234.000001", "1.234,000001"],
    ["3", "3"],
  ])("formatarDecimalCurto(%s) = %s", (texto, esperado) => {
    expect(formatarDecimalCurto(texto)).toBe(esperado);
  });

  it("texto inválido volta como veio nas três funções", () => {
    expect([formatarPercentual("abc"), formatarMoeda("abc"), formatarDecimalCurto("abc")]).toEqual([
      "abc",
      "abc",
      "abc",
    ]);
  });
});
