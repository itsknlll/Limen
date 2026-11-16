// Filtros da tela de Alertas: URL ⇄ formulário ⇄ consulta de GET /alertas (endpoint fixo).
//
// A URL é a única fonte dos filtros: enviar o formulário grava a URL, e a consulta e os
// erros saem dela. O link "Ver alertas" das Avaliações, o voltar do navegador e uma URL
// editada à mão passam pelo mesmo caminho. Nomes na URL: campanha, regra, inicio, fim.
//
// Mesmas regras do POST /avaliacoes (pedido.ts): campo vazio é omitido (nunca "" nem
// null); datas só "AAAA-MM-DD", comparadas como texto (validarPeriodo); ids só de itens
// da lista (o FastAPI aceitaria 0 e -1). O limite vai sempre explícito: é ele que decide
// o aviso "mostrando os 500 mais recentes" (não há paginação no backend).

import type { operations } from "@/api/esquema";
import { VALOR_TODAS } from "@/avaliacoes/formulario";
import { MENSAGENS_PEDIDO, validarPeriodo, type CorpoAvaliacao } from "@/avaliacoes/pedido";
import { lerIdCampanha } from "@/campanhas/dados";
import type { Regra } from "@/regras/textos";
import { ROTAS } from "@/rotas";
import { ehDataIso } from "@/visao-geral/dados";

export type ConsultaAlertas = NonNullable<operations["listar_alertas_get"]["parameters"]["query"]>;

export const LIMITE_ALERTAS = 500;

export interface FiltrosAlertas {
  /** "" = todas as campanhas. */
  campanhaId: string;
  /** "" = todas as regras. */
  regraId: string;
  /** "" ou "AAAA-MM-DD" (valor do <input type="date">). */
  inicio: string;
  fim: string;
}

export type CampoFiltro = keyof FiltrosAlertas;
export type ErrosFiltros = Partial<Record<CampoFiltro, string>>;

export const FILTROS_VAZIOS: FiltrosAlertas = { campanhaId: "", regraId: "", inicio: "", fim: "" };

/** Campo → parâmetro da URL, na ordem da tela (também a ordem na URL e a do foco). */
const PARAMETROS: readonly (readonly [CampoFiltro, string])[] = [
  ["campanhaId", "campanha"],
  ["regraId", "regra"],
  ["inicio", "inicio"],
  ["fim", "fim"],
];

export const MENSAGENS_FILTROS = {
  campanha: MENSAGENS_PEDIDO.campanha,
  regra: "Escolha uma regra da lista.",
} as const;

/** Valores como vieram (sem aparar); quem valida é montarConsultaAlertas. Repetido: vale o primeiro. */
export function lerFiltros(params: URLSearchParams): FiltrosAlertas {
  const filtros = { ...FILTROS_VAZIOS };
  for (const [campo, nome] of PARAMETROS) filtros[campo] = params.get(nome) ?? "";
  return filtros;
}

export function filtrosParaUrl(filtros: FiltrosAlertas): URLSearchParams {
  const params = new URLSearchParams();
  for (const [campo, nome] of PARAMETROS) if (filtros[campo] !== "") params.set(nome, filtros[campo]);
  return params;
}

export function temFiltro(filtros: FiltrosAlertas): boolean {
  return PARAMETROS.some(([campo]) => filtros[campo] !== "");
}

export function primeiroFiltroComErro(erros: ErrosFiltros): CampoFiltro | null {
  return PARAMETROS.find(([campo]) => erros[campo] !== undefined)?.[0] ?? null;
}

/**
 * Link do "Ver alertas" das Avaliações: campanha e período da execução. incluir_pausadas
 * não é filtro de alerta, e GET /alertas não filtra por avaliação: o link mostra os
 * alertas do período, inclusive os que já existiam.
 */
export function linkAlertas(corpo: Pick<CorpoAvaliacao, "campanha_id" | "inicio" | "fim">): string {
  const busca = filtrosParaUrl({
    campanhaId: corpo.campanha_id == null ? "" : String(corpo.campanha_id),
    regraId: "",
    inicio: corpo.inicio ?? "",
    fim: corpo.fim ?? "",
  }).toString();
  return busca === "" ? ROTAS.alertas : `${ROTAS.alertas}?${busca}`;
}

export type ResultadoFiltros =
  | { estado: "pronta"; consulta: ConsultaAlertas }
  | { estado: "aguardando" }
  | { estado: "invalida"; erros: ErrosFiltros };

export interface ComId {
  id: number;
}

