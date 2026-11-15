import { ArrowLeft, SearchX } from "lucide-react";
import { lazy, Suspense } from "react";
import { Link, useLocation, useParams } from "react-router";
import { useCampanhas } from "@/api/consultas";
import { encontrarCampanha, lerIdCampanha } from "@/campanhas/dados";
import { EsqueletoCampanha } from "@/campanhas/Esqueletos";
import { Button } from "@/components/ui/button";
import { TituloPagina } from "@/layout/TituloPagina";
import { ROTAS } from "@/rotas";

// Pedaço próprio no build. Se o download falhar, o erro cai no errorElement da raiz.
const ConteudoCampanha = lazy(() => import("@/campanhas/ConteudoCampanha"));

/**
 * Detalhe da campanha (/campanhas/:id).
 * - Id inválido (lerIdCampanha → null): "não encontrada", sem montar o conteúdo, então
 *   nenhum pedido de métricas sai.
 * - O h1 fica fora do Suspense e é sempre o mesmo elemento: começa "Campanha" e passa ao
 *   nome quando a lista chega (o foco do Layout não se perde; o título da aba acompanha).
 * - Id válido, mas fora da lista do usuário: a mesma mensagem.
 */
export function Campanha() {
  const { id } = useParams();
  const campanhaId = lerIdCampanha(id);
  const campanhas = useCampanhas();
  const campanha = campanhaId !== null && campanhas.data ? encontrarCampanha(campanhas.data, campanhaId) : null;
  const naoEncontrada = campanhaId === null || (campanhas.isSuccess && campanha === null);
  const titulo = naoEncontrada ? "Campanha não encontrada" : (campanha?.nome ?? "Campanha");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-start gap-2">
        <Button asChild variant="link" size="sm" className="px-0">
          <Link to={ROTAS.campanhas}>
            <ArrowLeft aria-hidden />
            Campanhas
          </Link>
        </Button>
        <TituloPagina>{titulo}</TituloPagina>
      </div>
      {naoEncontrada ? (
        <CampanhaNaoEncontrada />
      ) : (
        <Suspense fallback={<EsqueletoCampanha />}>
          <ConteudoCampanha campanhaId={campanhaId} />
        </Suspense>
      )}
    </div>
  );
}

function CampanhaNaoEncontrada() {
  const { pathname } = useLocation();
  return (
    <div className="flex flex-col gap-4 rounded-xl border bg-card p-6 text-sm text-card-foreground">
      <p className="flex items-start gap-3">
        <SearchX aria-hidden className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
        <span>
          Nenhuma campanha sua corresponde a{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs break-all">{pathname}</code>. Ela pode não
          existir ou ser de outra conta.
        </span>
      </p>
      <Button asChild variant="outline" size="sm" className="self-start">
        <Link to={ROTAS.campanhas}>
          <ArrowLeft aria-hidden />
          Voltar para Campanhas
        </Link>
      </Button>
    </div>
  );
}
