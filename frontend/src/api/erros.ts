// Contrato de erro da API: todo erro vem como {"detail": ..., "tipo": ...} (Fase 0).
// O frontend decide a mensagem e a ação pelo `tipo`, nunca pelo texto do `detail`:
// dois 409 pedem ações diferentes (regra duplicada × reconectar o Google).
//
// Tudo aqui é puro (sem fetch, sem React), para ser testado no Vitest.

/** Erros que só o frontend produz (não vêm do backend). */
export const TIPOS_DO_FRONTEND = ["sem_conexao", "desconhecido"] as const;

export class ErroApi extends Error {
  /** Código HTTP; null quando não houve resposta (falha de rede). */
  readonly status: number | null;
  readonly tipo: string;
  /** `detail` do backend, como veio: texto, lista de validação ou undefined. */
  readonly detail: unknown;
  /** Segundos do cabeçalho Retry-After (só a forma numérica). */
  readonly retryAfter: number | null;

  constructor(dados: {
    status: number | null;
    tipo: string;
    detail?: unknown;
    retryAfter?: number | null;
  }) {
    super(`${dados.tipo}${dados.status === null ? "" : ` (HTTP ${dados.status})`}`);
    this.name = "ErroApi";
    this.status = dados.status;
    this.tipo = dados.tipo;
    this.detail = dados.detail;
    this.retryAfter = dados.retryAfter ?? null;
  }
}

/** Lê Retry-After em segundos. A forma de data HTTP não é usada pelo backend: vira null. */
export function lerRetryAfter(valor: string | null | undefined): number | null {
  if (valor == null || !/^\d+$/.test(valor.trim())) return null;
  return Number(valor.trim());
}

function ehObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

/**
 * Converte uma resposta de erro em ErroApi.
 *
 * - Corpo no formato do backend → usa o `tipo` dele.
 * - 502 sem `tipo` → `sem_conexao`: é o que o proxy do Vite devolve (text/plain, corpo
 *   vazio) quando o backend está parado. O 502 do próprio backend sempre traz
 *   `tipo: "erro_google_ads"`, então os dois casos não se confundem.
 * - Qualquer outro corpo sem `tipo` → `desconhecido`.
 */
export function lerErro(
  status: number,
  corpo: unknown,
  cabecalhos?: { get(nome: string): string | null },
): ErroApi {
  const retryAfter = lerRetryAfter(cabecalhos?.get("Retry-After"));
  if (ehObjeto(corpo) && typeof corpo.tipo === "string" && corpo.tipo !== "") {
    return new ErroApi({ status, tipo: corpo.tipo, detail: corpo.detail, retryAfter });
  }
  const tipo = status === 502 ? "sem_conexao" : "desconhecido";
  return new ErroApi({ status, tipo, detail: corpo === "" ? undefined : corpo, retryAfter });
}

/** Falha antes de haver resposta (fetch lançou). O cancelamento não é erro: sai como veio. */
export function erroDeRede(causa: unknown): unknown {
  if (ehObjeto(causa) && causa.name === "AbortError") return causa;
  return new ErroApi({ status: null, tipo: "sem_conexao", detail: String(causa) });
}

// --- Mensagens ---------------------------------------------------------------

export type Acao = "entrar" | "reconectar_google" | "tentar_novamente";

export interface Mensagem {
  titulo: string;
  texto: string;
  acao: Acao | null;
  /** O `detail` em texto, para quem quiser o detalhe técnico (mostrado em letra menor). */
  detalhe: string | null;
}

type Montador = (erro: ErroApi) => Omit<Mensagem, "detalhe">;

/** Texto do `detail` quando ele é uma frase (o backend escreve essas em português). */
function detailEmTexto(erro: ErroApi): string | null {
  return typeof erro.detail === "string" && erro.detail.trim() !== "" ? erro.detail : null;
}

/** Campos citados num erro de validação (o `msg` do Pydantic vem em inglês; usamos só o local). */
export function camposInvalidos(detail: unknown): string[] {
  if (!Array.isArray(detail)) return [];
  const campos = detail
    .map((item) => (ehObjeto(item) && Array.isArray(item.local) ? item.local : null))
    .filter((local): local is unknown[] => local !== null)
    // O primeiro elemento é onde veio o dado ("body", "query", "path"), não o campo.
    .map((local) => local.slice(local.length > 1 ? 1 : 0).map(String).join("."))
    .filter((campo) => campo !== "");
  return [...new Set(campos)];
}

/** "em cerca de 1 hora", "em 5 minutos"... para o Retry-After. */
export function formatarEspera(segundos: number | null): string {
  if (segundos === null) return "mais tarde";
  if (segundos < 60) return "em alguns segundos";
  const minutos = Math.ceil(segundos / 60);
  if (minutos < 60) return `em ${minutos} ${minutos === 1 ? "minuto" : "minutos"}`;
  const horas = Math.ceil(minutos / 60);
  return `em cerca de ${horas} ${horas === 1 ? "hora" : "horas"}`;
}

const GENERICO: Montador = (erro) => ({
  titulo: "Erro inesperado",
  texto:
    erro.status === null
      ? "Algo deu errado. Tente de novo."
      : `O servidor respondeu com o código ${erro.status}. Tente de novo.`,
  acao: "tentar_novamente",
});

