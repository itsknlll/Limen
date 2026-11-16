// Células da tela de Alertas: funções puras, sem React nem fetch.
//
// O que disparou vem da CÓPIA das condições gravada no alerta (app/servicos/avaliacao.py),
// e não da regra atual: a regra pode ter sido editada depois. A regra atual só decide o
// aviso "a regra mudou". A cópia não tem `ordem`; ela foi gravada na ordem da regra e é
// mostrada como veio. Valores medidos chegam como str(Decimal) (CTR com 28 casas,
// conferido no banco limen em 15/11) e são tratados só como texto, via lib/decimal.ts.

import type { components } from "@/api/esquema";
import { SEM_DADO, textoAcessivel, type Celula } from "@/campanhas/dados";
import { arredondarDecimal, normalizarDecimal } from "@/lib/decimal";
import { formatarData, formatarDecimal, formatarInteiro } from "@/lib/formatar";
import { comUnidade, formatarLimiar, rotuloMetrica, rotuloOperador, type Regra } from "@/regras/textos";
import { ROTAS } from "@/rotas";
import { LIMITE_ALERTAS, type ResultadoFiltros } from "./filtros";

export type Alerta = components["schemas"]["AlertaSaida"];

export interface CondicaoCopiada {
  metrica: string;
  operador: string;
  limiar: string;
}

/** A API tipa a cópia como dicionário solto: só vale se os três campos forem texto. */
export function lerCondicaoCopiada(bruta: Record<string, unknown>): CondicaoCopiada | null {
  const { metrica, operador, limiar } = bruta;
  if (typeof metrica !== "string" || typeof operador !== "string" || typeof limiar !== "string") return null;
  return { metrica, operador, limiar };
}

/** Casas mínimas na tela; as outras métricas (contagens, conversões) não são arredondadas. */
const CASAS: Record<string, number> = { ctr: 2, custo: 2, cpc: 2 };

function casasDe(normal: string): number {
  const ponto = normal.indexOf(".");
  return ponto === -1 ? 0 : normal.length - ponto - 1;
}

/**
 * Valor medido para a tela, com a unidade da métrica. Arredonda com pelo menos as casas do
 * limiar (o arredondamento é monotônico, então o valor nunca passa para o outro lado do
 * limiar) e acrescenta casas enquanto o arredondado parecer igual ao limiar sem ser:
 * ("ctr", "0.996", "1.000000") → "0,996%", e não "1,00%". O laço termina: com as casas do
 * próprio valor, o arredondado é o valor, que é diferente do limiar.
 * Ausente → "—" ("sem dado"; ausente ≠ zero). Ilegível volta como veio.
 */
export function formatarMedido(metrica: string, valor: string | null | undefined, limiar: string | null): Celula {
  if (valor === null || valor === undefined) return SEM_DADO;
  const normal = normalizarDecimal(valor);
  if (normal === null) return { texto: valor, descricao: null };
  if (!Object.hasOwn(CASAS, metrica)) return { texto: comUnidade(metrica, formatarDecimal(normal)), descricao: null };

  const alvo = limiar === null ? null : normalizarDecimal(limiar);
  let casas = Math.max(CASAS[metrica]!, alvo === null ? 0 : casasDe(alvo));
  let texto = arredondarDecimal(normal, casas)!;
  while (alvo !== null && normal !== alvo && normalizarDecimal(texto) === alvo) {
    casas += 1;
    texto = arredondarDecimal(normal, casas)!;
  }
  return { texto: comUnidade(metrica, formatarDecimal(texto)), descricao: null };
}

export interface Disparo {
  /** "CTR 0,57% < 1%" */
  visivel: string;
  /** "CTR 0,57%, menor que 1%" */
  acessivel: string;
}

const ILEGIVEL: Disparo = { visivel: "condição ilegível", acessivel: "condição ilegível" };

export function textoDisparo(condicao: CondicaoCopiada | null, valores: Alerta["valores_medidos"]): Disparo {
  if (condicao === null) return ILEGIVEL;
  const { metrica, operador, limiar } = condicao;
  const nome = rotuloMetrica(metrica);
  const medido = formatarMedido(metrica, Object.hasOwn(valores, metrica) ? valores[metrica] : null, limiar);
  const referencia = formatarLimiar(metrica, limiar);
  return {
    visivel: `${nome} ${medido.texto} ${operador} ${referencia}`,
    acessivel: `${nome} ${textoAcessivel(medido)}, ${rotuloOperador(operador)} ${referencia}`,
  };
}

/**
 * A regra atual tem condições diferentes da cópia do alerta? Compara métrica, operador e
 * limiar normalizado ("1.000000" = "1"), na ordem da regra. Regra fora da lista (carregando
 * ou com erro) → null: não dá para saber, e a tela não mostra aviso.
 */
