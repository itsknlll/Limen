import { lazy, Suspense } from "react";
import { TituloPagina } from "@/layout/TituloPagina";
import { EsqueletoVisaoGeral } from "@/visao-geral/Esqueletos";

// Pedaço próprio no build (com o Recharts). Se o download falhar, o erro é lançado na
// renderização e cai no errorElement da raiz (ErroDeRota, com "Recarregar").
const ConteudoVisaoGeral = lazy(() => import("@/visao-geral/ConteudoVisaoGeral"));

/**
 * Visão geral. O h1 fica fora do Suspense: o Layout foca o h1 quando a rota muda, e um
 * h1 dentro do fallback seria desmontado quando o conteúdo chegasse, levando o foco
 * para o <body>. O fallback tem um único status para a tela inteira.
 */
export function VisaoGeral() {
  return (
    <div className="flex flex-col gap-6">
      <TituloPagina>Visão geral</TituloPagina>
      <Suspense fallback={<EsqueletoVisaoGeral />}>
        <ConteudoVisaoGeral />
      </Suspense>
    </div>
  );
}
