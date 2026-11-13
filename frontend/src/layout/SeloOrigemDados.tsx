import { FlaskConical } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Lembra em todas as telas de onde vêm os dados: a estrutura das campanhas vem da
 * Google Ads API (conta de teste, IDs reais); as métricas são sintéticas, porque
 * contas de teste não veiculam (IN-02b). Fica visível em todas as larguras.
 */
export function SeloOrigemDados({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 w-fit items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium whitespace-nowrap text-muted-foreground",
        className,
      )}
      title="Campanhas e IDs vêm da Google Ads API (conta de teste). As métricas são geradas pelo Limen, porque contas de teste não veiculam anúncios."
    >
      <FlaskConical aria-hidden className="size-3.5 shrink-0" />
      Campanhas reais · Métricas sintéticas
    </span>
  );
}
