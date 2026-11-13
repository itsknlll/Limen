import { Construction } from "lucide-react";
import { TituloPagina } from "@/layout/TituloPagina";

/** Placeholder das telas que entram nas próximas fases do dashboard. */
export function EmConstrucao({ titulo, previsao }: { titulo: string; previsao: string }) {
  return (
    <div className="flex flex-col gap-6">
      <TituloPagina>{titulo}</TituloPagina>
      <div className="flex items-start gap-3 rounded-xl border border-dashed bg-card p-6 text-sm text-card-foreground">
        <Construction aria-hidden className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
        <div className="flex flex-col gap-1">
          <p className="font-medium">Em construção</p>
          <p className="text-muted-foreground">Esta tela entra na {previsao} do dashboard.</p>
        </div>
      </div>
    </div>
  );
}
