// Erros do servidor nos campos dos formulários de regra e de avaliação (Fase 3, etapa 3).
// Oráculo dos testes: o corpo real dos erros 400 e 409 da API, colhido por um script
// temporário (campos.test.ts).
//
// O 400 de validação traz, em cada item, o `local` do Pydantic (["body","condicoes",1,
// "limiar"]); camposInvalidos (erros.ts) já o transforma em "condicoes.1.limiar". A
// mensagem do Pydantic vem em inglês e não é usada: o campo recebe uma frase em português.
// Um local que não é campo do formulário (ex.: ["body"] do período invertido) e qualquer
// outro erro ficam em `restante`: a tela mostra o EstadoErro, com a ação que o tipo pede.

import type { CampoAvaliacao } from "@/avaliacoes/pedido";
import { MENSAGENS } from "@/regras/validacao";
import { camposInvalidos, ErroApi } from "./erros";

export interface ErrosNosCampos {
  campos: Record<string, string>;
  restante: boolean;
}

export const MENSAGEM_RECUSADO = "O servidor recusou este valor.";
export const MENSAGEM_CODIGO_REPETIDO = "Já existe uma regra com este código.";

const CAMPO_REGRA = /^(?:codigo|nome|ativa|condicoes|condicoes\.\d+\.(?:metrica|operador|limiar))$/;
const CAMPO_AVALIACAO: Record<string, CampoAvaliacao> = { campanha_id: "campanhaId", inicio: "inicio", fim: "fim" };

type PorTipo = Record<string, { campo: string; mensagem: string }>;

function distribuir(erro: unknown, traduzir: (campo: string) => string | null, porTipo: PorTipo): ErrosNosCampos {
  if (!(erro instanceof ErroApi)) return { campos: {}, restante: true };
  if (Object.hasOwn(porTipo, erro.tipo)) {
    const { campo, mensagem } = porTipo[erro.tipo]!;
    return { campos: { [campo]: mensagem }, restante: false };
  }
  if (erro.tipo !== "validacao") return { campos: {}, restante: true };
  const lista = camposInvalidos(erro.detail);
  const campos: Record<string, string> = {};
  let restante = lista.length === 0;
  for (const campoApi of lista) {
    const alvo = traduzir(campoApi);
    if (alvo === null) restante = true;
    else campos[alvo] ??= MENSAGEM_RECUSADO;
  }
  return { campos, restante };
}

/** Formulário de regra: campos com o mesmo caminho do validarRegra; os dois 409 vão para o código. */
export function errosNosCamposRegra(erro: unknown): ErrosNosCampos {
  return distribuir(erro, (campo) => (CAMPO_REGRA.test(campo) ? campo : null), {
    conflito: { campo: "codigo", mensagem: MENSAGEM_CODIGO_REPETIDO },
    regra_referencia: { campo: "codigo", mensagem: MENSAGENS.codigoReferencia },
  });
}

/** Formulário de avaliação: nomes da API traduzidos para os do formulário (campanha_id → campanhaId). */
export function errosNosCamposAvaliacao(erro: unknown): ErrosNosCampos {
  return distribuir(erro, (campo) => (Object.hasOwn(CAMPO_AVALIACAO, campo) ? CAMPO_AVALIACAO[campo]! : null), {});
}
