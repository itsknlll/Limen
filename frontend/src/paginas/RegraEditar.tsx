import { ArrowLeft, Lock, SearchX } from "lucide-react";
import { lazy, Suspense } from "react";
import { Link, useLocation, useParams } from "react-router";
import { useRegra } from "@/api/consultas";
import { lerIdCampanha } from "@/campanhas/dados";
import { EstadoErro } from "@/componentes/EstadoErro";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TituloPagina } from "@/layout/TituloPagina";
import { regraNaoEncontrada } from "@/regras/edicao";
import { EsqueletoFormulario } from "@/regras/Esqueletos";
import { SeloRegra } from "@/regras/SeloRegra";
import { textoCondicoes, type Regra } from "@/regras/textos";
import { ROTAS } from "@/rotas";

// Pedaço próprio no build (o mesmo da regra nova). Se o download falhar, o erro cai no errorElement da raiz.
const FormularioRegra = lazy(() => import("@/regras/FormularioRegra"));

/**
 * Edição de regra (/regras/:id/editar).
 * - Id inválido (lerIdCampanha, reaproveitado da Fase 2 sem alteração → null): "Regra não
 *   encontrada" sem pedido (useRegra(null) fica desligada).
 * - 404 da API (não existe ou é de outro usuário; decidido pelo tipo nao_encontrado): a
 *   mesma mensagem. Outro erro: EstadoErro com "tentar de novo".
 * - R1 a R3: só leitura, sem formulário (a API recusaria o PUT com 409).
 * - O h1 fica fora do Suspense e é sempre o mesmo elemento: começa "Editar regra" e passa
 *   a "Editar R4" quando a regra chega (o foco do Layout não se perde).
 */
export function RegraEditar() {
  const { id } = useParams();
  const regraId = lerIdCampanha(id);
  const consulta = useRegra(regraId);
  const naoEncontrada = regraNaoEncontrada(regraId, consulta.error);
  const regra = consulta.data;
  const titulo = naoEncontrada
    ? "Regra não encontrada"
    : regra === undefined
      ? "Editar regra"
      : regra.referencia
        ? `Regra ${regra.codigo}`
        : `Editar ${regra.codigo}`;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-start gap-2">
        <Button asChild variant="link" size="sm" className="px-0">
          <Link to={ROTAS.regras}>
            <ArrowLeft aria-hidden />
            Regras
          </Link>
        </Button>
        <TituloPagina>{titulo}</TituloPagina>
      </div>
      {naoEncontrada ? (
        <RegraNaoEncontrada />
      ) : consulta.isPending ? (
        <EsqueletoFormulario texto="Carregando a regra…" />
      ) : consulta.isError ? (
        <EstadoErro erro={consulta.error} aoTentarNovamente={() => void consulta.refetch()} tentando={consulta.isFetching} />
      ) : consulta.data.referencia ? (
        <RegraReferencia regra={consulta.data} />
      ) : (
        <Suspense fallback={<EsqueletoFormulario texto="Carregando o formulário…" />}>
          <FormularioRegra regra={consulta.data} />
        </Suspense>
      )}
    </div>
  );
}

function RegraNaoEncontrada() {
  const { pathname } = useLocation();
  return (
    <div className="flex flex-col gap-4 rounded-xl border bg-card p-6 text-sm text-card-foreground">
      <p className="flex items-start gap-3">
        <SearchX aria-hidden className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
        <span>
          Nenhuma regra sua corresponde a{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs break-all">{pathname}</code>. Ela pode não
          existir ou ser de outra conta.
        </span>
      </p>
      <Button asChild variant="outline" size="sm" className="self-start">
        <Link to={ROTAS.regras}>
          <ArrowLeft aria-hidden />
          Voltar para Regras
        </Link>
      </Button>
    </div>
  );
}

/** R1 a R3: mostra a regra e diz por que não há formulário. */
function RegraReferencia({ regra }: { regra: Regra }) {
  const condicoes = textoCondicoes(regra);
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="flex flex-wrap items-center gap-2">
            <SeloRegra codigo={regra.codigo} />
            {regra.nome}
          </h2>
        </CardTitle>
        <CardDescription className="flex items-start gap-2">
          <Lock aria-hidden className="mt-0.5 size-4 shrink-0" />
          R1, R2 e R3 são as regras de referência da tabela congelada: a API recusa editar ou desativar estas regras.
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm">
        <span aria-hidden="true">{condicoes.visivel}</span>
        <span className="sr-only">{condicoes.acessivel}</span>
      </CardContent>
    </Card>
  );
}
