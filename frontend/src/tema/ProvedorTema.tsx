import { useCallback, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { ContextoTema } from "./contexto";
import {
  aplicarTema,
  CHAVE_TEMA,
  CONSULTA_ESCURO,
  lerPreferencia,
  resolverTema,
  type Preferencia,
} from "./tema";

// localStorage pode lançar (aba anônima, dados do site bloqueados): nesse caso
// a preferência vale só nesta sessão e o padrão é "sistema".
function lerGuardada(): Preferencia {
  try {
    return lerPreferencia(window.localStorage.getItem(CHAVE_TEMA));
  } catch {
    return "sistema";
  }
}

function guardar(preferencia: Preferencia): void {
  try {
    window.localStorage.setItem(CHAVE_TEMA, preferencia);
  } catch {
    /* sem armazenamento: segue só em memória */
  }
}

function assinarSistema(avisar: () => void): () => void {
  const consulta = window.matchMedia(CONSULTA_ESCURO);
  consulta.addEventListener("change", avisar);
  return () => consulta.removeEventListener("change", avisar);
}

const sistemaEscuro = () => window.matchMedia(CONSULTA_ESCURO).matches;

export function ProvedorTema({ children }: { children: ReactNode }) {
  const [preferencia, setPreferencia] = useState<Preferencia>(lerGuardada);
  // Acompanha a troca de tema do sistema operacional enquanto a página está aberta.
  const escuroNoSistema = useSyncExternalStore(assinarSistema, sistemaEscuro);
  const temaResolvido = resolverTema(preferencia, escuroNoSistema);

  useEffect(() => {
    aplicarTema(document.documentElement, temaResolvido);
  }, [temaResolvido]);

  // Trocou o tema em outra aba: esta acompanha. (key null = localStorage.clear()).
  useEffect(() => {
    const aoMudar = (e: StorageEvent) => {
      if (e.key === CHAVE_TEMA || e.key === null) setPreferencia(lerPreferencia(e.newValue));
    };
    window.addEventListener("storage", aoMudar);
    return () => window.removeEventListener("storage", aoMudar);
  }, []);

  const definirPreferencia = useCallback((nova: Preferencia) => {
    setPreferencia(nova);
    guardar(nova);
  }, []);

  const valor = useMemo(
    () => ({ preferencia, temaResolvido, definirPreferencia }),
    [preferencia, temaResolvido, definirPreferencia],
  );

  return <ContextoTema.Provider value={valor}>{children}</ContextoTema.Provider>;
}
