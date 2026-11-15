// Textos e valores da tela de Regras (Fase 3, etapa 4): funções puras, sem React nem fetch.
// O limiar chega da API como NUMERIC com 6 casas ("1.000000", "100.000000", "0.000000";
// conferido no banco limen em 15/11) e é tratado só como texto, via lib/decimal.ts:
// nada aqui usa Number nem parseFloat.

import type { components } from "@/api/esquema";
import { normalizarDecimal } from "@/lib/decimal";
import { formatarDecimal } from "@/lib/formatar";
import { lerLimiar, type Metrica, type Operador, type ValoresFormulario } from "./validacao";

export type Regra = components["schemas"]["RegraSaida"];
type Condicao = components["schemas"]["CondicaoSaida"];
type CondicaoFormulario = ValoresFormulario["condicoes"][number];

export const ROTULOS_METRICA: Record<Metrica, string> = {
  impressoes: "Impressões",
  cliques: "Cliques",
  custo: "Custo",
  conversoes: "Conversões",
  ctr: "CTR",
  cpc: "CPC",
};

/** Por extenso, para o leitor de tela (que leria "<" como "menos") e para as opções do select. */
export const ROTULOS_OPERADOR: Record<Operador, string> = {
  "<": "menor que",
  "<=": "menor ou igual a",
  ">": "maior que",
  ">=": "maior ou igual a",
  "==": "igual a",
};

/** Unidade como o motor calcula: CTR em %, custo e CPC em R$; as outras sem unidade. */
const UNIDADES: Partial<Record<Metrica, "%" | "R$">> = { ctr: "%", custo: "R$", cpc: "R$" };

/** A API tipa métrica e operador como texto: o que não está no mapa volta como veio (Object.hasOwn: "toString" não é rótulo). */
function doMapa(mapa: Record<string, string>, chave: string): string {
  return Object.hasOwn(mapa, chave) ? mapa[chave]! : chave;
}

export const rotuloMetrica = (metrica: string) => doMapa(ROTULOS_METRICA, metrica);
export const rotuloOperador = (operador: string) => doMapa(ROTULOS_OPERADOR, operador);

function comUnidade(metrica: string, numero: string): string {
  const unidade = Object.hasOwn(UNIDADES, metrica) ? UNIDADES[metrica as Metrica] : undefined;
  if (unidade === "%") return `${numero}%`;
  if (unidade === "R$") return `R$\u00A0${numero}`;
  return numero;
}

/**
 * Limiar da API para exibir: ("ctr", "1.000000") → "1%", ("custo", "1234.500000") → "R$ 1.234,5".
 * Sem arredondar (o limiar tem até 6 casas; formatarMoeda cortaria "0.125" em "0,13").
 * Texto inválido volta como veio, com a unidade.
 */
export function formatarLimiar(metrica: string, limiar: string): string {
  const valor = normalizarDecimal(limiar);
  return comUnidade(metrica, valor === null ? limiar : formatarDecimal(valor));
}

export interface TextoCondicao {
  visivel: string;
  acessivel: string;
}

/** "CTR < 1%" na tela; "CTR menor que 1%" para o leitor de tela. */
export function textoCondicao({ metrica, operador, limiar }: Pick<Condicao, "metrica" | "operador" | "limiar">): TextoCondicao {
  const nome = rotuloMetrica(metrica);
  const valor = formatarLimiar(metrica, limiar);
  return { visivel: `${nome} ${operador} ${valor}`, acessivel: `${nome} ${rotuloOperador(operador)} ${valor}` };
}

/** O backend devolve em ordem (order_by no modelo); ordenar de novo não custa e não depende disso. */
function emOrdem(condicoes: readonly Condicao[]): Condicao[] {
  return [...condicoes].sort((a, b) => a.ordem - b.ordem);
}

/** Condições ligadas por E (como o motor), na ordem da regra. */
export function textoCondicoes(regra: Pick<Regra, "condicoes">): TextoCondicao {
  const partes = emOrdem(regra.condicoes).map(textoCondicao);
  return {
    visivel: partes.map((p) => p.visivel).join(" e "),
    acessivel: partes.map((p) => p.acessivel).join(" e "),
  };
}

/** Condição em branco para "Adicionar condição": um objeto novo a cada chamada. */
export function novaCondicao(): CondicaoFormulario {
  return { metrica: "", operador: "", limiar: "" };
}

/** Formulário de /regras/nova: regra ativa, com uma condição em branco. */
export function valoresNovaRegra(): ValoresFormulario {
  return { codigo: "", nome: "", ativa: true, condicoes: [novaCondicao()] };
}

/**
 * Regra da API → formulário de edição. O limiar volta normalizado ("7.500000" → "7.5"),
 * só com texto. Se a API mandasse um limiar ilegível, ele iria como veio, e a validação
 * do formulário mostraria o erro no campo (em vez de trocar por um valor inventado).
 */
export function valoresIniciais(regra: Regra): ValoresFormulario {
  return {
    codigo: regra.codigo,
    nome: regra.nome,
    ativa: regra.ativa,
    condicoes: emOrdem(regra.condicoes).map(({ metrica, operador, limiar }) => ({
      metrica,
      operador,
      limiar: normalizarDecimal(limiar) ?? limiar,
    })),
  };
}

/**
 * O que será salvo, mostrado abaixo do campo limiar (pendência a): "1.000" digitado vira
 * "1", porque o ponto é separador decimal. Sem separador de milhar ("1000" → "1000"),
 * senão a prévia de "1000" mostraria "1.000" e repetiria a confusão. Vazio ou inválido →
 * null (quem fala é a mensagem de erro do campo).
 */
export function previaLimiar(metrica: string, texto: string): string | null {
  const leitura = lerLimiar(texto);
  return leitura.ok ? comUnidade(metrica, leitura.valor.replace(".", ",")) : null;
}
