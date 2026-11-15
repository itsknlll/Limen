import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Save, Trash2 } from "lucide-react";
import { type ComponentProps, type ReactNode, useEffect, useId, useRef, useState } from "react";
import { type Control, Controller, type FieldPath, useFieldArray, useForm, type UseFormRegister, useWatch } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";
import { errosNosCamposRegra } from "@/api/campos";
import { useSalvarRegra } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { ROTAS } from "@/rotas";
import { focoDaNovaCondicao } from "./edicao";
import { novaCondicao, previaLimiar, ROTULOS_METRICA, ROTULOS_OPERADOR, valoresIniciais, valoresNovaRegra, type Regra } from "./textos";
import { type CorpoRegra, esquemaRegra, LIMITES, METRICAS, OPERADORES, type ValoresFormulario } from "./validacao";

type Campo = FieldPath<ValoresFormulario>;
type CampoCondicao = `condicoes.${number}.metrica` | `condicoes.${number}.operador`;

const OPCOES_METRICA = METRICAS.map((m) => ({ valor: m, rotulo: ROTULOS_METRICA[m] }));
// Texto por extenso primeiro: o leitor de tela leria "<" como "menos".
const OPCOES_OPERADOR = OPERADORES.map((o) => ({ valor: o, rotulo: `${ROTULOS_OPERADOR[o]} (${o})` }));

/**
 * Formulário de regra nova (regra = null → POST /regras, endpoint fixo) ou de edição
 * (PUT /regras/{id}). Pedaço próprio no build; o h1 fica na página.
 * - Validação no navegador: o mesmo esquemaRegra do validarRegra (zodResolver); a saída
 *   do esquema já é o corpo do pedido (limiar normalizado, nome sem espaços nas pontas).
 * - Erros do servidor nos campos: errosNosCamposRegra (400 validacao pelo local do
 *   Pydantic; 409 conflito e regra_referencia no código); o resto vai para o EstadoErro.
 *   O foco vai para o primeiro campo recusado.
 * - Abaixo de cada limiar, "Será salvo como …" (previaLimiar), ligado ao campo por
 *   aria-describedby: lido ao focar, sem anunciar a cada tecla.
 * - Acessibilidade como na Fase 2: rótulo em todo campo, erro ligado ao campo
 *   (aria-invalid + aria-describedby), role="status" sempre presente, aria-disabled em
 *   vez de disabled no botão de enviar durante o pedido.
 * - Sucesso: aviso do sonner e volta para /regras (as consultas já foram invalidadas e
 *   relidas antes, pelo onSuccess de opcoesSalvarRegra).
 */
