import { Link } from "react-router";
import { ROTAS } from "@/rotas";
import { SeletorTema } from "@/tema/SeletorTema";
import { Marca } from "./Marca";
import { MenuCelular } from "./MenuCelular";
import { MenuUsuario } from "./MenuUsuario";
import { SeloOrigemDados } from "./SeloOrigemDados";

/**
 * Barra superior. No celular: botão do menu + marca, e o selo desce para uma segunda
 * linha (continua visível: a origem dos dados importa para ler qualquer número).
 */
export function BarraSuperior() {
  return (
    <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex h-14 items-center gap-2 px-4 md:px-8">
        <MenuCelular />
        <Link
          to={ROTAS.visaoGeral}
          className="rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50 md:hidden"
        >
          <Marca />
          <span className="sr-only"> — ir para a visão geral</span>
        </Link>
        <SeloOrigemDados className="hidden sm:inline-flex" />
        <div className="ml-auto flex items-center gap-1">
          <SeletorTema />
          <MenuUsuario />
        </div>
      </div>
      <div className="border-t px-4 py-2 sm:hidden">
        <SeloOrigemDados />
      </div>
    </header>
  );
}