/**
 * Lista `undefined` = ainda carregando. Só se espera por ela se o filtro dela estiver
 * preenchido: sem filtro, a consulta sai na hora. Lista que falhou chega como [] (o id não
 * pode ser conferido e o campo mostra o erro). Erro vence a espera: data inválida ou id
 * mal escrito aparecem mesmo com a lista carregando. O id da regra segue o mesmo formato
 * do da campanha (inteiro positivo sem zero à esquerda), por isso lerIdCampanha.
 */
export function montarConsultaAlertas(
  filtros: FiltrosAlertas,
  campanhas: readonly ComId[] | undefined,
  regras: readonly ComId[] | undefined,
): ResultadoFiltros {
  const erros: ErrosFiltros = {};
  const consulta: ConsultaAlertas = {};
  let aguardando = false;

  const ids = [
    ["campanhaId", campanhas, "campanha_id", MENSAGENS_FILTROS.campanha],
    ["regraId", regras, "regra_id", MENSAGENS_FILTROS.regra],
  ] as const;
  for (const [campo, lista, chave, mensagem] of ids) {
    const valor = filtros[campo];
    if (valor === "") continue;
    const id = lerIdCampanha(valor);
    if (id === null) erros[campo] = mensagem;
    else if (lista === undefined) aguardando = true;
    else if (lista.some((item) => item.id === id)) consulta[chave] = id;
    else erros[campo] = mensagem;
  }

  const { periodo, erros: errosPeriodo } = validarPeriodo(filtros.inicio, filtros.fim);
  Object.assign(erros, errosPeriodo);

  if (Object.keys(erros).length > 0) return { estado: "invalida", erros };
  if (aguardando) return { estado: "aguardando" };
  return { estado: "pronta", consulta: { ...consulta, ...periodo, limite: LIMITE_ALERTAS } };
}

/**
 * Lista para o filtro: com dados, os dados (mesmo se a releitura falhou depois); sem dados
 * e com erro, [] (o id não pode ser conferido e o campo mostra o erro); carregando,
 * undefined (montarConsultaAlertas espera, se o filtro dela estiver preenchido).
 */
export function listaParaFiltro<T>(consulta: { data: readonly T[] | undefined; isError: boolean }): readonly T[] | undefined {
  if (consulta.data !== undefined) return consulta.data;
  return consulta.isError ? [] : undefined;
}

export interface EnvioFiltros {
  busca: URLSearchParams;
  foco: CampoFiltro | null;
}

/**
 * Enviar sempre grava a URL (ela é a fonte dos filtros); o foco vai ao primeiro campo com
 * erro, calculado já no envio com as mesmas listas que a tela usa para ler a URL.
 */
export function envioDosFiltros(
  rascunho: FiltrosAlertas,
  campanhas: readonly ComId[] | undefined,
  regras: readonly ComId[] | undefined,
): EnvioFiltros {
  const resultado = montarConsultaAlertas(rascunho, campanhas, regras);
  return {
    busca: filtrosParaUrl(rascunho),
    foco: resultado.estado === "invalida" ? primeiroFiltroComErro(resultado.erros) : null,
  };
}

/** O erro da URL só aparece no campo enquanto o rascunho dele for o valor da URL. */
export function errosVisiveis(erros: ErrosFiltros, rascunho: FiltrosAlertas, filtros: FiltrosAlertas): ErrosFiltros {
  const visiveis: ErrosFiltros = {};
  for (const [campo] of PARAMETROS) {
    if (erros[campo] !== undefined && rascunho[campo] === filtros[campo]) visiveis[campo] = erros[campo];
  }
  return visiveis;
}

/** "Todas" primeiro, depois as regras na ordem da API; desativadas também (os alertas delas ficam). */
export function opcoesRegraFiltro(
  regras: readonly Pick<Regra, "id" | "codigo" | "nome" | "ativa">[],
): { valor: string; rotulo: string }[] {
  return [
    { valor: VALOR_TODAS, rotulo: "Todas as regras" },
    ...regras.map((r) => ({ valor: String(r.id), rotulo: `${r.codigo} · ${r.nome}${r.ativa ? "" : " (desativada)"}` })),
  ];
}

/**
 * Valor para o <input type="date">: ele só aceita "" ou "AAAA-MM-DD" válida (outro valor
 * gera aviso no console e o campo fica vazio do mesmo jeito). O texto da URL continua no
 * rascunho: o erro do campo segue aparecendo até a pessoa escolher uma data ou limpar.
 */
export function valorDoCampoData(texto: string): string {
  return ehDataIso(texto) ? texto : "";
}
