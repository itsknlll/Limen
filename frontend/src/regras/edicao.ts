// Decisões das telas de regra que não dependem do React (testadas no Vitest; a interface
// fica para o Playwright da Fase 4).

import type { FieldPath } from "react-hook-form";
import { ErroApi } from "@/api/erros";
import type { ValoresFormulario } from "./validacao";

/**
 * "Regra não encontrada": id inválido na URL (null; a consulta fica desligada e nenhum
 * pedido sai) ou 404 da API (não existe ou é de outro usuário), decidido pelo tipo.
 * Qualquer outro erro não é "não encontrada": a tela mostra o EstadoErro.
 */
export function regraNaoEncontrada(regraId: number | null, erro: unknown): boolean {
  return regraId === null || (erro instanceof ErroApi && erro.tipo === "nao_encontrado");
}

/**
 * focusName do append: a Métrica da condição nova (o índice dela é a quantidade atual).
 * Sem isso o react-hook-form focaria o 1º campo registrado da condição, que é o Limiar.
 */
export function focoDaNovaCondicao(quantidade: number): FieldPath<ValoresFormulario> {
  return `condicoes.${quantidade}.metrica`;
}
