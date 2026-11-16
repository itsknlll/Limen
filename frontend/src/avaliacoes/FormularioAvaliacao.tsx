import { Bell, Play } from "lucide-react";
import { useId, useRef, useState } from "react";
import { Link } from "react-router";
import { useCampanhas, useExecutarAvaliacao } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { ROTAS } from "@/rotas";
import {
  avisoAtual,
  campanhaDoSelect,
  decidirEnvio,
  depoisDoErro,
  type ErrosAvaliacao,
  FORMULARIO_INICIAL,
  opcoesCampanha,
  semErroNoCampo,
  valorDoSelect,
} from "./formulario";
import { type EstadoExecucao, textoResultado, textoStatus } from "./historico";
import type { CampoAvaliacao, FormularioAvaliacao as Formulario } from "./pedido";

/**
 * Formulário de POST /avaliacoes (endpoint fixo). Toda decisão vem de formulario.ts
 * (decidirEnvio, depoisDoErro) e de historico.ts (textoStatus, textoResultado); aqui só
 * se liga o estado à tela.
 * - Um pedido por vez: aria-disabled no botão (disabled tiraria o foco) e decidirEnvio
 *   ignora o envio enquanto há pedido. O botão fica em "Executando…" até o histórico e o
 *   resumo serem relidos (o onSuccess de opcoesExecutarAvaliacao devolve a promessa).
 * - role="status" sempre presente, com o textoStatus.
 * - Erro de campo (navegador ou servidor): no campo (aria-invalid + aria-describedby),
 *   com foco no primeiro da tela. O resto (período invertido no servidor, Google, rede)
 *   vai para o EstadoErro, acima do botão.
 * - Sem a lista de campanhas (carregando ou com erro), o select só tem "Todas".
 */
