import { useSyncExternalStore } from "react";

// Preferência do sistema por menos movimento (WCAG 2.3.3). Com ela ativa, o gráfico
// desenha as barras sem animação. Acompanha a troca com a página aberta (evento
// "change" do matchMedia), como o ProvedorTema faz com o tema do sistema.

export const CONSULTA_MENOS_MOVIMENTO = "(prefers-reduced-motion: reduce)";

type ListaMidia = Pick<MediaQueryList, "matches" | "addEventListener" | "removeEventListener">;
export type MatchMedia = (consulta: string) => ListaMidia;

function matchMediaDoNavegador(): MatchMedia | null {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? (consulta) => window.matchMedia(consulta)
    : null;
}

/** A pessoa pediu menos movimento? Sem matchMedia (ou se ele falhar) → false. */
export function prefereMenosMovimento(matchMedia: MatchMedia | null = matchMediaDoNavegador()): boolean {
  if (!matchMedia) return false;
  try {
    return matchMedia(CONSULTA_MENOS_MOVIMENTO).matches;
  } catch {
    return false;
  }
}

/** Avisa quando a preferência muda; devolve a função que cancela a assinatura. */
export function assinarMenosMovimento(
  avisar: () => void,
  matchMedia: MatchMedia | null = matchMediaDoNavegador(),
): () => void {
  if (!matchMedia) return () => {};
  const lista = matchMedia(CONSULTA_MENOS_MOVIMENTO);
  lista.addEventListener("change", avisar);
  return () => lista.removeEventListener("change", avisar);
}

export function usePrefereMenosMovimento(): boolean {
  return useSyncExternalStore(
    (avisar) => assinarMenosMovimento(avisar),
    () => prefereMenosMovimento(),
  );
}
