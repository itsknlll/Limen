// Validação do formulário de regras (Fase 3). Espelha o RegraEntrada do backend
// (app/api/esquemas.py) e o bloqueio de R1 a R3 (app/servicos/regras.py). Oráculo dos
// testes: respostas reais do Pydantic, colhidas no venv (validacao.test.ts).
//
// O limiar é texto do começo ao fim, sem Number nem parseFloat: a vírgula vira ponto, e
// casas e algarismos são contados sobre o texto normalizado por lib/decimal.ts, como o
// Pydantic conta (zeros à esquerda e à direita não contam: "1.0000000" tem 0 casas).
// Tamanhos de texto contam caracteres (Array.from), como o len() do Python; o .length do
// JavaScript contaria um emoji como 2.
//
// Diferenças de propósito (a tela é mais rígida, nunca o contrário): o limiar não aceita
// sinal, expoente nem separador sem algarismo dos dois lados ("-0", "+1", ".5", "5.",
// "1e3"), e o nome não pode ser só espaços. Espaços nas pontas do nome e do limiar são
// removidos antes de enviar. Códigos R1 a R3 são recusados aqui (o Pydantic aceita; no
// backend quem recusa é o serviço, com 409 regra_referencia).

import { z } from "zod";
import type { components } from "@/api/esquema";
import { normalizarDecimal } from "@/lib/decimal";

export type Metrica = components["schemas"]["Metrica"];
export type Operador = components["schemas"]["Operador"];
export type CorpoRegra = components["schemas"]["RegraEntrada"];

export const METRICAS = ["impressoes", "cliques", "custo", "conversoes", "ctr", "cpc"] as const satisfies readonly Metrica[];
export const OPERADORES = ["<", "<=", ">", ">=", "=="] as const satisfies readonly Operador[];

/** Se o backend ganhar uma métrica ou um operador, o typecheck reprova até a lista ser atualizada. */
type Cobre<T, L extends readonly unknown[]> = [Exclude<T, L[number]>] extends [never] ? true : false;
export const LISTAS_COMPLETAS: [Cobre<Metrica, typeof METRICAS>, Cobre<Operador, typeof OPERADORES>] = [true, true];

export const LIMITES = {
  codigo: 20,
  nome: 120,
  condicoesMin: 1,
  condicoesMax: 10,
  casas: 6,
  algarismosInteiros: 12,
} as const;
export const CODIGOS_REFERENCIA = ["R1", "R2", "R3"] as const;
export const PADRAO_CODIGO = /^[A-Za-z0-9_-]+$/;
const LIMIAR_DIGITADO = /^\d+(?:[.,]\d+)?$/;

export const MENSAGENS = {
  codigoVazio: "Informe o código.",
  codigoLongo: `Use no máximo ${LIMITES.codigo} caracteres.`,
  codigoFormato: "Use só letras sem acento, algarismos, _ ou -, sem espaços.",
  codigoReferencia: "R1, R2 e R3 são as regras de referência da tabela: escolha outro código.",
  nomeVazio: "Informe o nome.",
  nomeLongo: `Use no máximo ${LIMITES.nome} caracteres.`,
  metrica: "Escolha uma métrica da lista.",
  operador: "Escolha um operador da lista.",
  limiarVazio: "Informe o limiar.",
  limiarSinal: "Escreva o limiar sem sinal: ele não pode ser negativo.",
  limiarFormato: "Use só algarismos, com vírgula ou ponto antes das casas decimais (ex.: 1,5).",
  limiarCasas: `Use no máximo ${LIMITES.casas} casas decimais.`,
  limiarInteiros: `Use no máximo ${LIMITES.algarismosInteiros} algarismos antes da vírgula.`,
  condicoesPoucas: "A regra precisa de pelo menos uma condição.",
  condicoesMuitas: `Use no máximo ${LIMITES.condicoesMax} condições.`,
} as const;

const tamanho = (texto: string) => Array.from(texto).length;

export type Leitura = { ok: true; valor: string } | { ok: false; erro: string };

