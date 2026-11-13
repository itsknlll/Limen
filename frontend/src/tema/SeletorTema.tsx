import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTema } from "./contexto";
import { lerPreferencia, PREFERENCIAS, type Preferencia } from "./tema";

const OPCOES: Record<Preferencia, { rotulo: string; Icone: LucideIcon }> = {
  claro: { rotulo: "Claro", Icone: Sun },
  escuro: { rotulo: "Escuro", Icone: Moon },
  sistema: { rotulo: "Sistema", Icone: Monitor },
};

export function SeletorTema() {
  const { preferencia, definirPreferencia } = useTema();
  const atual = OPCOES[preferencia];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Tema: ${atual.rotulo}`}>
          <atual.Icone aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40">
        <DropdownMenuLabel>Tema</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={preferencia}
          onValueChange={(valor) => definirPreferencia(lerPreferencia(valor))}
        >
          {PREFERENCIAS.map((p) => {
            const { rotulo, Icone } = OPCOES[p];
            return (
              <DropdownMenuRadioItem key={p} value={p}>
                <Icone aria-hidden />
                {rotulo}
              </DropdownMenuRadioItem>
            );
          })}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
