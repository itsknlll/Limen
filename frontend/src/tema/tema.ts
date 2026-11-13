// Lógica pura do tema. O <script id="tema-inicial"> do index.html repete esta
// lógica (precisa rodar antes do bundle, para não piscar branco); o teste
// script-inline.test.ts executa aquele script e compara com estas funções.

export const CHAVE_TEMA = "limen:tema";
export const CONSULTA_ESCURO = "(prefers-color-scheme: dark)";

export const PREFERENCIAS = ["claro", "escuro", "sistema"] as const;
export type Preferencia = (typeof PREFERENCIAS)[number];
export type TemaResolvido = "claro" | "escuro";

/** Valor guardado → preferência. Ausente ou desconhecido vira "sistema" (sem erro). */
export function lerPreferencia(valor: string | null | undefined): Preferencia {
  return PREFERENCIAS.find((p) => p === valor) ?? "sistema";
}

export function resolverTema(preferencia: Preferencia, sistemaEscuro: boolean): TemaResolvido {
  if (preferencia === "sistema") return sistemaEscuro ? "escuro" : "claro";
  return preferencia;
}

/** O mínimo do <html> que o tema toca (interface própria para testar sem DOM). */
export interface RaizTema {
  classList: { toggle(classe: string, forcar: boolean): unknown };
  style: { colorScheme: string };
}

export function aplicarTema(raiz: RaizTema, tema: TemaResolvido): void {
  raiz.classList.toggle("dark", tema === "escuro");
  // color-scheme faz barra de rolagem e controles nativos acompanharem o tema.
  raiz.style.colorScheme = tema === "escuro" ? "dark" : "light";
}
