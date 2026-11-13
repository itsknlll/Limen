import { createContext, useContext } from "react";
import type { Preferencia, TemaResolvido } from "./tema";

export interface ValorTema {
  preferencia: Preferencia;
  temaResolvido: TemaResolvido;
  definirPreferencia: (preferencia: Preferencia) => void;
}

export const ContextoTema = createContext<ValorTema | null>(null);

export function useTema(): ValorTema {
  const valor = useContext(ContextoTema);
  if (!valor) throw new Error("useTema precisa estar dentro de <ProvedorTema>");
  return valor;
}
