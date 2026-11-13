import { useEffect } from "react";

/** Título da aba: "Visão geral · Limen". A página vem primeiro: é o que distingue abas abertas. */
export function tituloDoDocumento(pagina: string): string {
  const limpo = pagina.trim();
  return limpo === "" ? "Limen" : `${limpo} · Limen`;
}

/** Atualiza o título da aba enquanto a página estiver montada. */
export function useTituloDocumento(pagina: string): void {
  useEffect(() => {
    document.title = tituloDoDocumento(pagina);
  }, [pagina]);
}