export function FormularioAvaliacao() {
  const id = useId();
  const campanhas = useCampanhas();
  const executar = useExecutarAvaliacao();
  const pendente = executar.isPending;
  const lista = campanhas.data ?? [];

  const [form, setForm] = useState<Formulario>(FORMULARIO_INICIAL);
  const [erros, setErros] = useState<ErrosAvaliacao>({});
  const [estado, setEstado] = useState<EstadoExecucao>({ fase: "ocioso" });
  const [erroGeral, setErroGeral] = useState<{ erro: unknown } | null>(null);

  const refCampanha = useRef<HTMLButtonElement>(null);
  const refInicio = useRef<HTMLInputElement>(null);
  const refFim = useRef<HTMLInputElement>(null);
  const focar = (campo: CampoAvaliacao) =>
    ({ campanhaId: refCampanha, inicio: refInicio, fim: refFim })[campo].current?.focus();

  const alterar = (campo: CampoAvaliacao, valor: string) => {
    setForm((atual) => ({ ...atual, [campo]: valor }));
    setErros((atuais) => semErroNoCampo(atuais, campo));
  };

  const aoEnviar = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    const decisao = decidirEnvio(form, lista, pendente);
    if (decisao.acao === "ignorar") return;
    setErroGeral(null);
    if (decisao.acao === "corrigir") {
      setErros(decisao.erros);
      setEstado({ fase: "erro" });
      focar(decisao.foco);
      return;
    }
    setErros({});
    setEstado({ fase: "executando" });
    executar.mutate(decisao.corpo, {
      onSuccess: (saida) => setEstado({ fase: "concluida", saida }),
      onError: (erro) => {
        const resultado = depoisDoErro(erro);
        setErros(resultado.erros);
        if (resultado.restante) setErroGeral({ erro });
        setEstado({ fase: "erro" });
        if (resultado.foco !== null) focar(resultado.foco);
      },
    });
  };

  const aviso = avisoAtual(form, lista);
  const idCampanha = `${id}-campanha`;
  const idInicio = `${id}-inicio`;
  const idFim = `${id}-fim`;
  const idPausadas = `${id}-pausadas`;
  const idAviso = `${id}-aviso`;

  return (
    <form noValidate onSubmit={aoEnviar} className="flex flex-col gap-4">
      <span role="status" className="sr-only">
        {textoStatus(estado)}
      </span>

      <div className="flex max-w-md flex-col gap-1.5">
        <Label htmlFor={idCampanha}>Campanha</Label>
        <Select
          name="campanhaId"
          value={valorDoSelect(form.campanhaId)}
          onValueChange={(v) => alterar("campanhaId", campanhaDoSelect(v))}
        >
          <SelectTrigger
            id={idCampanha}
            ref={refCampanha}
            aria-invalid={erros.campanhaId ? true : undefined}
            aria-describedby={descritores(idCampanha, erros.campanhaId, aviso !== null && idAviso)}
            className="w-full"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {opcoesCampanha(lista).map((o) => (
              <SelectItem key={o.valor} value={o.valor}>
                {o.rotulo}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Erro id={idCampanha} texto={erros.campanhaId} />
        {campanhas.isPending && <p className="text-sm text-muted-foreground">Carregando as campanhas…</p>}
      </div>
      {campanhas.isError && (
        <EstadoErro
          erro={campanhas.error}
          aoTentarNovamente={() => void campanhas.refetch()}
          tentando={campanhas.isFetching}
          className="max-w-md"
        />
      )}

      <div className="grid max-w-md gap-4 sm:grid-cols-2">
        <CampoData
          id={idInicio}
          rotulo="Data inicial"
          ref={refInicio}
          valor={form.inicio}
          erro={erros.inicio}
          aoMudar={(v) => alterar("inicio", v)}
        />
        <CampoData id={idFim} rotulo="Data final" ref={refFim} valor={form.fim} erro={erros.fim} aoMudar={(v) => alterar("fim", v)} />
      </div>
      <p className="-mt-2 text-sm text-muted-foreground">Sem datas, o período todo é avaliado.</p>

      <div className="flex items-center gap-2">
        <Checkbox
          id={idPausadas}
          name="incluirPausadas"
          checked={form.incluirPausadas}
          onCheckedChange={(marcado) => setForm((atual) => ({ ...atual, incluirPausadas: marcado === true }))}
          aria-describedby={aviso !== null ? idAviso : undefined}
        />
        <Label htmlFor={idPausadas}>Incluir campanhas pausadas</Label>
      </div>
      {aviso !== null && (
        <p id={idAviso} className="max-w-xl text-sm text-muted-foreground">
          {aviso}
        </p>
      )}

      {erroGeral && <EstadoErro erro={erroGeral.erro} />}

      <Button type="submit" aria-disabled={pendente} className="self-start aria-disabled:cursor-wait aria-disabled:opacity-70">
        <Play aria-hidden className={cn(pendente && "animate-pulse")} />
        {pendente ? "Executando…" : "Executar avaliação"}
      </Button>

      {estado.fase === "concluida" && (
        <div className="flex max-w-xl flex-col gap-3 rounded-xl border bg-card p-4 text-sm">
          <p>{textoResultado(estado.saida)}</p>
          <Button asChild variant="outline" size="sm" className="self-start">
            <Link to={ROTAS.alertas}>
              <Bell aria-hidden />
              Ver alertas
            </Link>
          </Button>
        </div>
      )}
    </form>
  );
}

interface PropsData {
  id: string;
  rotulo: string;
  ref: React.Ref<HTMLInputElement>;
  valor: string;
  erro?: string;
  aoMudar: (valor: string) => void;
}

/** <input type="date">: o valor é "" ou "AAAA-MM-DD", como o pedido.ts espera. */
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
        aria-describedby={descritores(id, erro)}
      />
      <Erro id={id} texto={erro} />
    </div>
  );
}

/** Ids das mensagens de um campo: o erro primeiro, depois o aviso (se houver). */
function descritores(id: string, erro: string | undefined, extra: string | false = false) {
  const ids = [erro && `${id}-erro`, extra].filter(Boolean);
  return ids.length > 0 ? ids.join(" ") : undefined;
}

function Erro({ id, texto }: { id: string; texto?: string }) {
  if (!texto) return null;
  return (
    <p id={`${id}-erro`} className="text-sm text-destructive">
      {texto}
    </p>
  );
}
