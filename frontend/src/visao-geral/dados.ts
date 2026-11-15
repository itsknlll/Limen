// Dados da Visão geral: funções puras sobre as respostas de GET /resumo e GET /avaliacoes.
// Sem React, rede ou relógio; testadas em dados.test.ts.
//
// Datas puras ("2026-10-13") nunca passam por `new Date`: meia-noite UTC vira o dia
// anterior no Brasil. O calendário é percorrido partindo o texto.

import type { components } from "@/api/esquema";
import { formatarData, formatarDecimal, formatarInteiro, formatarPeriodo, rotuloStatus } from "@/lib/formatar";

export type Resumo = components["schemas"]["ResumoSaida"];
export type AlertasDia = components["schemas"]["ResumoAlertasDia"];
export type AlertasRegra = components["schemas"]["ResumoAlertasRegra"];
export type Avaliacao = components["schemas"]["AvaliacaoSaida"];

// --- Calendário -----------------------------------------------------------------

const DATA = /^(\d{4})-(\d{2})-(\d{2})$/;

function ehBissexto(ano: number): boolean {
  return (ano % 4 === 0 && ano % 100 !== 0) || ano % 400 === 0;
}

function diasNoMes(ano: number, mes: number): number {
  if (mes === 2) return ehBissexto(ano) ? 29 : 28;
  return [4, 6, 9, 11].includes(mes) ? 30 : 31;
}

function lerData(texto: string): [number, number, number] {
  const partes = DATA.exec(texto);
  if (!partes) throw new Error(`data fora do formato AAAA-MM-DD: ${texto}`);
  const [ano, mes, dia] = [Number(partes[1]), Number(partes[2]), Number(partes[3])];
  if (mes < 1 || mes > 12 || dia < 1 || dia > diasNoMes(ano, mes)) throw new Error(`data inexistente: ${texto}`);
  return [ano, mes, dia];
}

/**
 * "AAAA-MM-DD" de um dia que existe, com ano ≥ 1 (como o date do Python). Para o pedido
 * de avaliação, que recebe o texto do <input type="date">. Não lança erro.
 */
export function ehDataIso(texto: string): boolean {
  try {
    return lerData(texto)[0] >= 1;
  } catch {
    return false;
  }
}

const doisDigitos = (n: number) => String(n).padStart(2, "0");

/**
 * Todos os dias de `inicio` a `fim`, inclusive, como "AAAA-MM-DD".
 * `inicio > fim` → []. Data inválida lança erro: viria de fora do contrato da API, e
 * devolver [] mostraria um gráfico vazio sem aviso.
 */
export function diasEntre(inicio: string, fim: string): string[] {
  let [ano, mes, dia] = lerData(inicio);
  lerData(fim);
  const dias: string[] = [];
  for (let atual = inicio; atual <= fim; ) {
    dias.push(atual);
    dia += 1;
    if (dia > diasNoMes(ano, mes)) {
      dia = 1;
      mes += 1;
      if (mes > 12) {
        mes = 1;
        ano += 1;
      }
    }
    atual = `${ano}-${doisDigitos(mes)}-${doisDigitos(dia)}`;
  }
  return dias;
}

// --- Série do gráfico -----------------------------------------------------------

export interface PontoSerie {
  data: string;
  /** Alertas do dia, por código de regra; toda regra da série aparece, com 0 se não houver. */
  valores: Record<string, number>;
  total: number;
}

/**
 * Códigos na ordem do gráfico: os de `por_regra` (o backend ordena por código) e, por
 * defesa, qualquer código que só apareça em `por_dia`, no fim e em ordem alfabética.
 */
export function codigosDaSerie(porRegra: AlertasRegra[], porDia: AlertasDia[]): string[] {
  const codigos = porRegra.map((r) => r.codigo);
  const extras = new Set<string>();
  for (const dia of porDia) for (const codigo of Object.keys(dia.por_regra)) if (!codigos.includes(codigo)) extras.add(codigo);
  return [...codigos, ...[...extras].sort()];
}

/**
 * Um ponto por dia de `inicio` a `fim` (o período das métricas), preenchendo com 0 os
 * dias sem alerta: o backend só manda os dias com alerta. Um dia de `por_dia` fora do
 * período estende o eixo em vez de sumir. Sem período e sem alertas → [].
 */
export function serieAlertasPorDia(
  porDia: AlertasDia[],
  inicio: string | null,
  fim: string | null,
  codigos: string[],
): PontoSerie[] {
  const datas = porDia.map((d) => d.data).sort();
  const primeiro = [inicio, datas[0]].filter((d): d is string => !!d).sort()[0];
  const ultimo = [fim, datas.at(-1)].filter((d): d is string => !!d).sort().at(-1);
  if (!primeiro || !ultimo) return [];

  const doDia = new Map(porDia.map((d) => [d.data, d.por_regra]));
  return diasEntre(primeiro, ultimo).map((data) => {
    const doBackend = doDia.get(data) ?? {};
    const valores = Object.fromEntries(codigos.map((c) => [c, doBackend[c] ?? 0]));
    const total = Object.values(valores).reduce((soma, n) => soma + n, 0);
    return { data, valores, total };
  });
}

/**
 * Código do segmento no topo da pilha do dia: o último, na ordem da pilha, com valor
 * > 0. Só ele ganha o canto arredondado (4 px) da ponta da barra. Dia vazio → null.
 */
export function codigoNoTopo(valores: Record<string, number>, codigos: string[]): string | null {
  for (let i = codigos.length - 1; i >= 0; i--) if ((valores[codigos[i]!] ?? 0) > 0) return codigos[i]!;
  return null;
}

