// Formatação para exibição em pt-BR. Funções puras, testadas em formatar.test.ts.
//
// Duas armadilhas evitadas de propósito:
// - `new Date("2026-11-11")` é meia-noite em UTC; no Brasil (UTC-3) isso mostra 10/11.
//   Datas sem hora são formatadas partindo o texto, sem Date.
// - Decimais da API chegam como texto ("0.504") e são formatados como texto, sem
//   parseFloat (mesma política do backend: nada de float para valores e limiares).

const DATA = /^(\d{4})-(\d{2})-(\d{2})$/;
const DECIMAL = /^(-?)(\d+)(?:\.(\d+))?$/;
// Data e hora com fuso explícito (Z ou ±hh:mm): sem fuso, o navegador chutaria a hora local.
const DATA_HORA_COM_FUSO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/;

/** "2026-11-11" → "11/11/2026". Texto em outro formato volta como veio. */
export function formatarData(texto: string): string {
  const partes = DATA.exec(texto);
  if (!partes) return texto;
  const [, ano, mes, dia] = partes;
  return `${dia}/${mes}/${ano}`;
}

/** "2026-11-11" → "11/11" (eixo do gráfico). */
export function formatarDiaMes(texto: string): string {
  const partes = DATA.exec(texto);
  if (!partes) return texto;
  return `${partes[3]}/${partes[2]}`;
}

/** Período "13/10 a 11/11/2026" (mesmo ano) ou "28/12/2025 a 03/01/2026". */
export function formatarPeriodo(inicio: string | null, fim: string | null): string | null {
  if (!inicio || !fim) return null;
  if (inicio === fim) return formatarData(inicio);
  const mesmoAno = inicio.slice(0, 4) === fim.slice(0, 4) && DATA.test(inicio) && DATA.test(fim);
  return `${mesmoAno ? formatarDiaMes(inicio) : formatarData(inicio)} a ${formatarData(fim)}`;
}

/**
 * "2026-11-13T15:44:00.5+00:00" → "13/11/2026 às 12:44" (no fuso pedido; padrão: o do
 * navegador). Texto sem fuso explícito volta como veio.
 */
export function formatarDataHora(texto: string, fuso?: string): string {
  if (!DATA_HORA_COM_FUSO.test(texto)) return texto;
  const instante = new Date(texto);
  if (Number.isNaN(instante.getTime())) return texto;
  const partes = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: fuso,
  }).formatToParts(instante);
  const parte = (tipo: Intl.DateTimeFormatPartTypes) => partes.find((p) => p.type === tipo)?.value ?? "";
  return `${parte("day")}/${parte("month")}/${parte("year")} às ${parte("hour")}:${parte("minute")}`;
}

/** Agrupa os milhares de um inteiro em texto: "1234567" → "1.234.567". */
function agruparMilhares(digitos: string): string {
  return digitos.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** Decimal da API em texto: "1234.50" → "1.234,50". Texto inválido volta como veio. */
export function formatarDecimal(texto: string): string {
  const partes = DECIMAL.exec(texto);
  if (!partes) return texto;
  const [, sinal, inteiro, fracao] = partes;
  return `${sinal}${agruparMilhares(inteiro!)}${fracao === undefined ? "" : `,${fracao}`}`;
}

/**
 * Inteiro com separador de milhar: 1000 → "1.000", 10000 → "10.000".
 * Usa o mesmo agruparMilhares do formatarDecimal, e não o Intl: o agrupamento do Intl
 * depende dos dados de localização do navegador (alguns só agrupam a partir de 5
 * dígitos), e os testes rodam no Node, não no navegador. Assim o resultado é o mesmo
 * em qualquer ambiente. Valor que não é inteiro seguro volta como texto, sem formatar.
 */
export function formatarInteiro(numero: number): string {
  if (!Number.isSafeInteger(numero)) return String(numero);
  const sinal = numero < 0 ? "-" : "";
  return `${sinal}${agruparMilhares(String(Math.abs(numero)))}`;
}

/** ID de conta do Google Ads como o Google exibe: "4327030343" → "432-703-0343". */
export function formatarIdConta(id: string): string {
  const partes = /^(\d{3})(\d{3})(\d{4})$/.exec(id);
  return partes ? `${partes[1]}-${partes[2]}-${partes[3]}` : id;
}

const STATUS: Record<string, { singular: string; plural: string }> = {
  ENABLED: { singular: "ativa", plural: "ativas" },
  PAUSED: { singular: "pausada", plural: "pausadas" },
  REMOVED: { singular: "removida", plural: "removidas" },
  UNKNOWN: { singular: "desconhecida", plural: "desconhecidas" },
};

/** Status da campanha no Google Ads em português, concordando com a quantidade. */
export function rotuloStatus(status: string, quantidade = 1): string {
  if (!Object.hasOwn(STATUS, status)) return status;
  const rotulo = STATUS[status]!;
  return quantidade === 1 ? rotulo.singular : rotulo.plural;
}