export default function FormularioRegra({ regra }: { regra: Regra | null }) {
  const id = useId();
  const navegar = useNavigate();
  const salvar = useSalvarRegra();
  const pendente = salvar.isPending;
  const [erroGeral, setErroGeral] = useState<{ erro: unknown } | null>(null);
  const [aviso, setAviso] = useState("");
  // Ref, e não estado: guardar o alvo do foco não precisa redesenhar nada.
  const focarDepois = useRef<Campo | null>(null);

  const {
    register,
    control,
    handleSubmit,
    setError,
    setFocus,
    formState: { errors },
  } = useForm<ValoresFormulario, unknown, CorpoRegra>({
    resolver: zodResolver(esquemaRegra),
    defaultValues: regra ? valoresIniciais(regra) : valoresNovaRegra(),
  });
  const { fields, append, remove } = useFieldArray({ control, name: "condicoes" });

  // Depois de remover uma condição, os índices mudam: o foco só vai quando a lista já foi redesenhada.
  useEffect(() => {
    const alvo = focarDepois.current;
    if (alvo === null) return;
    focarDepois.current = null;
    setFocus(alvo);
  }, [fields, setFocus]);

  const aoEnviar = (corpo: CorpoRegra) => {
    if (pendente) return;
    setErroGeral(null);
    setAviso(`Salvando ${corpo.codigo}…`);
    salvar.mutate(
      { id: regra?.id ?? null, corpo },
      {
        onSuccess: (salva) => {
          setAviso("");
          toast.success(regra ? `${salva.codigo} salva.` : `${salva.codigo} criada.`);
          void navegar(ROTAS.regras);
        },
        onError: (erro) => {
          const { campos, restante } = errosNosCamposRegra(erro);
          // As chaves seguem o caminho do formulário (CAMPO_REGRA em api/campos.ts).
          const nomes = Object.keys(campos) as Campo[];
          for (const nome of nomes) setError(nome, { type: "servidor", message: campos[nome] });
          if (restante) setErroGeral({ erro });
          setAviso(nomes.length > 0 ? "O servidor recusou a regra. Confira os campos marcados." : "Não foi possível salvar a regra.");
          const primeiro = nomes.find((n) => n !== "condicoes");
          if (primeiro !== undefined) setFocus(primeiro);
        },
      },
    );
  };

  // Erro no navegador: o react-hook-form já foca o primeiro campo inválido.
  const aoInvalidar = () => setAviso("A regra não foi salva. Confira os campos marcados.");

  const aoRemover = (indice: number) => {
    remove(indice);
    focarDepois.current = `condicoes.${Math.max(0, indice - 1)}.metrica`;
  };

  const erroCondicoes = errors.condicoes?.message ?? errors.condicoes?.root?.message;

  return (
    <form noValidate onSubmit={handleSubmit(aoEnviar, aoInvalidar)} className="flex flex-col gap-6">
      <span role="status" className="sr-only">
        {aviso}
      </span>
      {erroGeral && <EstadoErro erro={erroGeral.erro} />}

      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Identificação</h2>
          </CardTitle>
          <CardDescription>O código aparece nos selos e nos alertas.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <CampoTexto
            id={`${id}-codigo`}
            rotulo="Código"
            dica={`Até ${LIMITES.codigo} caracteres: letras sem acento, algarismos, _ ou -. R1, R2 e R3 são reservados (também em minúsculas).`}
            erro={errors.codigo?.message}
            autoComplete="off"
            className="max-w-xs"
            {...register("codigo")}
          />
          <CampoTexto
            id={`${id}-nome`}
            rotulo="Nome"
            dica={`Até ${LIMITES.nome} caracteres.`}
            erro={errors.nome?.message}
            autoComplete="off"
            className="max-w-xl"
            {...register("nome")}
          />
          <Controller
            control={control}
            name="ativa"
            render={({ field }) => (
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`${id}-ativa`}
                    ref={field.ref}
                    checked={field.value}
                    onCheckedChange={(marcado) => field.onChange(marcado === true)}
                    onBlur={field.onBlur}
                    aria-invalid={errors.ativa ? true : undefined}
                    aria-describedby={descritores(`${id}-ativa`, { erro: errors.ativa?.message, dica: true })}
                  />
                  <Label htmlFor={`${id}-ativa`}>Regra ativa</Label>
                </div>
                <Mensagens id={`${id}-ativa`} erro={errors.ativa?.message} dica="Só as regras ativas entram nas avaliações." />
              </div>
            )}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Condições</h2>
          </CardTitle>
          <CardDescription>
            Ligadas por E: o alerta só é gerado quando todas são verdadeiras no mesmo dia. CTR em %, custo e CPC em R$.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {erroCondicoes && <p className="text-sm text-destructive">{erroCondicoes}</p>}
          <ol className="flex flex-col gap-4">
            {fields.map((campo, indice) => (
              <li key={campo.id}>
                <LinhaCondicao
                  id={`${id}-${campo.id}`}
                  indice={indice}
                  control={control}
                  register={register}
                  erros={errors.condicoes?.[indice]}
                  podeRemover={fields.length > LIMITES.condicoesMin}
                  aoRemover={() => aoRemover(indice)}
                />
              </li>
            ))}
          </ol>
          {fields.length < LIMITES.condicoesMax ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="self-start"
              // Sem focusName, o react-hook-form focaria o Limiar (ver focoDaNovaCondicao).
              onClick={() => append(novaCondicao(), { focusName: focoDaNovaCondicao(fields.length) })}
            >
              <Plus aria-hidden />
              Adicionar condição
            </Button>
          ) : (
            <p className="text-sm text-muted-foreground">Máximo de {LIMITES.condicoesMax} condições.</p>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        <Button type="submit" aria-disabled={pendente} className="aria-disabled:cursor-wait aria-disabled:opacity-70">
          <Save aria-hidden />
          {pendente ? "Salvando…" : regra ? "Salvar alterações" : "Criar regra"}
        </Button>
        <Button asChild variant="outline">
          <Link to={ROTAS.regras}>Cancelar</Link>
        </Button>
      </div>
    </form>
  );
}

interface PropsLinha {
  id: string;
  indice: number;
  control: Control<ValoresFormulario, unknown, CorpoRegra>;
  register: UseFormRegister<ValoresFormulario>;
  erros?: { metrica?: { message?: string }; operador?: { message?: string }; limiar?: { message?: string } };
  podeRemover: boolean;
  aoRemover: () => void;
}