/** Texto do gráfico para leitor de tela (o gráfico em si fica aria-hidden). */
export function descricaoGrafico(resumo: Resumo): string {
  const { alertas, metricas } = resumo;
  const periodo = formatarPeriodo(metricas.inicio, metricas.fim);
  const trecho = periodo ? (metricas.inicio === metricas.fim ? ` em ${periodo}` : ` de ${periodo}`) : "";
  if (alertas.total === 0) return `Nenhum alerta${trecho}.`;
  const dias = alertas.por_dia.filter((d) => Object.values(d.por_regra).some((n) => n > 0)).length;
  const porRegra = alertas.por_regra.map((r) => `${r.codigo} ${formatarInteiro(r.total)}`).join(", ");
  return (
    `${plural(alertas.total, "alerta", "alertas")} em ${plural(dias, "dia", "dias")}${trecho}: ${porRegra}.`
  );
}

// --- Textos dos KPIs ------------------------------------------------------------

function plural(n: number, singular: string, varios: string): string {
  return `${formatarInteiro(n)} ${n === 1 ? singular : varios}`;
}

const ORDEM_STATUS = ["ENABLED", "PAUSED", "REMOVED", "UNKNOWN"];

/** "2 ativas · 1 pausada" (status com 0 não aparecem). */
export function textoCampanhas(porStatus: Record<string, number>): string {
  const status = [
    ...ORDEM_STATUS.filter((s) => Object.hasOwn(porStatus, s)),
    ...Object.keys(porStatus).filter((s) => !ORDEM_STATUS.includes(s)).sort(),
  ];
  const partes = status
    .filter((s) => (porStatus[s] ?? 0) > 0)
    .map((s) => `${formatarInteiro(porStatus[s]!)} ${rotuloStatus(s, porStatus[s])}`);
  return partes.length ? partes.join(" · ") : "nenhuma campanha";
}

/** "3 ativas de 3". */
export function textoRegras({ total, ativas }: Resumo["regras"]): string {
  if (total === 0) return "nenhuma regra";
  return `${plural(ativas, "ativa", "ativas")} de ${formatarInteiro(total)}`;
}

const ORIGEM: Record<string, [string, string]> = {
  sintetica: ["sintético", "sintéticos"],
  google_ads: ["do Google Ads", "do Google Ads"],
};

/** "13/10 a 11/11/2026 · 90 sintéticos" (origens com 0 não aparecem). */
export function textoMetricas(metricas: Resumo["metricas"]): string {
  if (metricas.registros === 0) return "nenhum registro";
  const origens = Object.entries(metricas.por_origem)
    .filter(([, n]) => n > 0)
    .map(([origem, n]) => {
      const rotulo = Object.hasOwn(ORIGEM, origem) ? ORIGEM[origem]! : [origem, origem];
      return `${formatarInteiro(n)} ${n === 1 ? rotulo[0] : rotulo[1]}`;
    });
  const periodo = formatarPeriodo(metricas.inicio, metricas.fim);
  return [periodo, ...origens].filter(Boolean).join(" · ");
}

/**
 * Origem do total de alertas: "gerados em 2 avaliações". Sem isso, o 27 (soma de duas
 * execuções) seria confundido com os 18 da primeira. Usa `alertas.avaliacoes`, contado
 * no banco (avaliações distintas que geraram os alertas do período).
 */
export function textoAlertas(alertas: Resumo["alertas"]): string {
  if (alertas.avaliacoes === 0) return "nenhuma avaliação gerou alertas";
  return `gerados em ${plural(alertas.avaliacoes, "avaliação", "avaliações")}`;
}

// --- Últimas avaliações ---------------------------------------------------------

/**
 * Parâmetros da execução. `incluir_pausadas` NULL = avaliação anterior à migração 0003:
 * nada foi registrado, e mostrar "só ativas" seria falso (ausente ≠ falso). Depois da
 * 0003 ele é sempre gravado; aí `campanha_id` NULL significa todas as campanhas.
 */
export function textoParametros(a: Pick<Avaliacao, "incluir_pausadas" | "campanha_id" | "inicio" | "fim">): string {
  if (a.incluir_pausadas === null) return "não registrado";
  const campanhas = a.campanha_id === null ? "todas as campanhas" : `campanha nº ${a.campanha_id}`;
  let periodo: string;
  if (a.inicio && a.fim) periodo = formatarPeriodo(a.inicio, a.fim)!;
  else if (a.inicio) periodo = `a partir de ${formatarData(a.inicio)}`;
  else if (a.fim) periodo = `até ${formatarData(a.fim)}`;
  else periodo = "período todo";
  return [a.incluir_pausadas ? "com pausadas" : "só ativas", campanhas, periodo].join(" · ");
}

/** "0.870" → "0,870 ms"; null → "—" (duração não registrada). */
export function textoDuracao(ms: string | null): string {
  return ms === null ? "—" : `${formatarDecimal(ms)} ms`;
}

// --- Estado vazio ---------------------------------------------------------------

export type EstadoVazio = "sem_campanhas" | "sem_metricas" | "sem_avaliacoes" | "sem_alertas";

/**
 * Qual mensagem de vazio mostrar, na ordem em que o fluxo acontece (sincronizar →
 * métricas → avaliar). `sem_alertas` não é falha: a avaliação rodou e nada disparou.
 * null = há alertas para mostrar.
 */
export function estadoVazio(resumo: Resumo): EstadoVazio | null {
  if (resumo.campanhas.total === 0) return "sem_campanhas";
  if (resumo.metricas.registros === 0) return "sem_metricas";
  if (resumo.ultima_avaliacao === null) return "sem_avaliacoes";
  if (resumo.alertas.total === 0) return "sem_alertas";
  return null;
}