/**
 * Uma entrada por `tipo`. O teste `erros.test.ts` lê os tipos que o backend emite
 * (em todo `backend/app`) e exige que cada um tenha entrada aqui, e que toda entrada
 * aqui seja um tipo do backend ou de TIPOS_DO_FRONTEND.
 */
export const MENSAGENS: Record<string, Montador> = {
  // 400
  validacao: (erro) => {
    const campos = camposInvalidos(erro.detail);
    return {
      titulo: "Dados inválidos",
      texto:
        campos.length > 0
          ? `Confira ${campos.length === 1 ? "o campo" : "os campos"}: ${campos.join(", ")}.`
          : "Confira os dados enviados.",
      acao: null,
    };
  },
  requisicao_invalida: (erro) => ({
    titulo: "Pedido inválido",
    texto: detailEmTexto(erro) ?? "O servidor não aceitou o pedido.",
    acao: null,
  }),
  // 401
  nao_autenticado: () => ({
    titulo: "Sessão encerrada",
    texto: "Sua sessão terminou. Entre novamente para continuar.",
    acao: "entrar",
  }),
  // 404
  nao_encontrado: () => ({
    titulo: "Não encontrado",
    texto: "O item pedido não existe ou foi removido.",
    acao: null,
  }),
  // 409
  conflito: (erro) => ({
    titulo: "Conflito com dados existentes",
    texto: detailEmTexto(erro) ?? "A operação conflita com dados já gravados.",
    acao: null,
  }),
  regra_referencia: (erro) => ({
    titulo: "Regra de referência",
    texto:
      detailEmTexto(erro) ??
      "R1, R2 e R3 são as regras da tabela congelada e não podem ser criadas, alteradas nem desativadas.",
    acao: null,
  }),
  token_google_ausente: () => ({
    titulo: "Google Ads não conectado",
    texto: "Conecte sua conta Google para acessar as campanhas.",
    acao: "reconectar_google",
  }),
  token_google_revogado: () => ({
    titulo: "Acesso ao Google revogado",
    texto: "O acesso ao Google Ads foi revogado. Entre com o Google de novo para reconectar a conta.",
    acao: "reconectar_google",
  }),
  // 502
  erro_google_ads: () => ({
    titulo: "Erro no Google Ads",
    texto: "O Google Ads recusou o pedido. Se continuar, confira a configuração da conta.",
    acao: null,
  }),
  // 503
  google_autenticacao_temporaria: () => ({
    titulo: "Falha temporária no Google",
    texto: "O Google não confirmou a autenticação agora. Tente de novo em instantes.",
    acao: "tentar_novamente",
  }),
  google_ads_indisponivel: () => ({
    titulo: "Google Ads indisponível",
    texto: "A Google Ads API não respondeu depois de várias tentativas. Tente de novo em alguns minutos.",
    acao: "tentar_novamente",
  }),
  cota_excedida: (erro) => ({
    titulo: "Cota da Google Ads API excedida",
    // Sem botão de repetir: repetir agora só gastaria mais cota (IN-06).
    texto: `A cota de chamadas ao Google Ads acabou. Tente de novo ${formatarEspera(erro.retryAfter)}.`,
    acao: null,
  }),
  // Outros códigos HTTP do backend
  erro_http: GENERICO,
  // Só do frontend
  sem_conexao: () => ({
    titulo: "Servidor inacessível",
    texto: "Não foi possível falar com o servidor. Confira se o backend está rodando na porta 8080.",
    acao: "tentar_novamente",
  }),
  desconhecido: GENERICO,
};

/** Mensagem em português para qualquer erro (inclusive erros que não são da API). */
export function mensagemDoErro(erro: unknown): Mensagem {
  if (!(erro instanceof ErroApi)) {
    return { ...GENERICO(new ErroApi({ status: null, tipo: "desconhecido" })), detalhe: null };
  }
  // Object.hasOwn: um tipo "toString" ou "__proto__" não pode casar com o protótipo.
  const montar = Object.hasOwn(MENSAGENS, erro.tipo) ? MENSAGENS[erro.tipo]! : GENERICO;
  return { ...montar(erro), detalhe: detailEmTexto(erro) };
}

// --- Repetição automática (TanStack Query) ----------------------------------

/** Só o que é transitório. Mesma lógica do sincronizador (IN-05 repete; IN-06 não). */
const TRANSITORIOS = new Set(["sem_conexao", "google_ads_indisponivel", "google_autenticacao_temporaria"]);
export const MAXIMO_DE_REPETICOES = 2;

/**
 * `retry` do TanStack Query. `falhas` é quantas vezes já falhou antes desta decisão
 * (0 na primeira falha), então `falhas < 2` permite 2 repetições (3 tentativas).
 * Nunca repete 4xx (401 incluso: repetir não abre sessão) nem cota excedida.
 */
export function deveRepetir(falhas: number, erro: unknown): boolean {
  if (!(erro instanceof ErroApi)) return false;
  if (erro.status !== null && erro.status >= 400 && erro.status < 500) return false;
  return TRANSITORIOS.has(erro.tipo) && falhas < MAXIMO_DE_REPETICOES;
}
