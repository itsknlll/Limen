import createClient from "openapi-fetch";
import { erroDeRede, lerErro } from "./erros";
import type { components, paths } from "./esquema";

// Tipos gerados de /openapi.json por `npm run tipos:api` (backend na porta 8080).
// O arquivo é versionado: build e typecheck funcionam sem backend no ar, e o git diff
// mostra quando o contrato mudou.
export type Esquemas = components["schemas"];

// "/api" passa pelo proxy do Vite, que tira o prefixo (ver vite.config.ts). As rotas do
// OAuth não usam este cliente: são navegação de página inteira (o fetch não segue o
// redirecionamento para o Google).
export const api = createClient<paths>({ baseUrl: "/api" });

/**
 * Início do login com Google (GET /api/oauth/google/login no backend). É um link de
 * página inteira: o proxy do Vite repassa ao 8080 sem tirar o prefixo, o backend grava
 * state e PKCE na sessão e redireciona para o Google; o callback (8080) volta para "/".
 * Serve também para reconectar o Google (prompt=consent devolve um refresh token novo).
 */
export const URL_LOGIN_GOOGLE = "/api/oauth/google/login";

interface Resultado<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Desembrulha a resposta do openapi-fetch: devolve os dados ou lança ErroApi. */
export async function exigir<T>(chamada: Promise<Resultado<T>>): Promise<T> {
  let resultado: Resultado<T>;
  try {
    resultado = await chamada;
  } catch (causa) {
    throw erroDeRede(causa);
  }
  const { data, error, response } = resultado;
  if (!response.ok) throw lerErro(response.status, error, response.headers);
  return data as T;
}
