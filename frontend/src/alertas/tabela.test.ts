// Oráculo: 4 alertas reais do banco limen (consulta só leitura de 15/11/2026, colunas
// explícitas), com valores_medidos e condicoes copiados como vieram. CTR esperado =
// round(ctr, 2) do PostgreSQL (o oráculo do decimal.ts). Casos sintéticos estão marcados.
import { describe, expect, it } from "vitest";
import type { ResultadoFiltros } from "./filtros";
import {
  AVISO_REGRA_MUDOU,
  celulasAlerta,
  estadoVazioAlertas,
  faseAlertas,
  formatarMedido,
  lerCondicaoCopiada,
  regraDoAlerta,
  regraMudou,
  TEXTO_FILTROS_INVALIDOS,
  textoContagem,
  textoDisparo,
  textoStatusAlertas,
  type Alerta,
  type FaseAlertas,
} from "./tabela";

const NBSP = "\u00A0";

const base = { criado_em: "2026-11-13T12:00:00Z", origem: "sintetica" };
const REAIS: Alerta[] = [
  {
    ...base,
    id: 45,
    avaliacao_id: 2,
    data: "2026-11-11",
    campanha_id: 2,
    campanha_nome: "Limen C - Pesquisa",
    regra_id: 1,
    regra_codigo: "R1",
    regra_nome: "CTR baixo",
    valores_medidos: { ctr: "0.5719538351547339393320396282" },
    condicoes: [{ limiar: "1.000000", metrica: "ctr", operador: "<" }],
  },
  {
    ...base,
    id: 9,
    avaliacao_id: 1,
    data: "2026-11-10",
    campanha_id: 1,
    campanha_nome: "Limen A - Pesquisa",
    regra_id: 2,
    regra_codigo: "R2",
    regra_nome: "CPC alto",
    valores_medidos: { cpc: "7.20" },
    condicoes: [{ limiar: "5.000000", metrica: "cpc", operador: ">" }],
  },
  {
    ...base,
    id: 18,
    avaliacao_id: 1,
    data: "2026-11-10",
    campanha_id: 3,
    campanha_nome: "Limen B - Pesquisa",
    regra_id: 3,
    regra_codigo: "R3",
    regra_nome: "Custo sem conversão",
    valores_medidos: { custo: "446.40", conversoes: "0.000000" },
    condicoes: [
      { limiar: "100.000000", metrica: "custo", operador: ">" },
      { limiar: "0.000000", metrica: "conversoes", operador: "==" },
    ],
  },
  {
    ...base,
    id: 16,
    avaliacao_id: 1,
    data: "2026-11-06",
    campanha_id: 3,
    campanha_nome: "Limen B - Pesquisa",
    regra_id: 1,
    regra_codigo: "R1",
    regra_nome: "CTR baixo",
    valores_medidos: { ctr: "0.3752985329239167519617877857" },
    condicoes: [{ limiar: "1.000000", metrica: "ctr", operador: "<" }],
  },
];
const [C_R1, A_R2, B_R3, B_R1] = REAIS as [Alerta, Alerta, Alerta, Alerta];

// Regras atuais como o GET /regras devolve (limiar NUMERIC com 6 casas; conferido em 15/11).
const R1_ATUAL = { condicoes: [{ ordem: 1, metrica: "ctr", operador: "<", limiar: "1.000000" }] };
const R3_ATUAL = {
  condicoes: [
    { ordem: 2, metrica: "conversoes", operador: "==", limiar: "0.000000" },
    { ordem: 1, metrica: "custo", operador: ">", limiar: "100.000000" },
  ],
};

