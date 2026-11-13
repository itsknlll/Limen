import type { CSSProperties } from "react";
import { Toaster } from "sonner";
import { useTema } from "@/tema/contexto";

/**
 * Avisos (sonner) com o nosso tema. Não usa o `shadcn add sonner`: aquele componente
 * importa `next-themes`, que seria um pacote novo e um segundo controle de tema.
 * As cores vêm dos tokens de src/index.css (as mesmas variáveis que o shadcn passaria).
 */
export function Notificacoes() {
  const { temaResolvido } = useTema();
  return (
    <Toaster
      theme={temaResolvido === "escuro" ? "dark" : "light"}
      position="top-right"
      closeButton
      // Os rótulos padrão do sonner são em inglês ("Notifications", "Close toast").
      containerAriaLabel="Avisos"
      toastOptions={{ closeButtonAriaLabel: "Fechar aviso" }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as CSSProperties
      }
    />
  );
}
