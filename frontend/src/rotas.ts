// Caminhos das telas do React, num lugar só (roteador, navegação e links usam daqui).
// Nenhum pode começar com /api: esse prefixo é do proxy do Vite para o backend
// (rotas.test.ts confere). Por isso /alertas pode ser tela e endpoint ao mesmo tempo.

export const ROTAS = {
  entrar: "/entrar",
  visaoGeral: "/",
  campanhas: "/campanhas",
  campanha: "/campanhas/:id",
  regras: "/regras",
  regraNova: "/regras/nova",
  regraEditar: "/regras/:id/editar",
  avaliacoes: "/avaliacoes",
  alertas: "/alertas",
} as const;

export type Rota = (typeof ROTAS)[keyof typeof ROTAS];

/** Itens da navegação principal, na ordem da barra lateral. */
export const ITENS_NAVEGACAO = [
  { rota: ROTAS.visaoGeral, rotulo: "Visão geral" },
  { rota: ROTAS.campanhas, rotulo: "Campanhas" },
  { rota: ROTAS.regras, rotulo: "Regras" },
  { rota: ROTAS.avaliacoes, rotulo: "Avaliações" },
  { rota: ROTAS.alertas, rotulo: "Alertas" },
] as const satisfies readonly { rota: Rota; rotulo: string }[];

/** Caminho relativo ao layout ("/campanhas/:id" → "campanhas/:id"), como o React Router aninhado pede. */
export function relativo(rota: Rota): string {
  return rota.replace(/^\//, "");
}
