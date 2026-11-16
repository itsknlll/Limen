// Decisões do formulário de avaliação (Fase 3, etapa 5) que não dependem do React
// (testadas no Vitest; a interface fica para o Playwright da Fase 4). A validação e o
// corpo do pedido são do pedido.ts (etapa 2); os erros do servidor, do api/campos.ts.
//
// Um estado de erros só, trocado inteiro a cada envio: o cliente valida antes de enviar e
// o servidor só responde se o cliente deixou passar, então os dois nunca aparecem juntos.

import { errosNosCamposAvaliacao } from "@/api/campos";
import type { Campanha } from "@/campanhas/dados";
import { rotuloStatus } from "@/lib/formatar";
import { montarPedidoAvaliacao, type CampoAvaliacao, type CorpoAvaliacao, type FormularioAvaliacao } from "./pedido";

export type ErrosAvaliacao = Partial<Record<CampoAvaliacao, string>>;
type CampanhaDaLista = Pick<Campanha, "id" | "nome" | "status">;

export const FORMULARIO_INICIAL: FormularioAvaliacao = { campanhaId: "", inicio: "", fim: "", incluirPausadas: false };

/** Ordem dos campos na tela: o foco vai para o primeiro com erro. */
const ORDEM_DOS_CAMPOS: readonly CampoAvaliacao[] = ["campanhaId", "inicio", "fim"];

export function primeiroCampoComErro(erros: ErrosAvaliacao): CampoAvaliacao | null {
  return ORDEM_DOS_CAMPOS.find((campo) => erros[campo] !== undefined) ?? null;
}

export type DecisaoEnvio =
  | { acao: "ignorar" }
  | { acao: "corrigir"; erros: ErrosAvaliacao; foco: CampoAvaliacao }
  | { acao: "enviar"; corpo: CorpoAvaliacao };

/**
 * O que fazer ao enviar. Com um pedido em andamento, ignora: o botão usa aria-disabled
 * (não disabled, para não perder o foco), então o clique chega e é barrado aqui. Cada
 * POST /avaliacoes cria uma linha nova no histórico.
 */
export function decidirEnvio(
  form: FormularioAvaliacao,
  campanhas: readonly CampanhaDaLista[],
  pendente: boolean,
): DecisaoEnvio {
  if (pendente) return { acao: "ignorar" };
  const resultado = montarPedidoAvaliacao(form, campanhas);
  if (resultado.ok) return { acao: "enviar", corpo: resultado.corpo };
  return { acao: "corrigir", erros: resultado.erros, foco: primeiroCampoComErro(resultado.erros)! };
}

export interface DepoisDoErro {
  erros: ErrosAvaliacao;
  foco: CampoAvaliacao | null;
  /** Há erro que não é de campo (período invertido, Google, rede): a tela mostra o EstadoErro. */
  restante: boolean;
}

/** Erro do POST /avaliacoes: campos recusados (só os do formulário) e o resto para o EstadoErro. */
export function depoisDoErro(erro: unknown): DepoisDoErro {
  const { campos, restante } = errosNosCamposAvaliacao(erro);
  const erros: ErrosAvaliacao = {};
  for (const campo of ORDEM_DOS_CAMPOS) if (Object.hasOwn(campos, campo)) erros[campo] = campos[campo];
  return { erros, foco: primeiroCampoComErro(erros), restante };
}

/** Ao editar um campo, o erro dele some (os outros ficam até o próximo envio). */
export function semErroNoCampo(erros: ErrosAvaliacao, campo: CampoAvaliacao): ErrosAvaliacao {
  if (!Object.hasOwn(erros, campo)) return erros;
  const resto = { ...erros };
  delete resto[campo];
  return resto;
}

// O Select do Radix trata value "" como "nada escolhido" (mostra o placeholder), então
// "todas as campanhas" usa um valor próprio no select e vira "" no formulário.
export const VALOR_TODAS = "todas";

export function valorDoSelect(campanhaId: string): string {
  return campanhaId === "" ? VALOR_TODAS : campanhaId;
}

export function campanhaDoSelect(valor: string): string {
  return valor === VALOR_TODAS ? "" : valor;
}

/** Opções do select: "Todas" primeiro, depois as campanhas na ordem da API, com o status quando não está ativa. */
export function opcoesCampanha(campanhas: readonly CampanhaDaLista[]): { valor: string; rotulo: string }[] {
  return [
    { valor: VALOR_TODAS, rotulo: "Todas as campanhas" },
    ...campanhas.map((c) => ({
      valor: String(c.id),
      rotulo: c.status === "ENABLED" ? c.nome : `${c.nome} (${rotuloStatus(c.status)})`,
    })),
  ];
}

/** Aviso de campanha pausada ou removida (do pedido.ts), mostrado abaixo do select enquanto se preenche. */
export function avisoAtual(form: FormularioAvaliacao, campanhas: readonly CampanhaDaLista[]): string | null {
  const resultado = montarPedidoAvaliacao(form, campanhas);
  return resultado.ok ? resultado.aviso : null;
}
