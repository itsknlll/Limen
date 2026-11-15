import { type ComponentProps, type ReactNode, useId } from "react";
import { cn } from "@/lib/utils";

interface Props extends Omit<ComponentProps<"table">, "children"> {
  /** Legenda da tabela (<caption>); também dá nome à região rolável. */
  legenda: ReactNode;
  /** false: a legenda fica só para o leitor de tela (quando o título do cartão já diz o mesmo). */
  legendaVisivel?: boolean;
  children: ReactNode;
}

/**
 * Tabela que rola para o lado em telas estreitas, também pelo teclado.
 * O <Table> do shadcn já rola, mas o contêiner dele não recebe foco: quem usa teclado não
 * consegue rolar (WCAG 2.1.1). Aqui a região é focável (tabIndex={0}) e tem nome (a
 * legenda), para o leitor de tela anunciar o que é ao receber o foco. Fica sempre na
 * ordem do Tab, mesmo sem rolagem: detectar a rolagem mudaria o comportamento conforme a
 * largura da tela. O anel usa --ring sem transparência (par testado: ≥ 3:1).
 * Os filhos são os TableHeader/TableBody/TableRow do shadcn, sem o <Table>.
 */
export function TabelaRolavel({ legenda, legendaVisivel = false, className, children, ...props }: Props) {
  const idLegenda = useId();
  return (
    <div
      role="region"
      aria-labelledby={idLegenda}
      tabIndex={0}
      className="relative w-full overflow-x-auto rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <table data-slot="table" className={cn("w-full caption-top text-sm", className)} {...props}>
        <caption id={idLegenda} className={legendaVisivel ? "pb-3 text-left text-sm text-muted-foreground" : "sr-only"}>
          {legenda}
        </caption>
        {children}
      </table>
    </div>
  );
}
