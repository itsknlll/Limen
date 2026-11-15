import { CirclePause, CirclePlay, CircleQuestionMark, CircleX, type LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { rotuloStatus } from "@/lib/formatar";

// Só as variantes com contraste testado (contraste.test.ts): default = primary-foreground
// sobre primary; outline = foreground sobre o cartão. A cor não é o único sinal: cada
// status tem texto e ícone próprios.
const APARENCIA: Record<string, { Icone: LucideIcon; variante: "default" | "outline" }> = {
  ENABLED: { Icone: CirclePlay, variante: "default" },
  PAUSED: { Icone: CirclePause, variante: "outline" },
  REMOVED: { Icone: CircleX, variante: "outline" },
};
const DESCONHECIDO = { Icone: CircleQuestionMark, variante: "outline" } as const;

/** Status da campanha (texto de rotuloStatus; "capitalize" só muda a exibição). */
export function SeloStatus({ status }: { status: string }) {
  const { Icone, variante } = Object.hasOwn(APARENCIA, status) ? APARENCIA[status]! : DESCONHECIDO;
  return (
    <Badge variant={variante} className="capitalize">
      <Icone aria-hidden />
      {rotuloStatus(status)}
    </Badge>
  );
}