/** Uma condição: grupo com legenda "Condição N" (dá contexto aos rótulos repetidos). */
function LinhaCondicao({ id, indice, control, register, erros, podeRemover, aoRemover }: PropsLinha) {
  const numero = indice + 1;
  const [metrica, limiar] = useWatch({ control, name: [`condicoes.${indice}.metrica`, `condicoes.${indice}.limiar`] });
  const previa = previaLimiar(metrica, limiar);

  return (
    <fieldset className="flex flex-col gap-3 rounded-lg border p-3">
      <legend className="px-1 text-sm font-medium">Condição {numero}</legend>
      <div className="grid gap-3 sm:grid-cols-3">
        <CampoSelecao
          id={`${id}-metrica`}
          rotulo="Métrica"
          textoVazio="Escolha a métrica"
          opcoes={OPCOES_METRICA}
          control={control}
          nome={`condicoes.${indice}.metrica`}
          erro={erros?.metrica?.message}
        />
        <CampoSelecao
          id={`${id}-operador`}
          rotulo="Operador"
          textoVazio="Escolha o operador"
          opcoes={OPCOES_OPERADOR}
          control={control}
          nome={`condicoes.${indice}.operador`}
          erro={erros?.operador?.message}
        />
        <CampoTexto
          id={`${id}-limiar`}
          rotulo="Limiar"
          inputMode="decimal"
          autoComplete="off"
          erro={erros?.limiar?.message}
          extra={
            previa !== null && (
              <>
                Será salvo como <strong className="font-semibold text-foreground">{previa}</strong>
              </>
            )
          }
          {...register(`condicoes.${indice}.limiar`)}
        />
      </div>
      {podeRemover && (
        <Button type="button" variant="ghost" size="sm" className="self-start" onClick={aoRemover}>
          <Trash2 aria-hidden />
          Remover condição {numero}
        </Button>
      )}
    </fieldset>
  );
}

interface PropsSelecao {
  id: string;
  rotulo: string;
  textoVazio: string;
  opcoes: readonly { valor: string; rotulo: string }[];
  control: Control<ValoresFormulario, unknown, CorpoRegra>;
  nome: CampoCondicao;
  erro?: string;
}

/** Select do Radix ligado ao formulário; o ref vai para o gatilho (o setFocus e o foco no erro chegam nele). */
function CampoSelecao({ id, rotulo, textoVazio, opcoes, control, nome, erro }: PropsSelecao) {
  return (
    <Controller
      control={control}
      name={nome}
      render={({ field }) => (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={id}>{rotulo}</Label>
          <Select value={field.value} onValueChange={field.onChange} name={field.name}>
            <SelectTrigger
              id={id}
              ref={field.ref}
              onBlur={field.onBlur}
              aria-invalid={erro ? true : undefined}
              aria-describedby={descritores(id, { erro })}
              className="w-full"
            >
              <SelectValue placeholder={textoVazio} />
            </SelectTrigger>
            <SelectContent>
              {opcoes.map((o) => (
                <SelectItem key={o.valor} value={o.valor}>
                  {o.rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Mensagens id={id} erro={erro} />
        </div>
      )}
    />
  );
}

interface PropsCampoTexto extends ComponentProps<"input"> {
  id: string;
  rotulo: string;
  dica?: string;
  /** Texto auxiliar que muda com o valor (a prévia do limiar). */
  extra?: ReactNode;
  erro?: string;
}

function CampoTexto({ id, rotulo, dica, extra, erro, className, ...input }: PropsCampoTexto) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label htmlFor={id}>{rotulo}</Label>
      <Input
        id={id}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descritores(id, { erro, extra: Boolean(extra), dica: Boolean(dica) })}
        {...input}
      />
      <Mensagens id={id} erro={erro} extra={extra} dica={dica} />
    </div>
  );
}

/** Ids das mensagens de um campo, na ordem de leitura: erro, prévia, dica. */
function descritores(id: string, { erro, extra = false, dica = false }: { erro?: string; extra?: boolean; dica?: boolean }) {
  const ids = [erro && `${id}-erro`, extra && `${id}-extra`, dica && `${id}-dica`].filter(Boolean);
  return ids.length > 0 ? ids.join(" ") : undefined;
}

function Mensagens({ id, erro, extra, dica }: { id: string; erro?: string; extra?: ReactNode; dica?: string }) {
  return (
    <>
      {erro && (
        <p id={`${id}-erro`} className="text-sm text-destructive">
          {erro}
        </p>
      )}
      {extra && (
        <p id={`${id}-extra`} className="text-sm text-muted-foreground">
          {extra}
        </p>
      )}
      {dica && (
        <p id={`${id}-dica`} className="text-sm text-muted-foreground">
          {dica}
        </p>
      )}
    </>
  );
}
