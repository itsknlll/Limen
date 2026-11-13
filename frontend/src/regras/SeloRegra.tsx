import { cn } from "@/lib/utils";
import { aparenciaDaRegra } from "./aparencia";

interface Props {
  codigo: string;
  /** Nome vindo da API; se ausente, usa o nome padrão (R1 a R3) quando `comNome`. */
  nome?: string;
  comNome?: boolean;
  className?: string;
}

/** Selo da regra: ícone + código sempre visíveis; a cor é o terceiro sinal, nunca o único. */
export function SeloRegra({ codigo, nome, comNome = false, className }: Props) {
  const { Icone, classes, nomePadrao } = aparenciaDaRegra(codigo);
  const nomeExibido = comNome ? (nome ?? nomePadrao) : null;

  return (
    <span
      data-slot="selo-regra"
      className={cn(
        "inline-flex h-6 w-fit shrink-0 items-center gap-1.5 rounded-full px-2.5 text-xs font-medium whitespace-nowrap",
        classes.fundo,
        classes.texto,
        className,
      )}
    >
      <Icone aria-hidden className="size-3.5 shrink-0" />
      <span className="font-semibold">{codigo}</span>
      {nomeExibido && <span>{nomeExibido}</span>}
    </span>
  );
}