/** Limiar digitado → texto normalizado para enviar (" 1,50 " → "1.5"), ou a mensagem do erro. */
export function lerLimiar(texto: string): Leitura {
  const limpo = texto.trim();
  if (limpo === "") return { ok: false, erro: MENSAGENS.limiarVazio };
  if (/^[+-]/.test(limpo)) return { ok: false, erro: MENSAGENS.limiarSinal };
  if (!LIMIAR_DIGITADO.test(limpo)) return { ok: false, erro: MENSAGENS.limiarFormato };
  const valor = normalizarDecimal(limpo.replace(",", "."));
  if (valor === null) return { ok: false, erro: MENSAGENS.limiarFormato };
  const [inteira = "", fracao = ""] = valor.split(".");
  if (fracao.length > LIMITES.casas) return { ok: false, erro: MENSAGENS.limiarCasas };
  // Em "0.5" nenhum algarismo inteiro conta, como no Pydantic.
  const algarismosInteiros = inteira === "0" ? 0 : inteira.length;
  if (algarismosInteiros > LIMITES.algarismosInteiros) return { ok: false, erro: MENSAGENS.limiarInteiros };
  return { ok: true, valor };
}

/** Sem distinguir maiúsculas, como o serviço do backend ("r1" seria confundida com a R1). */
export function ehCodigoReferencia(codigo: string): boolean {
  return (CODIGOS_REFERENCIA as readonly string[]).includes(codigo.toUpperCase());
}

export function erroCodigo(codigo: string): string | null {
  if (codigo === "") return MENSAGENS.codigoVazio;
  if (tamanho(codigo) > LIMITES.codigo) return MENSAGENS.codigoLongo;
  if (!PADRAO_CODIGO.test(codigo)) return MENSAGENS.codigoFormato;
  if (ehCodigoReferencia(codigo)) return MENSAGENS.codigoReferencia;
  return null;
}

/** O tamanho é medido no nome sem espaços nas pontas, que é o que vai para o backend. */
export function erroNome(nome: string): string | null {
  const limpo = nome.trim();
  if (limpo === "") return MENSAGENS.nomeVazio;
  if (tamanho(limpo) > LIMITES.nome) return MENSAGENS.nomeLongo;
  return null;
}

function daLista<T extends string>(lista: readonly T[], mensagem: string) {
  return z.string().transform((valor, ctx): T => {
    const achado = lista.find((item) => item === valor);
    if (achado !== undefined) return achado;
    ctx.addIssue({ code: "custom", message: mensagem });
    return z.NEVER;
  });
}

const esquemaCondicao = z.object({
  metrica: daLista(METRICAS, MENSAGENS.metrica),
  operador: daLista(OPERADORES, MENSAGENS.operador),
  limiar: z.string().transform((texto, ctx) => {
    const leitura = lerLimiar(texto);
    if (leitura.ok) return leitura.valor;
    ctx.addIssue({ code: "custom", message: leitura.erro });
    return z.NEVER;
  }),
});

export const esquemaRegra = z.object({
  codigo: z.string().superRefine((codigo, ctx) => {
    const erro = erroCodigo(codigo);
    if (erro !== null) ctx.addIssue({ code: "custom", message: erro });
  }),
  nome: z.string().transform((nome, ctx) => {
    const erro = erroNome(nome);
    if (erro === null) return nome.trim();
    ctx.addIssue({ code: "custom", message: erro });
    return z.NEVER;
  }),
  ativa: z.boolean(),
  condicoes: z
    .array(esquemaCondicao)
    .min(LIMITES.condicoesMin, MENSAGENS.condicoesPoucas)
    .max(LIMITES.condicoesMax, MENSAGENS.condicoesMuitas),
});

export type ValoresFormulario = z.input<typeof esquemaRegra>;

/** A saída do esquema é exatamente o corpo de POST/PUT /regras: o typecheck confere. */
function paraCorpo(saida: z.output<typeof esquemaRegra>): CorpoRegra {
  return saida;
}

export type ResultadoValidacao = { ok: true; corpo: CorpoRegra } | { ok: false; erros: Record<string, string> };

/** Erros por caminho ("codigo", "condicoes.1.limiar"); fica o primeiro erro de cada campo. */
export function validarRegra(valores: ValoresFormulario): ResultadoValidacao {
  const resultado = esquemaRegra.safeParse(valores);
  if (resultado.success) return { ok: true, corpo: paraCorpo(resultado.data) };
  const erros: Record<string, string> = {};
  for (const problema of resultado.error.issues) {
    erros[problema.path.map(String).join(".")] ??= problema.message;
  }
  return { ok: false, erros };
}

/** Corpo do PUT que ativa uma regra vinda da API: a mesma validação do formulário, com ativa = true. */
export function corpoParaAtivar(regra: components["schemas"]["RegraSaida"]): ResultadoValidacao {
  return validarRegra({
    codigo: regra.codigo,
    nome: regra.nome,
    ativa: true,
    condicoes: regra.condicoes.map(({ metrica, operador, limiar }) => ({ metrica, operador, limiar })),
  });
}
