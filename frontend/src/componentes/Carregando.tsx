import type { ReactNode } from "react";

// Região que está carregando. Os blocos de esqueleto são decorativos (aria-hidden);
// o leitor de tela ouve só o texto de status.
//
// Um status por região que carrega: usado sozinho (uma consulta carregando), anuncia o
// seu. Dentro de uma região maior que já anuncia, recebe comStatus={false} e fica só
// visual, para o leitor de tela não ouvir várias mensagens seguidas.

interface Props {
  texto: string;
  /** false: só os blocos visuais, sem role="status" (quem anuncia é a região de fora). */
  comStatus: boolean;
  className?: string;
  children: ReactNode;
}

export function Carregando({ texto, comStatus, className, children }: Props) {
  if (!comStatus) {
    return (
      <div aria-hidden="true" className={className}>
        {children}
      </div>
    );
  }
  return (
    <div aria-busy="true" className={className}>
      <span role="status" className="sr-only">
        {texto}
      </span>
      <div aria-hidden="true" className="contents">
        {children}
      </div>
    </div>
  );
}
