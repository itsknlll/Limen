import { useEffect, useRef, type MouseEvent } from "react";
import { Outlet, ScrollRestoration, useLocation } from "react-router";
import { BarraLateral } from "./BarraLateral";
import { BarraSuperior } from "./BarraSuperior";

const ID_CONTEUDO = "conteudo";

/** Foca o h1 da página nova quando a rota muda (não na primeira carga). */
function useFocoAoNavegar() {
  const { pathname } = useLocation();
  // Compara com o caminho anterior em vez de "pular a primeira execução": no
  // StrictMode o efeito roda duas vezes na montagem, e o foco iria para o h1 na
  // primeira carga, passando por cima do link "pular para o conteúdo".
  const anterior = useRef(pathname);
  useEffect(() => {
    if (anterior.current === pathname) return;
    // Atualiza antes de qualquer saída: mesmo quando o foco fica com o diálogo, esta
    // rota já foi tratada, e voltar a ela depois não pode parecer "mesma rota".
    anterior.current = pathname;
    const titulo = document.querySelector<HTMLElement>(`#${ID_CONTEUDO} h1`);
    // Um diálogo ainda aberto (ex.: o Sheet do menu do celular, durante a animação de
    // fechar) esconde a página com aria-hidden até desmontar. Focar o h1 agora deixaria
    // o foco dentro de uma área escondida (o Chrome bloqueia o aria-hidden e avisa no
    // console). Quem cuida do foco é o diálogo: o MenuCelular foca o h1 depois de
    // desmontar (onCloseAutoFocus roda após a retirada do aria-hidden).
    if (!titulo || titulo.closest('[aria-hidden="true"]')) return;
    titulo.focus();
  }, [pathname]);
}

function pularParaConteudo(evento: MouseEvent<HTMLAnchorElement>) {
  // Foco e rolagem à mão: o "#conteudo" na URL criaria uma entrada no histórico.
  evento.preventDefault();
  const principal = document.getElementById(ID_CONTEUDO);
  principal?.focus();
  principal?.scrollIntoView();
}

export function Layout() {
  useFocoAoNavegar();
  return (
    <div className="min-h-svh bg-background text-foreground">
      <a
        href={`#${ID_CONTEUDO}`}
        onClick={pularParaConteudo}
        // O espaçamento vai no estado de foco: `.focus\:not-sr-only:focus` zera o padding e,
        // por ter especificidade maior (classe + :focus), anulava um `px-4` comum.
        // `focus:px-4` tem a mesma especificidade e vem depois no CSS gerado, então vence.
        // A sombra separa o link do logo que fica embaixo dele.
        className="sr-only rounded-lg bg-primary text-sm font-medium text-primary-foreground focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2 focus:shadow-lg focus:outline-none focus:ring-3 focus:ring-ring/50"
      >
        Pular para o conteúdo
      </a>
      <BarraLateral />
      <div className="flex min-h-svh flex-col md:pl-60">
        <BarraSuperior />
        <main id={ID_CONTEUDO} tabIndex={-1} className="flex-1 px-4 py-6 outline-none md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
      <ScrollRestoration />
    </div>
  );
}
