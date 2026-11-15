// Decimais da API chegam como texto (Decimal do Python serializado pelo Pydantic).
// Formas vistas: "12.50", "-3", "3.3333333333333333" e, para o zero de uma divisão
// NUMERIC da view, "0E-16" (com expoente). Nada aqui usa float: o texto vira dígitos
// inteiros + escala, e as contas são feitas com BigInt.
//
// Oráculo dos testes (decimal.test.ts): round() e trim_scale() do PostgreSQL 16.

import { formatarDecimal } from "./formatar";

/** Sinal, parte inteira, fração e expoente. Exige dígito antes do ponto, como o str() do Python. */
const FORMA = /^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/;

/** A API nunca chega perto disso; o limite evita montar textos gigantes ("1E+999999"). */
export const EXPOENTE_MAXIMO = 1000;

/** valor = ±inteiro × 10^-escala, com escala ≥ 0. */
interface Partes {
  negativo: boolean;
  inteiro: bigint;
  escala: number;
}

function ler(texto: string): Partes | null {
  const m = FORMA.exec(texto.trim());
  if (!m) return null;
  const [, sinal, parteInteira, fracao = "", expoenteTexto = "0"] = m;
  const expoente = Number(expoenteTexto);
  if (Math.abs(expoente) > EXPOENTE_MAXIMO) return null;
  let digitos = parteInteira! + fracao;
  let escala = fracao.length - expoente;
  if (escala < 0) {
    digitos += "0".repeat(-escala);
    escala = 0;
  }
  return { negativo: sinal === "-", inteiro: BigInt(digitos), escala };
}

/** Escreve com exatamente `escala` casas. Zero nunca leva sinal ("-0.00" → "0.00"), como no PostgreSQL. */
function escrever({ negativo, inteiro, escala }: Partes): string {
  const digitos = inteiro.toString().padStart(escala + 1, "0");
  const corte = digitos.length - escala;
  const texto = escala === 0 ? digitos : `${digitos.slice(0, corte)}.${digitos.slice(corte)}`;
  return negativo && inteiro !== 0n ? `-${texto}` : texto;
}

/** Forma simples, sem expoente nem zeros à direita: "0E-16" → "0", "1.2300" → "1.23". Inválido → null. */
export function normalizarDecimal(texto: string): string | null {
  const partes = ler(texto);
  if (!partes) return null;
  let { inteiro, escala } = partes;
  while (escala > 0 && inteiro % 10n === 0n) {
    inteiro /= 10n;
    escala -= 1;
  }
  return escrever({ ...partes, inteiro, escala });
}

/**
 * Arredonda para `casas` casas, sempre com essa quantidade: ("7", 2) → "7.00".
 * Empate vai para longe do zero, como o round() do PostgreSQL para NUMERIC:
 * 2.5 → 3 e -2.5 → -3 (não o "empate para o par" do Decimal do Python).
 * Inválido → null.
 */
export function arredondarDecimal(texto: string, casas: number): string | null {
  if (!Number.isInteger(casas) || casas < 0) throw new RangeError(`casas inválidas: ${casas}`);
  const partes = ler(texto);
  if (!partes) return null;
  if (partes.escala <= casas) {
    const fator = 10n ** BigInt(casas - partes.escala);
    return escrever({ ...partes, inteiro: partes.inteiro * fator, escala: casas });
  }
  const divisor = 10n ** BigInt(partes.escala - casas);
  let inteiro = partes.inteiro / divisor;
  // Só a magnitude é arredondada (o sinal fica à parte), então somar 1 no empate
  // já afasta do zero nos dois sinais.
  if ((partes.inteiro % divisor) * 2n >= divisor) inteiro += 1n;
  return escrever({ ...partes, inteiro, escala: casas });
}

/** CTR da API (já em %): "3.3333333333333333" → "3,33%". Texto inválido volta como veio. */
export function formatarPercentual(texto: string, casas = 2): string {
  const valor = arredondarDecimal(texto, casas);
  return valor === null ? texto : `${formatarDecimal(valor)}%`;
}

/** Reais com 2 casas: "1234.5" → "R$ 1.234,50", com espaço inseparável (como o Intl). Inválido volta como veio. */
export function formatarMoeda(texto: string): string {
  const valor = arredondarDecimal(texto, 2);
  return valor === null ? texto : `R$\u00A0${formatarDecimal(valor)}`;
}

/** Sem casas inúteis: "1.500000" → "1,5" (conversões admitem fração). Inválido volta como veio. */
export function formatarDecimalCurto(texto: string): string {
  const valor = normalizarDecimal(texto);
  return valor === null ? texto : formatarDecimal(valor);
}
