import type { LucideIcon } from "lucide-react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  Icone: LucideIcon;
  titulo: string;
  texto: string;
  /** Link para a tela que resolve o vazio (ex.: Campanhas para sincronizar). */
  acao?: { rotulo: string; para: string };
  className?: string;
}

/**
 * Estado vazio: não é erro, então sem role="alert" (o leitor de tela não é
 * interrompido; o texto é lido na ordem normal da página).
 */
export function EstadoVazio({ Icone, titulo, texto, acao, className }: Props) {
  return (
    <div className={cn("flex flex-col gap-3 rounded-xl border border-dashed bg-card p-4 text-sm text-card-foreground", className)}>
      <div className="flex items-start gap-3">
        <Icone aria-hidden className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
        <div className="flex min-w-0 flex-col gap-1">
          <p className="font-semibold">{titulo}</p>
          <p className="text-muted-foreground">{texto}</p>
        </div>
      </div>
      {acao && (
        <Button asChild variant="outline" size="sm" className="self-start">
          <Link to={acao.para}>{acao.rotulo}</Link>
        </Button>
      )}
    </div>
  );
}
