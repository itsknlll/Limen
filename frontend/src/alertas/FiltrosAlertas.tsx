import { Filter, X } from "lucide-react";
import { useId, useRef, useState } from "react";
import { Link } from "react-router";
import { useCampanhas, useRegras } from "@/api/consultas";
import { campanhaDoSelect, opcoesCampanha, valorDoSelect } from "@/avaliacoes/formulario";
import { EstadoErro } from "@/componentes/EstadoErro";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ROTAS } from "@/rotas";
import {
  type CampoFiltro,
  envioDosFiltros,
  type ErrosFiltros,
  errosVisiveis,
  type FiltrosAlertas as Filtros,
  filtrosParaUrl,
  listaParaFiltro,
  opcoesRegraFiltro,
  temFiltro,
  valorDoCampoData,
} from "./filtros";

interface Props {
  /** Filtros lidos da URL. */
  filtros: Filtros;
  /** Erros dos filtros da URL (de montarConsultaAlertas). */
  erros: ErrosFiltros;
  aoEnviar: (busca: URLSearchParams) => void;
}

/**
 * Formulário dos filtros. O rascunho é local; enviar grava a URL (envioDosFiltros) e foca
 * o primeiro campo com erro. Quando a URL muda por fora (voltar do navegador, "Limpar
 * filtros", link das Avaliações), o rascunho é trocado pelo da URL durante o render (padrão
 * do React para estado derivado de prop), sem remontar o formulário: o foco não se perde.
 * Sem a lista (carregando ou com erro), o select só tem "Todas".
 * Filtrar só lê: sem aria-disabled nem bloqueio de pedido repetido.
 */
export function FiltrosAlertas({ filtros, erros, aoEnviar }: Props) {
  const id = useId();
  const campanhas = useCampanhas();
  const regras = useRegras();

  const busca = filtrosParaUrl(filtros).toString();
  const [origem, setOrigem] = useState(busca);
  const [rascunho, setRascunho] = useState<Filtros>(filtros);
  if (origem !== busca) {
    setOrigem(busca);
    setRascunho(filtros);
  }

  const refCampanha = useRef<HTMLButtonElement>(null);
  const refRegra = useRef<HTMLButtonElement>(null);
  const refInicio = useRef<HTMLInputElement>(null);
  const refFim = useRef<HTMLInputElement>(null);
  const focar = (campo: CampoFiltro) =>
    ({ campanhaId: refCampanha, regraId: refRegra, inicio: refInicio, fim: refFim })[campo].current?.focus();

  const alterar = (campo: CampoFiltro, valor: string) => setRascunho((atual) => ({ ...atual, [campo]: valor }));

  const aoSubmeter = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    const envio = envioDosFiltros(rascunho, listaParaFiltro(campanhas), listaParaFiltro(regras));
    aoEnviar(envio.busca);
    if (envio.foco !== null) focar(envio.foco);
  };

  const visiveis = errosVisiveis(erros, rascunho, filtros);
  const ids = { campanha: `${id}-campanha`, regra: `${id}-regra`, inicio: `${id}-inicio`, fim: `${id}-fim` };

  return (
    <form noValidate onSubmit={aoSubmeter} className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={ids.campanha}>Campanha</Label>
          <Select
            name="campanhaId"
            value={valorDoSelect(rascunho.campanhaId)}
            onValueChange={(v) => alterar("campanhaId", campanhaDoSelect(v))}
          >
            <SelectTrigger
              id={ids.campanha}
              ref={refCampanha}
              aria-invalid={visiveis.campanhaId ? true : undefined}
              aria-describedby={descritor(ids.campanha, visiveis.campanhaId)}
              className="w-full"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {opcoesCampanha(campanhas.data ?? []).map((o) => (
                <SelectItem key={o.valor} value={o.valor}>
                  {o.rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Erro id={ids.campanha} texto={visiveis.campanhaId} />
          {campanhas.isPending && <p className="text-sm text-muted-foreground">Carregando as campanhas…</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor={ids.regra}>Regra</Label>
          {/* valorDoSelect/campanhaDoSelect só convertem "todas" ↔ "" (servem para qualquer select com "Todas"). */}
          <Select
            name="regraId"
            value={valorDoSelect(rascunho.regraId)}
            onValueChange={(v) => alterar("regraId", campanhaDoSelect(v))}
          >
            <SelectTrigger
              id={ids.regra}
              ref={refRegra}
              aria-invalid={visiveis.regraId ? true : undefined}
              aria-describedby={descritor(ids.regra, visiveis.regraId)}
              className="w-full"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {opcoesRegraFiltro(regras.data ?? []).map((o) => (
                <SelectItem key={o.valor} value={o.valor}>
                  {o.rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Erro id={ids.regra} texto={visiveis.regraId} />
          {regras.isPending && <p className="text-sm text-muted-foreground">Carregando as regras…</p>}
        </div>

        <CampoData
          id={ids.inicio}
          rotulo="Data inicial"
          ref={refInicio}
          valor={valorDoCampoData(rascunho.inicio)}
          erro={visiveis.inicio}
          aoMudar={(v) => alterar("inicio", v)}
        />
        <CampoData
          id={ids.fim}
          rotulo="Data final"
          ref={refFim}
          valor={valorDoCampoData(rascunho.fim)}
          erro={visiveis.fim}
          aoMudar={(v) => alterar("fim", v)}
        />
      </div>

      {campanhas.isError && (
        <EstadoErro
          erro={campanhas.error}
          aoTentarNovamente={() => void campanhas.refetch()}
          tentando={campanhas.isFetching}
          className="max-w-md"
        />
      )}
      {regras.isError && (
        <EstadoErro
          erro={regras.error}
          aoTentarNovamente={() => void regras.refetch()}
          tentando={regras.isFetching}
          className="max-w-md"
        />
      )}

      <div className="flex flex-wrap gap-2">
        <Button type="submit">
          <Filter aria-hidden />
          Filtrar
        </Button>
        {temFiltro(filtros) && (
          <Button asChild variant="outline">
            <Link to={ROTAS.alertas}>
              <X aria-hidden />
              Limpar filtros
            </Link>
          </Button>
        )}
      </div>
    </form>
  );
}

// Limpeza opcional (registrada no CLAUDE.md): CampoData, descritor e Erro repetem os do
// FormularioAvaliacao, onde são privados. Extrair para src/componentes/ e usar nos dois.

interface PropsData {
  id: string;
  rotulo: string;
  ref: React.Ref<HTMLInputElement>;
  valor: string;
  erro?: string;
  aoMudar: (valor: string) => void;
}

/** <input type="date">: o valor é "" ou "AAAA-MM-DD", como o filtros.ts espera. */
function CampoData({ id, rotulo, ref, valor, erro, aoMudar }: PropsData) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{rotulo}</Label>
      <Input
        id={id}
        ref={ref}
        type="date"
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descritor(id, erro)}
      />
      <Erro id={id} texto={erro} />
    </div>
  );
}

function descritor(id: string, erro: string | undefined) {
  return erro ? `${id}-erro` : undefined;
}

function Erro({ id, texto }: { id: string; texto?: string }) {
  if (!texto) return null;
  return (
    <p id={`${id}-erro`} className="text-sm text-destructive">
      {texto}
    </p>
  );
}
