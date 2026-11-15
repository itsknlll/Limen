// Oráculo: corpo real dos erros 400 e 409 da API (POST/PUT /regras e POST /avaliacoes),
// colhido em 15/11/2026 por um script temporário com a aplicação de verdade e sem banco
// (sessão falsa que falha se usada). A tabela foi gerada da saída JSON, sem edição à mão;
// a mensagem do Pydantic (em inglês) não foi guardada, porque o frontend não a usa.
import { describe, expect, it } from "vitest";
import { MENSAGENS } from "@/regras/validacao";
import {
  errosNosCamposAvaliacao,
  errosNosCamposRegra,
  MENSAGEM_CODIGO_REPETIDO,
  MENSAGEM_RECUSADO,
  type ErrosNosCampos,
} from "./campos";
import { ErroApi } from "./erros";

const RESPOSTAS: [string, string, string, number, string, { local: (string | number)[]; tipo: string }[] | null][] = [
  ["POST", "/regras", "{\"codigo\": \"\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 400, "validacao", [{"local": ["body", "codigo"], "tipo": "string_too_short"}]],
  ["POST", "/regras", "{\"codigo\": \"R 4\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 400, "validacao", [{"local": ["body", "codigo"], "tipo": "string_pattern_mismatch"}]],
  ["POST", "/regras", "{\"codigo\": \"R4\", \"nome\": \"\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 400, "validacao", [{"local": ["body", "nome"], "tipo": "string_too_short"}]],
  ["POST", "/regras", "{\"codigo\": \"R4\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 400, "validacao", [{"local": ["body", "nome"], "tipo": "missing"}]],
  ["POST", "/regras", "{\"codigo\": \"R4\", \"nome\": \"CPC muito alto\", \"condicoes\": []}", 400, "validacao", [{"local": ["body", "condicoes"], "tipo": "too_short"}]],
  ["POST", "/regras", "{\"codigo\": \"R4\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}, {\"metrica\": \"xyz\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 400, "validacao", [{"local": ["body", "condicoes", 1, "metrica"], "tipo": "enum"}]],
  ["POST", "/regras", "{\"codigo\": \"R4\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}, {\"metrica\": \"cpc\", \"operador\": \"=\", \"limiar\": \"7.5\"}]}", 400, "validacao", [{"local": ["body", "condicoes", 1, "operador"], "tipo": "enum"}]],
  ["POST", "/regras", "{\"codigo\": \"R4\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}, {\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"-1\"}]}", 400, "validacao", [{"local": ["body", "condicoes", 1, "limiar"], "tipo": "greater_than_equal"}]],
  ["POST", "/regras", "{\"codigo\": \"R4\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"0.0000001\"}]}", 400, "validacao", [{"local": ["body", "condicoes", 0, "limiar"], "tipo": "decimal_max_places"}]],
  ["POST", "/regras", "{\"codigo\": \"\", \"nome\": \"\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 400, "validacao", [{"local": ["body", "codigo"], "tipo": "string_too_short"}, {"local": ["body", "nome"], "tipo": "string_too_short"}]],
  ["POST", "/regras", "{\"codigo\": \"R1\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 409, "regra_referencia", null],
  ["POST", "/regras", "{\"codigo\": \"r2\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 409, "regra_referencia", null],
  ["PUT", "/regras/1", "{\"codigo\": \"\", \"nome\": \"CPC muito alto\", \"condicoes\": [{\"metrica\": \"cpc\", \"operador\": \">\", \"limiar\": \"7.5\"}]}", 400, "validacao", [{"local": ["body", "codigo"], "tipo": "string_too_short"}]],
  ["POST", "/avaliacoes", "{\"inicio\": \"2026-11-12\", \"fim\": \"2026-11-11\"}", 400, "validacao", [{"local": ["body"], "tipo": "value_error"}]],
  ["POST", "/avaliacoes", "{\"inicio\": \"2026-02-30\"}", 400, "validacao", [{"local": ["body", "inicio"], "tipo": "date_from_datetime_parsing"}]],
  ["POST", "/avaliacoes", "{\"fim\": \"abc\"}", 400, "validacao", [{"local": ["body", "fim"], "tipo": "date_from_datetime_parsing"}]],
  ["POST", "/avaliacoes", "{\"campanha_id\": \"abc\"}", 400, "validacao", [{"local": ["body", "campanha_id"], "tipo": "int_parsing"}]],
  ["POST", "/avaliacoes", "{\"incluir_pausadas\": \"talvez\"}", 400, "validacao", [{"local": ["body", "incluir_pausadas"], "tipo": "bool_parsing"}]],
];

const R = MENSAGEM_RECUSADO;
/** O esperado para cada resposta do oráculo, na mesma ordem. */
const ESPERADO: ErrosNosCampos[] = [
  { campos: { codigo: R }, restante: false },
  { campos: { codigo: R }, restante: false },
  { campos: { nome: R }, restante: false },
  { campos: { nome: R }, restante: false },
  { campos: { condicoes: R }, restante: false },
  { campos: { "condicoes.1.metrica": R }, restante: false },
  { campos: { "condicoes.1.operador": R }, restante: false },
  { campos: { "condicoes.1.limiar": R }, restante: false },
  { campos: { "condicoes.0.limiar": R }, restante: false },
  { campos: { codigo: R, nome: R }, restante: false },
  { campos: { codigo: MENSAGENS.codigoReferencia }, restante: false },
  { campos: { codigo: MENSAGENS.codigoReferencia }, restante: false },
  { campos: { codigo: R }, restante: false },
  { campos: {}, restante: true }, // período invertido: o local é só ["body"]
  { campos: { inicio: R }, restante: false },
  { campos: { fim: R }, restante: false },
  { campos: { campanhaId: R }, restante: false },
  { campos: {}, restante: true }, // incluir_pausadas não é campo de texto do formulário
];

describe("erros reais da API nos campos", () => {
  it("um esperado para cada resposta do oráculo", () => {
    expect(ESPERADO).toHaveLength(RESPOSTAS.length);
  });

  it.each(RESPOSTAS.map((resposta, i) => [...resposta, ESPERADO[i]!] as const))(
    "%s %s %s → %i %s",
    (_metodo, caminho, _corpo, status, tipo, itens, esperado) => {
      // O 409 traz uma frase no detail; o texto não importa (o frontend decide pelo tipo).
      const erro = new ErroApi({ status, tipo, detail: itens ?? "frase do backend" });
      const distribuir = caminho === "/avaliacoes" ? errosNosCamposAvaliacao : errosNosCamposRegra;
      expect(distribuir(erro)).toEqual(esperado);
    },
  );
});

describe("casos fora do oráculo", () => {
  it("409 conflito (código repetido, vem do UNIQUE do banco) vai para o código", () => {
    expect(errosNosCamposRegra(new ErroApi({ status: 409, tipo: "conflito", detail: "Já existe…" }))).toEqual({
      campos: { codigo: MENSAGEM_CODIGO_REPETIDO },
      restante: false,
    });
  });

  it("conflito no formulário de avaliação não é campo", () => {
    expect(errosNosCamposAvaliacao(new ErroApi({ status: 409, tipo: "conflito" }))).toEqual({ campos: {}, restante: true });
  });

  it.each([
    ["sem conexão", new ErroApi({ status: null, tipo: "sem_conexao" })],
    ["erro do Google", new ErroApi({ status: 502, tipo: "erro_google_ads" })],
    ["validação sem lista", new ErroApi({ status: 400, tipo: "validacao", detail: "texto" })],
    ["erro que não é da API", new Error("qualquer")],
  ])("%s fica em restante", (_, erro) => {
    expect(errosNosCamposRegra(erro)).toEqual({ campos: {}, restante: true });
  });

  it("local que não é campo não vira campo; os conhecidos continuam", () => {
    const erro = new ErroApi({
      status: 400,
      tipo: "validacao",
      detail: [{ local: ["body", "xyz"] }, { local: ["body", "nome"] }],
    });
    expect(errosNosCamposRegra(erro)).toEqual({ campos: { nome: R }, restante: true });
  });
});
