import { Bell, Coins, MousePointerClick, Target, type LucideIcon } from "lucide-react";

// Aparência das regras no dashboard. A cor nunca vem sozinha: todo uso mostra
// também o ícone e o código (ver SeloRegra). As cores são tokens de src/index.css.

export type TomRegra = "r1" | "r2" | "r3" | "outra";

export interface AparenciaRegra {
  codigo: string;
  tom: TomRegra;
  /** Nome da regra padrão na tabela congelada (v1.0); null para regras criadas pelo usuário. */
  nomePadrao: string | null;
  Icone: LucideIcon;
  /** Classes completas e literais, para o Tailwind encontrá-las no código. */
  classes: { texto: string; fundo: string };
  /** Cor para o Recharts (fill/stroke), que recebe CSS e não classes. */
  corCss: string;
}

const TONS: Record<TomRegra, Pick<AparenciaRegra, "Icone" | "classes" | "corCss">> = {
  r1: {
    Icone: MousePointerClick,
    classes: { texto: "text-regra-r1", fundo: "bg-regra-r1-suave" },
    corCss: "var(--regra-r1)",
  },
  r2: {
    Icone: Coins,
    classes: { texto: "text-regra-r2", fundo: "bg-regra-r2-suave" },
    corCss: "var(--regra-r2)",
  },
  r3: {
    Icone: Target,
    classes: { texto: "text-regra-r3", fundo: "bg-regra-r3-suave" },
    corCss: "var(--regra-r3)",
  },
  outra: {
    Icone: Bell,
    classes: { texto: "text-regra-outra", fundo: "bg-regra-outra-suave" },
    corCss: "var(--regra-outra)",
  },
};

// Código exato: o banco tem UNIQUE (usuario, codigo) sensível a maiúsculas, então
// "r1" seria outra regra, criada pelo usuário.
const PADRAO: Record<string, { tom: TomRegra; nome: string }> = {
  R1: { tom: "r1", nome: "CTR baixo" },
  R2: { tom: "r2", nome: "CPC alto" },
  R3: { tom: "r3", nome: "Custo sem conversão" },
};

export function aparenciaDaRegra(codigo: string): AparenciaRegra {
  // Object.hasOwn: "toString" ou "__proto__" não podem casar com o protótipo.
  const padrao = Object.hasOwn(PADRAO, codigo) ? PADRAO[codigo]! : null;
  const tom = padrao?.tom ?? "outra";
  return { codigo, tom, nomePadrao: padrao?.nome ?? null, ...TONS[tom] };
}