describe("celulasAlerta com os alertas reais", () => {
  it("dia como texto, sem new Date (11/11, não 10/11)", () => {
    expect(celulasAlerta(C_R1, R1_ATUAL).dia).toBe("11/11/2026");
  });
  it("campanha e regra como vieram da API", () => {
    const c = celulasAlerta(C_R1, R1_ATUAL);
    expect([c.campanha, c.codigo, c.nome]).toEqual(["Limen C - Pesquisa", "R1", "CTR baixo"]);
  });
  it.each([
    [C_R1, "CTR 0,57% < 1%", "CTR 0,57%, menor que 1%"],
    [B_R1, "CTR 0,38% < 1%", "CTR 0,38%, menor que 1%"],
    [A_R2, `CPC R$${NBSP}7,20 > R$${NBSP}5`, `CPC R$${NBSP}7,20, maior que R$${NBSP}5`],
  ])("alerta real %#: o que disparou", (alerta, visivel, acessivel) => {
    expect(celulasAlerta(alerta, undefined).disparos).toEqual([{ visivel, acessivel }]);
  });
  it("R3: uma linha por condição, na ordem da cópia", () => {
    expect(celulasAlerta(B_R3, R3_ATUAL).disparos).toEqual([
      { visivel: `Custo R$${NBSP}446,40 > R$${NBSP}100`, acessivel: `Custo R$${NBSP}446,40, maior que R$${NBSP}100` },
      { visivel: "Conversões 0 == 0", acessivel: "Conversões 0, igual a 0" },
    ]);
  });
  it("regra sem mudança: false, mesmo com o limiar em outro formato e a ordem da API embaralhada", () => {
    expect(celulasAlerta(C_R1, R1_ATUAL).regraMudou).toBe(false);
    expect(celulasAlerta(B_R3, R3_ATUAL).regraMudou).toBe(false);
  });
  it("regra fora da lista: null (não sabe)", () => {
    expect(celulasAlerta(C_R1, undefined).regraMudou).toBeNull();
  });
});

describe("a cópia do alerta vale, não a regra atual (sintético: R4 editada depois)", () => {
  const alerta: Alerta = {
    ...C_R1,
    id: 900,
    regra_id: 4,
    regra_codigo: "R4",
    regra_nome: "CTR muito baixo",
    valores_medidos: { ctr: "1.5" },
    condicoes: [{ limiar: "2.000000", metrica: "ctr", operador: "<" }],
  };
  const atual = { condicoes: [{ ordem: 1, metrica: "ctr", operador: "<", limiar: "3.000000" }] };

  it("o limiar mostrado é o da avaliação (2%), não o atual (3%)", () => {
    expect(celulasAlerta(alerta, atual).disparos).toEqual([{ visivel: "CTR 1,50% < 2%", acessivel: "CTR 1,50%, menor que 2%" }]);
  });
  it("e a tela avisa que a regra mudou", () => {
    expect(celulasAlerta(alerta, atual).regraMudou).toBe(true);
    expect(AVISO_REGRA_MUDOU).toMatch(/são as da avaliação/);
  });
  it.each([
    ["operador", { condicoes: [{ ordem: 1, metrica: "ctr", operador: "<=", limiar: "2" }] }],
    ["métrica", { condicoes: [{ ordem: 1, metrica: "cpc", operador: "<", limiar: "2" }] }],
    [
      "uma condição a mais",
      {
        condicoes: [
          { ordem: 1, metrica: "ctr", operador: "<", limiar: "2" },
          { ordem: 2, metrica: "custo", operador: ">", limiar: "1" },
        ],
      },
    ],
  ])("mudou o %s: true", (_, regra) => {
    expect(regraMudou(alerta.condicoes, regra)).toBe(true);
  });
});

describe("formatarMedido", () => {
  it("valor normalizado: 28 casas viram 2, e o expoente some", () => {
    expect(formatarMedido("ctr", "0.5719538351547339393320396282", "1.000000").texto).toBe("0,57%");
    expect(formatarMedido("ctr", "0E-16", "1.000000").texto).toBe("0,00%");
    expect(formatarMedido("conversoes", "0.000000", "0.000000").texto).toBe("0");
    expect(formatarMedido("impressoes", "12345", "100").texto).toBe("12.345");
  });
  it.each([
    ["ctr", "0.996", "1.000000", "0,996%"],
    ["ctr", "1.0004", "1.000000", "1,0004%"],
    ["cpc", "5.004", "5.000000", `R$${NBSP}5,004`],
    // Limiar com 3 casas: arredonda com 3 (0,995 < 0,996); com 2 daria "1,00%", do outro lado do limiar.
    ["ctr", "0.9951", "0.996000", "0,995%"],
  ])("(sintético) %s %s contra %s: não parece igual ao limiar → %s", (metrica, valor, limiar, esperado) => {
    expect(formatarMedido(metrica, valor, limiar).texto).toBe(esperado);
  });
  it("igual de verdade (==) não ganha casas", () => {
    expect(formatarMedido("ctr", "1.000000", "1.000000").texto).toBe("1,00%");
  });
  it("ausente: — com 'sem dado' (ausente ≠ zero)", () => {
    expect(formatarMedido("ctr", null, "1").texto).toBe("—");
    expect(formatarMedido("ctr", undefined, "1").descricao).toBe("sem dado");
  });
  it("ilegível volta como veio", () => {
    expect(formatarMedido("ctr", "abc", "1").texto).toBe("abc");
  });
});

