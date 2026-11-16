// Histórico e resultado das avaliações (Fase 3, etapa 5): funções puras sobre as respostas
// de GET /avaliacoes e POST /avaliacoes (endpoints fixos). Sem React, rede ou relógio;
// testadas em historico.test.ts. Oráculo: linhas reais do banco limen.
//
// Parâmetros NULL = avaliação anterior à migração 0003: nada foi registrado. O sinal é
// `incluir_pausadas` NULL (depois da 0003 ele é sempre gravado), a mesma regra do
// textoParametros da Visão geral. Mostrar "não" ou "todas" seria falso (ausente ≠ falso).
// Limitação: campanha_id tem FK ON DELETE SET NULL; uma campanha apagada depois da 0003
// apareceria como "todas". Campanhas não são apagadas (a sincronização marca REMOVED).

import type { Campanha } from "@/campanhas/dados";
import { formatarData, formatarDataHora, formatarInteiro, formatarPeriodo } from "@/lib/formatar";
import type { Avaliacao } from "@/visao-geral/dados";

export const NAO_REGISTRADO = "não registrado";

export interface CelulasHistorico {
  data: string;
  periodo: string;
  campanha: string;
  pausadas: string;
  alertasGerados: string;
  alertasJaExistentes: string;
  /** Parâmetros anteriores à 0003: a tela mostra essas células em itálico. */
  parametrosAusentes: boolean;
}

type CampanhaDaLista = Pick<Campanha, "id" | "nome">;

// Cópia do trecho de período do textoParametros (visao-geral/dados.ts), para não alterar
// aquele arquivo nesta etapa. Limpeza opcional registrada no CLAUDE.md.
function textoPeriodo(inicio: string | null, fim: string | null): string {
  if (inicio && fim) return formatarPeriodo(inicio, fim)!;
  if (inicio) return `a partir de ${formatarData(inicio)}`;
  if (fim) return `até ${formatarData(fim)}`;
  return "período todo";
}

/**
 * Nome da campanha avaliada. `campanhas` undefined = lista ainda não carregou (ou falhou):
 * mostra o número, sem afirmar que ela está fora da lista.
 */
function textoCampanha(campanhaId: number | null, campanhas: readonly CampanhaDaLista[] | undefined): string {
  if (campanhaId === null) return "todas";
  if (campanhas === undefined) return `campanha nº ${campanhaId}`;
  const campanha = campanhas.find((c) => c.id === campanhaId);
  return campanha ? campanha.nome : `campanha nº ${campanhaId} (fora da lista)`;
}

type LinhaHistorico = Pick<
  Avaliacao,
  "iniciada_em" | "incluir_pausadas" | "campanha_id" | "inicio" | "fim" | "alertas_gerados" | "alertas_ja_existentes"
>;

/** Células de uma linha do histórico. `fuso` só nos testes; na tela, o do navegador. */
export function celulasHistorico(
  a: LinhaHistorico,
  campanhas: readonly CampanhaDaLista[] | undefined,
  fuso?: string,
): CelulasHistorico {
  const ausentes = a.incluir_pausadas === null;
  return {
    data: formatarDataHora(a.iniciada_em, fuso),
    periodo: ausentes ? NAO_REGISTRADO : textoPeriodo(a.inicio, a.fim),
    campanha: ausentes ? NAO_REGISTRADO : textoCampanha(a.campanha_id, campanhas),
    pausadas: ausentes ? NAO_REGISTRADO : a.incluir_pausadas ? "sim" : "não",
    alertasGerados: formatarInteiro(a.alertas_gerados),
    alertasJaExistentes: formatarInteiro(a.alertas_ja_existentes),
    parametrosAusentes: ausentes,
  };
}

function plural(n: number, singular: string, varios: string): string {
  return `${formatarInteiro(n)} ${n === 1 ? singular : varios}`;
}

type Resultado = Pick<
  Avaliacao,
  "id" | "alertas_gerados" | "alertas_ja_existentes" | "registros_avaliados" | "registros_rejeitados"
>;

/**
 * Frase do resultado de POST /avaliacoes. Zero alertas novos não é falha ("nenhum alerta
 * novo"); zero registros avaliados ganha uma dica, porque é o caso da campanha pausada
 * sem "Incluir campanhas pausadas" ou de um período sem métricas.
 */
export function textoResultado(s: Resultado): string {
  const novos = s.alertas_gerados === 0 ? "nenhum alerta novo" : plural(s.alertas_gerados, "alerta novo", "alertas novos");
  const existentes =
    s.alertas_ja_existentes === 0 ? "" : `, ${plural(s.alertas_ja_existentes, "já existia", "já existiam")}`;
  const registros = `${plural(s.registros_avaliados, "registro avaliado", "registros avaliados")}, ${plural(s.registros_rejeitados, "rejeitado", "rejeitados")}`;
  const dica =
    s.registros_avaliados === 0 ? " Nenhum registro foi avaliado: confira o período e se a campanha está pausada." : "";
  return `Avaliação nº ${s.id} concluída: ${novos}${existentes}. ${registros}.${dica}`;
}

export type EstadoExecucao =
  | { fase: "ocioso" }
  | { fase: "executando" }
  | { fase: "concluida"; saida: Resultado & Pick<Avaliacao, "campanha_id" | "inicio" | "fim"> }
  | { fase: "erro" };

/** Texto da região role="status", que existe sempre e fica vazia fora do pedido. */
export function textoStatus(estado: EstadoExecucao): string {
  switch (estado.fase) {
    case "ocioso":
      return "";
    case "executando":
      return "Executando a avaliação…";
    case "concluida":
      return textoResultado(estado.saida);
    case "erro":
      return "A avaliação não foi executada.";
  }
}
