import { Menu, X } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Marca } from "./Marca";
import { Navegacao } from "./Navegacao";

/**
 * Menu recolhível para telas menores que md. O Sheet (Radix Dialog) prende o foco
 * enquanto aberto, fecha com Esc e devolve o foco ao botão que o abriu.
 * O botão de fechar do sheet.tsx gerado tem o texto "Close" em inglês; como os
 * componentes de ui não são editados, ele é desligado (showCloseButton={false}) e
 * substituído por um botão próprio, "Fechar menu".
 */
export function MenuCelular() {
  const [aberto, setAberto] = useState(false);
  // Fechou por um link: o foco vai para o h1 da página (como no Layout), e não de volta
  // ao botão do menu, que é o padrão do Radix. Fechou por Esc ou "Fechar menu": padrão.
  const fechouPorLink = useRef(false);
  const aoNavegar = () => {
    fechouPorLink.current = true;
    setAberto(false);
  };
  const aoDevolverFoco = (evento: Event) => {
    if (!fechouPorLink.current) return;
    fechouPorLink.current = false;
    evento.preventDefault();
    document.querySelector<HTMLElement>("#conteudo h1")?.focus();
  };
  return (
    <Sheet open={aberto} onOpenChange={setAberto}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Abrir menu">
          <Menu aria-hidden />
        </Button>
      </SheetTrigger>
      <SheetContent
        side="left"
        showCloseButton={false}
        // Sem descrição: o título basta. undefined evita o aviso do Radix.
        aria-describedby={undefined}
        onCloseAutoFocus={aoDevolverFoco}
        className="w-72 gap-6 bg-sidebar px-3 py-4 text-sidebar-foreground"
      >
        <SheetHeader className="flex-row items-center justify-between p-0 pl-2">
          <SheetTitle asChild>
            <div>
              <Marca subtitulo />
              <span className="sr-only">Menu de navegação</span>
            </div>
          </SheetTitle>
          <SheetClose asChild>
            <Button variant="ghost" size="icon" aria-label="Fechar menu">
              <X aria-hidden />
            </Button>
          </SheetClose>
        </SheetHeader>
        <Navegacao aoNavegar={aoNavegar} />
      </SheetContent>
    </Sheet>
  );
}