export function regraMudou(copia: Alerta["condicoes"], regraAtual: Pick<Regra, "condicoes"> | undefined): boolean | null {
  if (regraAtual === undefined) return null;
  const atuais = [...regraAtual.condicoes].sort((a, b) => a.ordem - b.ordem);
  if (atuais.length !== copia.length) return true;
  return copia.some((bruta, i) => {
    const c = lerCondicaoCopiada(bruta);
    const a = atuais[i]!;
    return (
      c === null ||
      c.metrica !== a.metrica ||
      c.operador !== a.operador ||
      normalizarDecimal(c.limiar) !== normalizarDecimal(a.limiar)
    );
  });
}

export interface CelulasAlerta {
  id: number;
  dia: string;
  campanha: string;
  codigo: string;
  nome: string;
  disparos: Disparo[];
  regraMudou: boolean | null;
}

export function celulasAlerta(alerta: Alerta, regraAtual: Pick<Regra, "condicoes"> | undefined): CelulasAlerta {
  return {
    id: alerta.id,
    dia: formatarData(alerta.data),
    campanha: alerta.campanha_nome,
    codigo: alerta.regra_codigo,
    nome: alerta.regra_nome,
    disparos: alerta.condicoes.map((bruta) => textoDisparo(lerCondicaoCopiada(bruta), alerta.valores_medidos)),
    regraMudou: regraMudou(alerta.condicoes, regraAtual),
  };
}

export const AVISO_REGRA_MUDOU = "A regra mudou depois deste alerta; as condições mostradas são as da avaliação.";

/**
 * Contagem acima da tabela. GET /alertas não tem paginação: com `limite` itens, pode haver
 * mais, e o texto diz isso (a ordem da API é do dia mais recente para o mais antigo).
 */
export function textoContagem(quantidade: number, limite: number): string {
  if (quantidade >= limite) {
    return `Mostrando os ${formatarInteiro(limite)} alertas mais recentes. Use os filtros para ver os anteriores.`;
  }
  return quantidade === 1 ? "1 alerta" : `${formatarInteiro(quantidade)} alertas`;
}

export interface Vazio {
  titulo: string;
  texto: string;
  acao: { rotulo: string; para: string };
}

/** Sem filtro: ainda não há alertas (leva às Avaliações). Com filtro: nada com estes filtros (limpa a URL). */
export function estadoVazioAlertas(comFiltro: boolean): Vazio {
  if (comFiltro) {
    return {
      titulo: "Nenhum alerta com estes filtros",
      texto: "Nenhum alerta corresponde à campanha, à regra e ao período escolhidos. Mude os filtros ou limpe-os para ver todos.",
      acao: { rotulo: "Limpar filtros", para: ROTAS.alertas },
    };
  }
  return {
    titulo: "Nenhum alerta ainda",
    texto:
      "Um alerta é gravado quando uma avaliação encontra um dia que cumpre todas as condições de uma regra ativa. Execute uma avaliação para gerar alertas.",
    acao: { rotulo: "Ir para Avaliações", para: ROTAS.avaliacoes },
  };
}

/** A regra atual do alerta, pelo id (nunca pela posição). Lista ausente → undefined. */
export function regraDoAlerta<R extends { id: number }>(
  regras: readonly R[] | undefined,
  alerta: Pick<Alerta, "regra_id">,
): R | undefined {
  return regras?.find((r) => r.id === alerta.regra_id);
}

export type FaseAlertas =
  | { fase: "invalida" }
  | { fase: "aguardando" }
  | { fase: "carregando" }
  | { fase: "erro"; erro: unknown }
  | { fase: "pronta"; alertas: readonly Alerta[] };

/**
 * O que a tela mostra. Os filtros decidem antes da consulta: com URL inválida a consulta
 * fica desligada e continuaria "pending" para sempre, por isso "invalida" vem primeiro.
 */
export function faseAlertas(
  resultado: ResultadoFiltros,
  consulta: { isPending: boolean; isError: boolean; error: unknown; data: readonly Alerta[] | undefined },
): FaseAlertas {
  if (resultado.estado === "invalida") return { fase: "invalida" };
  if (resultado.estado === "aguardando") return { fase: "aguardando" };
  if (consulta.data !== undefined) return { fase: "pronta", alertas: consulta.data };
  if (consulta.isError) return { fase: "erro", erro: consulta.error };
  return { fase: "carregando" };
}

export const TEXTO_FILTROS_INVALIDOS = "Corrija os filtros acima para ver os alertas.";

/**
 * Texto do único role="status" da tela. Erro fica vazio: o EstadoErro já tem role="alert"
 * (duas regiões falariam a mesma coisa).
 */
export function textoStatusAlertas(fase: FaseAlertas, limite: number = LIMITE_ALERTAS): string {
  switch (fase.fase) {
    case "invalida":
      return TEXTO_FILTROS_INVALIDOS;
    case "aguardando":
    case "carregando":
      return "Carregando os alertas…";
    case "erro":
      return "";
    case "pronta":
      return fase.alertas.length === 0 ? "Nenhum alerta." : textoContagem(fase.alertas.length, limite);
  }
}
