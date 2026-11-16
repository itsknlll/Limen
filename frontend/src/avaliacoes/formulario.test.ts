// Testes de formulario.ts. Campanhas: as reais do banco limen (id interno, nome, status;
// mesma consulta só de leitura do historico.test.ts). Erros do servidor: os corpos reais de
// POST /avaliacoes do oráculo de campos.test.ts (linhas do período invertido e da data
// inválida), sem a mensagem em inglês.

import { describe, expect, it } from "vitest";
import { ErroApi } from "@/api/erros";
import { MENSAGEM_RECUSADO } from "@/api/campos";
import { MENSAGENS_PEDIDO } from "./pedido";
import {
  avisoAtual,
  campanhaDoSelect,
  decidirEnvio,
  depoisDoErro,
  FORMULARIO_INICIAL,
  opcoesCampanha,
  primeiroCampoComErro,
  semErroNoCampo,
  valorDoSelect,
  VALOR_TODAS,
} from "./formulario";

const CAMPANHAS = [
  { id: 1, nome: "Limen A - Pesquisa", status: "ENABLED" },
  { id: 2, nome: "Limen C - Pesquisa", status: "PAUSED" },
  { id: 3, nome: "Limen B - Pesquisa", status: "ENABLED" },
];

const PERIODO_INVERTIDO = new ErroApi({ status: 400, tipo: "validacao", detail: [{ local: ["body"], tipo: "value_error" }] });
const INICIO_INVALIDO = new ErroApi({
  status: 400,
  tipo: "validacao",
  detail: [{ local: ["body", "inicio"], tipo: "date_from_datetime_parsing" }],
});

describe("primeiroCampoComErro", () => {
  it.each([
    [{ campanhaId: "x", inicio: "x", fim: "x" }, "campanhaId"],
    [{ inicio: "x", fim: "x" }, "inicio"],
    [{ fim: "x", inicio: "x" }, "inicio"],
    [{ fim: "x" }, "fim"],
    [{}, null],
  ] as const)("%o → %s (ordem da tela, não a das chaves)", (erros, esperado) => {
    expect(primeiroCampoComErro(erros)).toBe(esperado);
  });
});

describe("decidirEnvio", () => {
  it("formulário inicial: envia só incluir_pausadas", () => {
    expect(decidirEnvio(FORMULARIO_INICIAL, CAMPANHAS, false)).toEqual({ acao: "enviar", corpo: { incluir_pausadas: false } });
  });

  it("com pedido em andamento, ignora (mesmo com formulário válido)", () => {
    expect(decidirEnvio(FORMULARIO_INICIAL, CAMPANHAS, true)).toEqual({ acao: "ignorar" });
  });

  it("com pedido em andamento, ignora também formulário inválido (não mostra erro)", () => {
    expect(decidirEnvio({ ...FORMULARIO_INICIAL, inicio: "2026-11-12", fim: "2026-11-11" }, CAMPANHAS, true)).toEqual({
      acao: "ignorar",
    });
  });

  it("campanha, período e pausadas", () => {
    const form = { campanhaId: "2", inicio: "2026-10-13", fim: "2026-11-11", incluirPausadas: true };
    expect(decidirEnvio(form, CAMPANHAS, false)).toEqual({
      acao: "enviar",
      corpo: { incluir_pausadas: true, campanha_id: 2, inicio: "2026-10-13", fim: "2026-11-11" },
    });
  });

  it("período invertido: corrige, com foco na data final", () => {
    const form = { ...FORMULARIO_INICIAL, inicio: "2026-11-12", fim: "2026-11-11" };
    expect(decidirEnvio(form, CAMPANHAS, false)).toEqual({
      acao: "corrigir",
      erros: { fim: MENSAGENS_PEDIDO.periodo },
      foco: "fim",
    });
  });

  it("campanha fora da lista e data inválida: foco na campanha (primeira da tela)", () => {
    const form = { ...FORMULARIO_INICIAL, campanhaId: "99", inicio: "2026-02-30" };
    expect(decidirEnvio(form, CAMPANHAS, false)).toEqual({
      acao: "corrigir",
      erros: { campanhaId: MENSAGENS_PEDIDO.campanha, inicio: MENSAGENS_PEDIDO.data },
      foco: "campanhaId",
    });
  });

  it("sem a lista (carregando ou com erro), só 'todas' passa", () => {
    expect(decidirEnvio(FORMULARIO_INICIAL, [], false).acao).toBe("enviar");
    expect(decidirEnvio({ ...FORMULARIO_INICIAL, campanhaId: "1" }, [], false).acao).toBe("corrigir");
  });
});

