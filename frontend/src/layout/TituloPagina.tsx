import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { useTituloDocumento } from "./titulo";

interface Props {
  children: ReactNode;
  /** Texto do título da aba, quando o h1 não é texto puro. */
  documento?: string;
  className?: string;
}

/**
 * O h1 de cada página. tabIndex={-1}: o Layout move o foco para ele quando a rota
 * muda, e o leitor de tela anuncia a página nova (sem isso, numa SPA o foco fica no
 * link clicado e nada é anunciado).
 */
export function TituloPagina({ children, documento, className }: Props) {
  useTituloDocumento(documento ?? (typeof children === "string" ? children : ""));
  return (
    <h1 tabIndex={-1} className={cn("text-2xl font-semibold tracking-tight outline-none", className)}>
      {children}
    </h1>
  );
}
