import { cn } from "@/lib/utils";

/** "L" índigo + nome. Mesmo desenho do favicon (public/favicon.svg). */
export function Marca({ subtitulo = false, className }: { subtitulo?: boolean; className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <span
        aria-hidden
        className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary text-base font-bold text-primary-foreground"
      >
        L
      </span>
      <span className="flex flex-col leading-tight">
        <span className="font-semibold">Limen</span>
        {subtitulo && <span className="text-xs text-muted-foreground">Motor de regras de alertas</span>}
      </span>
    </span>
  );
}