describe("depoisDoErro", () => {
  it("período invertido do servidor (local ['body']): nenhum campo, vai para o EstadoErro", () => {
    expect(depoisDoErro(PERIODO_INVERTIDO)).toEqual({ erros: {}, foco: null, restante: true });
  });

  it("data recusada pelo servidor: no campo, com foco", () => {
    expect(depoisDoErro(INICIO_INVALIDO)).toEqual({ erros: { inicio: MENSAGEM_RECUSADO }, foco: "inicio", restante: false });
  });

  it.each([
    ["sem conexão", new ErroApi({ status: null, tipo: "sem_conexao" })],
    ["cota excedida", new ErroApi({ status: 503, tipo: "cota_excedida", retryAfter: 3600 })],
    ["erro que não é ErroApi", new Error("qualquer")],
  ])("%s: nenhum campo, vai para o EstadoErro", (_nome, erro) => {
    expect(depoisDoErro(erro)).toEqual({ erros: {}, foco: null, restante: true });
  });
});

describe("semErroNoCampo", () => {
  it("tira só o campo editado", () => {
    expect(semErroNoCampo({ inicio: "a", fim: "b" }, "fim")).toEqual({ inicio: "a" });
  });

  it("campo sem erro: devolve o mesmo objeto (sem nova renderização à toa)", () => {
    const erros = { inicio: "a" };
    expect(semErroNoCampo(erros, "fim")).toBe(erros);
  });
});

describe("valor do select", () => {
  it("'' ↔ 'todas', ida e volta", () => {
    expect(valorDoSelect("")).toBe(VALOR_TODAS);
    expect(campanhaDoSelect(VALOR_TODAS)).toBe("");
    expect(VALOR_TODAS).not.toBe("");
  });

  it("id passa como está, nos dois sentidos", () => {
    expect(valorDoSelect("2")).toBe("2");
    expect(campanhaDoSelect("2")).toBe("2");
  });

  it("'todas' escolhido no select gera pedido sem campanha_id", () => {
    const form = { ...FORMULARIO_INICIAL, campanhaId: campanhaDoSelect(VALOR_TODAS) };
    expect(decidirEnvio(form, CAMPANHAS, false)).toEqual({ acao: "enviar", corpo: { incluir_pausadas: false } });
  });
});

describe("opcoesCampanha", () => {
  it("'Todas' primeiro, depois na ordem da API, com status quando não está ativa", () => {
    expect(opcoesCampanha(CAMPANHAS)).toEqual([
      { valor: VALOR_TODAS, rotulo: "Todas as campanhas" },
      { valor: "1", rotulo: "Limen A - Pesquisa" },
      { valor: "2", rotulo: "Limen C - Pesquisa (pausada)" },
      { valor: "3", rotulo: "Limen B - Pesquisa" },
    ]);
  });

  it("removida e status desconhecido", () => {
    expect(
      opcoesCampanha([
        { id: 4, nome: "X", status: "REMOVED" },
        { id: 5, nome: "Y", status: "NOVO_STATUS" },
      ]).slice(1),
    ).toEqual([
      { valor: "4", rotulo: "X (removida)" },
      { valor: "5", rotulo: "Y (NOVO_STATUS)" },
    ]);
  });

  it("sem campanhas: só 'Todas'", () => {
    expect(opcoesCampanha([])).toEqual([{ valor: VALOR_TODAS, rotulo: "Todas as campanhas" }]);
  });
});

describe("avisoAtual", () => {
  it("campanha C (pausada) sem incluir pausadas: aviso do pedido.ts", () => {
    expect(avisoAtual({ ...FORMULARIO_INICIAL, campanhaId: "2" }, CAMPANHAS)).toContain("Limen C - Pesquisa está pausada");
  });

  it("campanha C com incluir pausadas: sem aviso", () => {
    expect(avisoAtual({ ...FORMULARIO_INICIAL, campanhaId: "2", incluirPausadas: true }, CAMPANHAS)).toBeNull();
  });

  it("campanha ativa ou todas: sem aviso", () => {
    expect(avisoAtual({ ...FORMULARIO_INICIAL, campanhaId: "1" }, CAMPANHAS)).toBeNull();
    expect(avisoAtual(FORMULARIO_INICIAL, CAMPANHAS)).toBeNull();
  });
});
