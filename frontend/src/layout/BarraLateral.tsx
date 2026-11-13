import { Link } from "react-router";
import { ROTAS } from "@/rotas";
import { Marca } from "./Marca";
import { Navegacao } from "./Navegacao";

/** Barra lateral fixa, a partir de md (768 px). Abaixo disso, a mesma navegação vai no MenuCelular. */
export function BarraLateral() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col gap-6 border-r bg-sidebar px-3 py-4 text-sidebar-foreground md:flex">
      <Link to={ROTAS.visaoGeral} className="rounded-lg px-2 outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
        <Marca subtitulo />
        <span className="sr-only"> — ir para a visão geral</span>
      </Link>
      <Navegacao />
    </aside>
  );
}
