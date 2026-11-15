import { CircleCheck, CircleOff, ListChecks, Lock, Pencil, Plus, Power } from "lucide-react";
import { useRef, useState } from "react";
import { generatePath, Link } from "react-router";
import { toast } from "sonner";
import { useAtivarRegra, useDesativarRegra, useRegras } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { EstadoVazio } from "@/componentes/EstadoVazio";
import { TabelaRolavel } from "@/componentes/TabelaRolavel";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatarInteiro } from "@/lib/formatar";
import { ROTAS } from "@/rotas";
import { EsqueletoRegras } from "./Esqueletos";
import { SeloRegra } from "./SeloRegra";
import { textoCondicoes, type Regra } from "./textos";

/** Conteúdo da tela Regras (pedaço próprio no build; o h1 fica na página). */
export default function ConteudoRegras() {
  const consulta = useRegras();

  if (consulta.isPending) return <EsqueletoRegras />;
  if (consulta.isError) {
    return <EstadoErro erro={consulta.error} aoTentarNovamente={() => void consulta.refetch()} tentando={consulta.isFetching} />;
  }
  if (consulta.data.length === 0) {
    return (
      <EstadoVazio
        Icone={ListChecks}
        titulo="Nenhuma regra ainda"
        texto="As regras R1 a R3 são criadas no primeiro login. Crie uma regra para o motor avaliar."
        acao={{ rotulo: "Nova regra", para: ROTAS.regraNova }}
      />
    );
  }
  return <ListaRegras regras={consulta.data} />;
}

const contar = (n: number, um: string, varios: string) => (n === 1 ? `1 ${um}` : `${formatarInteiro(n)} ${varios}`);

/**
 * Lista de regras com Editar, Ativar e Desativar.
 * - R1 a R3 (referencia: true): sem ações, com cadeado e texto; a API recusaria (409).
 * - Um só botão por linha alterna "Desativar"/"Ativar": é o mesmo elemento antes e
 *   depois da troca, então o foco fica nele (dois botões diferentes mandariam o foco
 *   para o <body> quando um sumisse).
 * - Desativar pede confirmação num alert-dialog controlado (um para a tabela). Sem
 *   Trigger, o Radix não sabe para onde devolver o foco ao fechar: o onCloseAutoFocus
 *   devolve ao botão da linha.
 * - aria-disabled em vez de disabled enquanto um pedido corre (o botão focado não perde
 *   o foco); o clique é ignorado no código. Um pedido por vez: as duas mutações
 *   compartilham o estado da tela.
 * - O role="status" existe sempre (vazio fora do pedido). O sucesso vai para o sonner,
 *   como na sincronização; o erro aparece acima da tabela, sem esconder a lista.
 */
