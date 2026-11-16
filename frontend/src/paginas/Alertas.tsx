import { lazy, Suspense } from "react";
import { EsqueletoAlertas } from "@/alertas/Esqueletos";
import { TituloPagina } from "@/layout/TituloPagina";

// Pedaço próprio no build. Se o download falhar, o erro cai no errorElement da raiz.
const ConteudoAlertas = lazy(() => import("@/alertas/ConteudoAlertas"));

/** Alertas. O h1 fica fora do Suspense (o foco do Layout não se perde quando o conteúdo chega). */
export function Alertas() {
  return (
    <div className="flex flex-col gap-6">
      <TituloPagina>Alertas</TituloPagina>
      <Suspense fallback={<EsqueletoAlertas />}>
        <ConteudoAlertas />
      </Suspense>
    </div>
  );
}
