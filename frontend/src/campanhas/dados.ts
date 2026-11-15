// Funções puras das telas Campanhas e Campanha (sem fetch, sem React), testadas no Vitest.
// Política de ausente/indefinido igual à do motor (backend/app/motor/metricas.py):
// ausente ≠ zero; CTR e CPC são indefinidos (N/A) se faltar um dos dois termos ou se o
// denominador for 0. O valor mostrado é o da view (vw_metrica_diaria); aqui só se
// explica por que ele é N/A.

import type { components } from "@/api/esquema";
import { formatarDecimalCurto, formatarMoeda, formatarPercentual } from "@/lib/decimal";
import { formatarDataHora, formatarInteiro, formatarPeriodo } from "@/lib/formatar";

export type Campanha = components["schemas"]["CampanhaSaida"];
export type Metrica = components["schemas"]["MetricaSaida"];

/** Id da URL (/campanhas/:id): só inteiro positivo, sem zero à esquerda. Inválido → null (a tela não chama a API). */
export function lerIdCampanha(param: string | undefined): number | null {
  if (param === undefined || !/^[1-9]\d*$/.test(param)) return null;
  const id = Number(param);
  return Number.isSafeInteger(id) ? id : null;
}

/** A campanha do detalhe vem da lista de GET /campanhas (não há GET /campanhas/{id}). */
export function encontrarCampanha(lista: readonly Campanha[], id: number): Campanha | null {
  return lista.find((c) => c.id === id) ?? null;
}

/**
 * Orçamento diário em micros (R$ 1 = 1.000.000) → "R$ 50,00". As contas ficam com o
 * decimal.ts (BigInt): o número vira o texto "50000000E-6". null = campanha sem orçamento
 * vinculado, que é diferente de orçamento 0 (ausente ≠ zero).
 */
export function formatarOrcamento(micros: number | null): string {
  if (micros === null) return "sem orçamento";
  if (!Number.isSafeInteger(micros) || micros < 0) return "orçamento inválido";
  return formatarMoeda(`${micros}E-6`);
}

/** Data e hora da última sincronização, no fuso do navegador (ou no pedido). */
export function textoSincronizacao(sincronizadaEm: string | null, fuso?: string): string {
  return sincronizadaEm === null ? "nunca" : formatarDataHora(sincronizadaEm, fuso);
}

/** Aviso depois do POST /campanhas/sincronizar. */
export function mensagemSincronizacao(quantidade: number): string {
  if (quantidade === 0) return "Nenhuma campanha encontrada no Google Ads.";
  if (quantidade === 1) return "1 campanha sincronizada.";
  return `${formatarInteiro(quantidade)} campanhas sincronizadas.`;
}

const ORIGENS: Record<string, string> = { sintetica: "sintética", google_ads: "Google Ads" };

/** Origem do registro (CHECK ck_metrica_origem). Desconhecida volta como veio. */
export function rotuloOrigem(origem: string): string {
  return Object.hasOwn(ORIGENS, origem) ? ORIGENS[origem]! : origem;
}

/** "30 dias · 13/10 a 11/11/2026", para a legenda da tabela. Lista vazia → null. */
export function descricaoPeriodo(metricas: readonly Pick<Metrica, "data">[]): string | null {
  if (metricas.length === 0) return null;
  // Datas ISO (AAAA-MM-DD) ordenam como texto: não depende da ordem que a API mandou.
  const datas = metricas.map((m) => m.data).sort();
  const dias = metricas.length === 1 ? "1 dia" : `${formatarInteiro(metricas.length)} dias`;
  return `${dias} · ${formatarPeriodo(datas[0]!, datas[datas.length - 1]!)}`;
}

// --- Células da tabela diária ------------------------------------------------

export interface Celula {
  texto: string;
  /** Explicação do símbolo (title e leitor de tela); null quando o texto já basta. */
  descricao: string | null;
}

const SEM_DADO: Celula = { texto: "—", descricao: "sem dado" };

export function celulaInteiro(valor: number | null): Celula {
  return valor === null ? SEM_DADO : { texto: formatarInteiro(valor), descricao: null };
}

export function celulaMoeda(valor: string | null): Celula {
  return valor === null ? SEM_DADO : { texto: formatarMoeda(valor), descricao: null };
}

/** Conversões admitem fração ("1.500000" → "1,5"). */
export function celulaDecimal(valor: string | null): Celula {
  return valor === null ? SEM_DADO : { texto: formatarDecimalCurto(valor), descricao: null };
}

function indefinido(motivo: string): Celula {
  return { texto: "N/A", descricao: `indefinido: ${motivo}` };
}

/** CTR (%). Mesma ordem de verificação de calcular_ctr no motor. */
export function celulaCtr(m: Pick<Metrica, "ctr" | "impressoes" | "cliques">): Celula {
  if (m.ctr !== null) return { texto: formatarPercentual(m.ctr), descricao: null };
  if (m.impressoes === null && m.cliques === null) return indefinido("impressões e cliques ausentes");
  if (m.impressoes === null) return indefinido("impressões ausentes");
  if (m.cliques === null) return indefinido("cliques ausentes");
  if (m.impressoes === 0) return indefinido("0 impressões");
  return indefinido("valor não calculado");
}

/** CPC (R$). Mesma ordem de verificação de calcular_cpc no motor. */
export function celulaCpc(m: Pick<Metrica, "cpc" | "custo" | "cliques">): Celula {
  if (m.cpc !== null) return { texto: formatarMoeda(m.cpc), descricao: null };
  if (m.custo === null && m.cliques === null) return indefinido("custo e cliques ausentes");
  if (m.custo === null) return indefinido("custo ausente");
  if (m.cliques === null) return indefinido("cliques ausentes");
  if (m.cliques === 0) return indefinido("0 cliques");
  return indefinido("valor não calculado");
}
