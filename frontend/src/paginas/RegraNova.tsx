import { ArrowLeft } from "lucide-react";
import { lazy, Suspense } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { TituloPagina } from "@/layout/TituloPagina";
import { EsqueletoFormulario } from "@/regras/Esqueletos";
import { ROTAS } from "@/rotas";

// Pedaço próprio no build (o mesmo da edição). Se o download falhar, o erro cai no errorElement da raiz.
const FormularioRegra = lazy(() => import("@/regras/FormularioRegra"));

/** Nova regra. O h1 fica fora do Suspense (o foco do Layout não se perde quando o formulário chega). */
export function RegraNova() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-start gap-2">
        <Button asChild variant="link" size="sm" className="px-0">
          <Link to={ROTAS.regras}>
            <ArrowLeft aria-hidden />
            Regras
          </Link>
        </Button>
        <TituloPagina>Nova regra</TituloPagina>
      </div>
      <Suspense fallback={<EsqueletoFormulario texto="Carregando o formulário…" />}>
        <FormularioRegra regra={null} />
      </Suspense>
    </div>
  );
}
