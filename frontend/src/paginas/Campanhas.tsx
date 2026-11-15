import { lazy, Suspense } from "react";
import { EsqueletoCampanhas } from "@/campanhas/Esqueletos";
import { TituloPagina } from "@/layout/TituloPagina";

// Pedaço próprio no build. Se o download falhar, o erro cai no errorElement da raiz.
const ConteudoCampanhas = lazy(() => import("@/campanhas/ConteudoCampanhas"));

/** Campanhas. O h1 fica fora do Suspense (o foco do Layout não se perde quando o conteúdo chega). */
export function Campanhas() {
  return (
    <div className="flex flex-col gap-6">
      <TituloPagina>Campanhas</TituloPagina>
      <Suspense fallback={<EsqueletoCampanhas />}>
        <ConteudoCampanhas />
      </Suspense>
    </div>
  );
}
