// Montagem do corpo de POST /avaliacoes (endpoint fixo) a partir do formulário.
// Espelha o AvaliacaoEntrada (app/api/esquemas.py). Oráculo dos testes: respostas reais
// do Pydantic, colhidas no venv (pedido.test.ts).
//
// Campo vazio é omitido (para o backend, ausente = sem filtro): nunca vai "" nem null.
// incluir_pausadas vai sempre, explícito. Datas como texto, sem new Date; a ordem é
// comparada como texto, porque "AAAA-MM-DD" ordena como data.
// Diferenças de propósito: só "AAAA-MM-DD" (o Pydantic também aceita data com hora) e só
// ids de campanhas da lista (o Pydantic aceita qualquer inteiro, como 0 e -1).

import type { components } from "@/api/esquema";
import { lerIdCampanha, type Campanha } from "@/campanhas/dados";
import { rotuloStatus } from "@/lib/formatar";
import { ehDataIso } from "@/visao-geral/dados";

export type CorpoAvaliacao = components["schemas"]["AvaliacaoEntrada"];

export interface FormularioAvaliacao {
  /** "" = todas as campanhas (valor do <select>). */
  campanhaId: string;
  /** "" ou "AAAA-MM-DD" (valor do <input type="date">). */
  inicio: string;
  fim: string;
  incluirPausadas: boolean;
}

export type CampoAvaliacao = "campanhaId" | "inicio" | "fim";

export type ResultadoPedido =
  | { ok: true; corpo: CorpoAvaliacao; aviso: string | null }
  | { ok: false; erros: Partial<Record<CampoAvaliacao, string>> };

export const MENSAGENS_PEDIDO = {
  campanha: "Escolha uma campanha da lista.",
  data: "Use uma data válida.",
  periodo: "A data final deve ser igual ou posterior à inicial.",
} as const;

export function montarPedidoAvaliacao(
  form: FormularioAvaliacao,
  campanhas: readonly Pick<Campanha, "id" | "nome" | "status">[],
): ResultadoPedido {
  const erros: Partial<Record<CampoAvaliacao, string>> = {};
  const corpo: CorpoAvaliacao = { incluir_pausadas: form.incluirPausadas };

  let campanha: Pick<Campanha, "id" | "nome" | "status"> | undefined;
  if (form.campanhaId !== "") {
    const id = lerIdCampanha(form.campanhaId);
    campanha = id === null ? undefined : campanhas.find((c) => c.id === id);
    if (campanha === undefined) erros.campanhaId = MENSAGENS_PEDIDO.campanha;
    else corpo.campanha_id = campanha.id;
  }

  for (const campo of ["inicio", "fim"] as const) {
    const valor = form[campo];
    if (valor === "") continue;
    if (ehDataIso(valor)) corpo[campo] = valor;
    else erros[campo] = MENSAGENS_PEDIDO.data;
  }
  if (corpo.inicio && corpo.fim && corpo.inicio > corpo.fim) erros.fim = MENSAGENS_PEDIDO.periodo;

  if (Object.keys(erros).length > 0) return { ok: false, erros };

  // Mesma regra do backend: sem incluir_pausadas, só campanhas ENABLED são avaliadas.
  const aviso =
    campanha !== undefined && campanha.status !== "ENABLED" && !form.incluirPausadas
      ? `A campanha ${campanha.nome} está ${rotuloStatus(campanha.status)}: sem "Incluir campanhas pausadas", nenhum registro dela será avaliado.`
      : null;
  return { ok: true, corpo, aviso };
}