describe("textoDisparo e lerCondicaoCopiada", () => {
  it("métrica sem valor medido: 'sem dado' para o leitor de tela", () => {
    expect(textoDisparo({ metrica: "ctr", operador: "<", limiar: "1" }, {})).toEqual({
      visivel: "CTR — < 1%",
      acessivel: "CTR sem dado, menor que 1%",
    });
  });
  it("métrica 'toString' não é lida do protótipo (Object.hasOwn)", () => {
    expect(textoDisparo({ metrica: "toString", operador: "<", limiar: "1" }, {}).visivel).toBe("toString — < 1");
  });
  it.each([[{ metrica: "ctr", operador: "<" }], [{ metrica: "ctr", operador: "<", limiar: 1 }], [{}]])(
    "cópia sem os três textos: ilegível %#",
    (bruta) => {
      expect(lerCondicaoCopiada(bruta)).toBeNull();
      expect(textoDisparo(lerCondicaoCopiada(bruta), {}).visivel).toBe("condição ilegível");
    },
  );
});

describe("textoContagem", () => {
  it.each([
    [1, 500, "1 alerta"],
    [27, 500, "27 alertas"],
    [499, 500, "499 alertas"],
    [500, 500, "Mostrando os 500 alertas mais recentes. Use os filtros para ver os anteriores."],
    [5000, 5000, "Mostrando os 5.000 alertas mais recentes. Use os filtros para ver os anteriores."],
  ])("%i de limite %i → %s", (quantidade, limite, esperado) => {
    expect(textoContagem(quantidade, limite)).toBe(esperado);
  });
});

describe("estadoVazioAlertas", () => {
  it("sem filtro: explica de onde vêm os alertas e leva às Avaliações", () => {
    const v = estadoVazioAlertas(false);
    expect(v.acao.para).toBe("/avaliacoes");
    expect(v.texto).toMatch(/avaliação/);
  });
  it("com filtro: limpar leva a /alertas sem parâmetros", () => {
    expect(estadoVazioAlertas(true).acao).toEqual({ rotulo: "Limpar filtros", para: "/alertas" });
  });
});

describe("regraDoAlerta", () => {
  const regras = [
    { id: 3, nome: "R3" },
    { id: 1, nome: "R1" },
  ];
  it("pelo id, não pela posição", () => {
    expect(regraDoAlerta(regras, { regra_id: 1 })?.nome).toBe("R1");
  });
  it("lista ausente ou regra fora dela: undefined", () => {
    expect(regraDoAlerta(undefined, { regra_id: 1 })).toBeUndefined();
    expect(regraDoAlerta(regras, { regra_id: 9 })).toBeUndefined();
  });
});

describe("faseAlertas", () => {
  const desligada = { isPending: true, isError: false, error: null, data: undefined };
  const pronta: ResultadoFiltros = { estado: "pronta", consulta: { limite: 500 } };
  it("URL inválida vence a consulta desligada (que ficaria pending para sempre)", () => {
    expect(faseAlertas({ estado: "invalida", erros: { fim: "x" } }, desligada)).toEqual({ fase: "invalida" });
  });
  it("aguardando a lista", () => {
    expect(faseAlertas({ estado: "aguardando" }, desligada)).toEqual({ fase: "aguardando" });
  });
  it("carregando", () => {
    expect(faseAlertas(pronta, desligada)).toEqual({ fase: "carregando" });
  });
  it("erro sem dados", () => {
    const erro = new Error("x");
    expect(faseAlertas(pronta, { isPending: false, isError: true, error: erro, data: undefined })).toEqual({ fase: "erro", erro });
  });
  it("com dados", () => {
    expect(faseAlertas(pronta, { isPending: false, isError: false, error: null, data: REAIS })).toEqual({
      fase: "pronta",
      alertas: REAIS,
    });
  });
});

describe("textoStatusAlertas", () => {
  const FASES: [FaseAlertas, string][] = [
    [{ fase: "invalida" }, TEXTO_FILTROS_INVALIDOS],
    [{ fase: "aguardando" }, "Carregando os alertas…"],
    [{ fase: "carregando" }, "Carregando os alertas…"],
    [{ fase: "erro", erro: null }, ""],
    [{ fase: "pronta", alertas: [] }, "Nenhum alerta."],
    [{ fase: "pronta", alertas: REAIS }, "4 alertas"],
  ];
  it.each(FASES)("%o → %j", (fase, esperado) => {
    expect(textoStatusAlertas(fase)).toBe(esperado);
  });
});
