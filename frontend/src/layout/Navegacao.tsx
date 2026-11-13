import { Bell, LayoutDashboard, ListChecks, Megaphone, Play, type LucideIcon } from "lucide-react";
import { NavLink } from "react-router";
import { cn } from "@/lib/utils";
import { ITENS_NAVEGACAO, ROTAS, type Rota } from "@/rotas";

const ICONES: Partial<Record<Rota, LucideIcon>> = {
  [ROTAS.visaoGeral]: LayoutDashboard,
  [ROTAS.campanhas]: Megaphone,
  [ROTAS.regras]: ListChecks,
  [ROTAS.avaliacoes]: Play,
  [ROTAS.alertas]: Bell,
};

/**
 * Navegação principal, usada na barra lateral e no menu do celular.
 * O NavLink põe aria-current="page" no item ativo; o destaque índigo (texto primary
 * sobre primary/10, conferido em contraste.test.ts) vem junto com o peso da fonte,
 * para a cor não ser o único sinal.
 */
export function Navegacao({ aoNavegar }: { aoNavegar?: () => void }) {
  return (
    <nav aria-label="Principal">
      <ul className="flex flex-col gap-1">
        {ITENS_NAVEGACAO.map(({ rota, rotulo }) => {
          const Icone = ICONES[rota] ?? LayoutDashboard;
          return (
            <li key={rota}>
              <NavLink
                to={rota}
                // "/" só fica ativo nele mesmo; "/campanhas" também em "/campanhas/3".
                end={rota === ROTAS.visaoGeral}
                onClick={aoNavegar}
                className={({ isActive }) =>
                  cn(
                    "flex h-9 items-center gap-3 rounded-lg px-3 text-sm outline-none transition-colors",
                    "focus-visible:ring-3 focus-visible:ring-ring/50",
                    isActive
                      ? "bg-primary/10 font-semibold text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                <Icone aria-hidden className="size-4 shrink-0" />
                {rotulo}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