function ListaRegras({ regras }: { regras: Regra[] }) {
  const ativar = useAtivarRegra();
  const desativar = useDesativarRegra();
  const [alvo, setAlvo] = useState<Regra | null>(null); // fica preenchido durante a animação de fechar
  const [confirmando, setConfirmando] = useState(false);
  const botoes = useRef(new Map<number, HTMLButtonElement>());

  const ocupado = ativar.isPending || desativar.isPending;
  const idEmAndamento = ativar.isPending ? ativar.variables?.id : desativar.isPending ? desativar.variables : undefined;
  const regraEmAndamento = regras.find((r) => r.id === idEmAndamento);
  // isError é booleano; o error da mutação é unknown e não pode ir direto para o JSX.
  const temErro = ativar.isError || desativar.isError;
  const erro = ativar.isError ? ativar.error : desativar.error;

  const aoAlternar = (regra: Regra) => {
    if (ocupado) return;
    if (regra.ativa) {
      setAlvo(regra);
      setConfirmando(true);
      return;
    }
    desativar.reset();
    ativar.mutate(regra, { onSuccess: () => toast.success(`${regra.codigo} ativada.`) });
  };

  const aoConfirmar = () => {
    if (alvo === null || ocupado) return;
    const regra = alvo;
    ativar.reset();
    desativar.mutate(regra.id, { onSuccess: () => toast.success(`${regra.codigo} desativada.`) });
  };

  const total = contar(regras.length, "regra", "regras");
  const ativas = contar(regras.filter((r) => r.ativa).length, "ativa", "ativas");

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Regras do motor</h2>
        </CardTitle>
        <CardDescription>
          {total}, {ativas}. R1 a R3 são as regras de referência da tabela congelada e não podem ser alteradas.
        </CardDescription>
        <CardAction>
          <Button asChild size="sm">
            <Link to={ROTAS.regraNova}>
              <Plus aria-hidden />
              Nova regra
            </Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <span role="status" className="sr-only">
          {regraEmAndamento ? `${ativar.isPending ? "Ativando" : "Desativando"} ${regraEmAndamento.codigo}…` : ""}
        </span>
        {temErro && <EstadoErro erro={erro} />}
        <TabelaRolavel legenda={`Regras do motor: ${total}, ${ativas}`}>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Regra</TableHead>
              <TableHead scope="col">Condições</TableHead>
              <TableHead scope="col">Situação</TableHead>
              <TableHead scope="col">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {regras.map((r) => {
              const condicoes = textoCondicoes(r);
              const aqui = r.id === idEmAndamento;
              return (
                <TableRow key={r.id}>
                  <TableHead scope="row" className="font-medium">
                    <div className="flex flex-col items-start gap-1">
                      <SeloRegra codigo={r.codigo} />
                      <span className="whitespace-normal">{r.nome}</span>
                    </div>
                  </TableHead>
                  <TableCell className="min-w-56 whitespace-normal">
                    <span aria-hidden="true">{condicoes.visivel}</span>
                    <span className="sr-only">{condicoes.acessivel}</span>
                  </TableCell>
                  <TableCell>
                    <SeloSituacao ativa={r.ativa} />
                  </TableCell>
                  <TableCell>
                    {r.referencia ? (
                      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                        <Lock aria-hidden className="size-4" />
                        Referência da tabela
                      </span>
                    ) : (
                      <div className="flex gap-2">
                        <Button asChild variant="outline" size="sm">
                          <Link to={generatePath(ROTAS.regraEditar, { id: String(r.id) })}>
                            <Pencil aria-hidden />
                            Editar<span className="sr-only"> {r.codigo}</span>
                          </Link>
                        </Button>
                        <Button
                          ref={(el) => {
                            if (el) botoes.current.set(r.id, el);
                            else botoes.current.delete(r.id);
                          }}
                          variant="outline"
                          size="sm"
                          onClick={() => aoAlternar(r)}
                          aria-disabled={ocupado}
                          className="aria-disabled:cursor-wait aria-disabled:opacity-70"
                        >
                          <Power aria-hidden />
                          {aqui ? (r.ativa ? "Desativando…" : "Ativando…") : r.ativa ? "Desativar" : "Ativar"}
                          <span className="sr-only"> {r.codigo}</span>
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </TabelaRolavel>
      </CardContent>

      <AlertDialog open={confirmando} onOpenChange={setConfirmando}>
        <AlertDialogContent
          onCloseAutoFocus={(evento) => {
            evento.preventDefault();
            if (alvo) botoes.current.get(alvo.id)?.focus();
          }}
        >
          <AlertDialogHeader>
            <AlertDialogTitle>Desativar {alvo?.codigo}?</AlertDialogTitle>
            <AlertDialogDescription>
              A regra deixa de entrar nas próximas avaliações. Ela não é apagada: os alertas que já gerou continuam no
              histórico, e você pode ativá-la de novo.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={aoConfirmar}>
              Desativar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}

/** Ativa/Desativada: texto e ícone próprios (a cor não é o único sinal); variantes com contraste testado. */
function SeloSituacao({ ativa }: { ativa: boolean }) {
  return ativa ? (
    <Badge variant="default">
      <CircleCheck aria-hidden />
      Ativa
    </Badge>
  ) : (
    <Badge variant="outline">
      <CircleOff aria-hidden />
      Desativada
    </Badge>
  );
}
