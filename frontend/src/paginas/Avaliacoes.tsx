import { lazy, Suspense } from "react";
import { EsqueletoAvaliacoes } from "@/avaliacoes/Esqueletos";
import { TituloPagina } from "@/layout/TituloPagina";

// Pedaço próprio no build. Se o download falhar, o erro cai no errorElement da raiz.
const ConteudoAvaliacoes = lazy(() => import("@/avaliacoes/ConteudoAvaliacoes"));

/** Avaliações. O h1 fica fora do Suspense (o foco do Layout não se perde quando o conteúdo chega). */
export function Avaliacoes() {
  return (
    <div className="flex flex-col gap-6">
      <TituloPagina>Avaliações</TituloPagina>
      <Suspense fallback={<EsqueletoAvaliacoes />}>
        <ConteudoAvaliacoes />
      </Suspense>
    </div>
  );
}
