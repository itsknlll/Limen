import { lazy, Suspense } from "react";
import { TituloPagina } from "@/layout/TituloPagina";
import { EsqueletoRegras } from "@/regras/Esqueletos";

// Pedaço próprio no build. Se o download falhar, o erro cai no errorElement da raiz.
const ConteudoRegras = lazy(() => import("@/regras/ConteudoRegras"));

/** Regras. O h1 fica fora do Suspense (o foco do Layout não se perde quando o conteúdo chega). */
export function Regras() {
  return (
    <div className="flex flex-col gap-6">
      <TituloPagina>Regras</TituloPagina>
      <Suspense fallback={<EsqueletoRegras />}>
        <ConteudoRegras />
      </Suspense>
    </div>
  );
}
