import { describe, expect, it } from "vitest";
import { corpoParaAtivar, METRICAS, OPERADORES, validarRegra, type CorpoRegra } from "./validacao";
import {
  formatarLimiar,
  novaCondicao,
  previaLimiar,
  rotuloMetrica,
  rotuloOperador,
  ROTULOS_METRICA,
  ROTULOS_OPERADOR,
  textoCondicao,
  textoCondicoes,
  valoresIniciais,
  valoresNovaRegra,
  type Regra,
} from "./textos";

const R$ = "R$\u00A0";

// Limiares como o banco limen devolve (NUMERIC com 6 casas, consulta de 15/11).
const R1: Regra = {
  id: 1,
  codigo: "R1",
  nome: "CTR baixo",
  ativa: true,
  referencia: true,
  condicoes: [{ ordem: 1, metrica: "ctr", operador: "<", limiar: "1.000000" }],
};
const R3: Regra = {
  id: 3,
  codigo: "R3",
  nome: "Custo sem conversão",
  ativa: true,
  referencia: true,
  condicoes: [
    { ordem: 1, metrica: "custo", operador: ">", limiar: "100.000000" },
    { ordem: 2, metrica: "conversoes", operador: "==", limiar: "0.000000" },
  ],
};
// Regras do usuário (as que o formulário edita), com as condições fora de ordem de propósito.
const R4: Regra = {
  id: 4,
  codigo: "R4",
  nome: "CPC alto",
  ativa: true,
  referencia: false,
  condicoes: [{ ordem: 1, metrica: "cpc", operador: ">", limiar: "7.500000" }],
};
const R9: Regra = {
  id: 9,
  codigo: "R9_teste",
  nome: "Muitas impressões, poucos cliques",
  ativa: false,
  referencia: false,
  condicoes: [
    { ordem: 2, metrica: "cliques", operador: "<=", limiar: "10.000000" },
    { ordem: 1, metrica: "impressoes", operador: ">=", limiar: "123456789012.123456" },
  ],
};

describe("rótulos", () => {
  it("cobrem exatamente as métricas e os operadores do formulário", () => {
    expect(Object.keys(ROTULOS_METRICA).sort()).toEqual([...METRICAS].sort());
    expect(Object.keys(ROTULOS_OPERADOR).sort()).toEqual([...OPERADORES].sort());
  });

  it.each(["toString", "__proto__", "receita", ""])("valor desconhecido %j volta como veio", (v) => {
    expect(rotuloMetrica(v)).toBe(v);
    expect(rotuloOperador(v)).toBe(v);
  });
});

describe("formatarLimiar", () => {
  it.each([
    ["ctr", "1.000000", "1%"],
    ["cpc", "5.000000", `${R$}5`],
    ["custo", "100.000000", `${R$}100`],
    ["conversoes", "0.000000", "0"],
    ["custo", "1234.500000", `${R$}1.234,5`],
    ["ctr", "0.125000", "0,125%"], // sem arredondar para 2 casas
    ["impressoes", "123456789012.123456", "123.456.789.012,123456"], // float estragaria
    ["toString", "2.000000", "2"], // métrica desconhecida: sem unidade
    ["ctr", "abc", "abc%"],
  ])("(%s, %s) → %s", (metrica, limiar, esperado) => {
    expect(formatarLimiar(metrica, limiar)).toBe(esperado);
  });
});

describe("textoCondicao e textoCondicoes", () => {
  it("R1: símbolo na tela, por extenso para o leitor de tela", () => {
    expect(textoCondicao(R1.condicoes[0]!)).toEqual({ visivel: "CTR < 1%", acessivel: "CTR menor que 1%" });
  });

  it("R3: condições ligadas por E", () => {
    expect(textoCondicoes(R3)).toEqual({
      visivel: `Custo > ${R$}100 e Conversões == 0`,
      acessivel: `Custo maior que ${R$}100 e Conversões igual a 0`,
    });
  });

  it("segue a ordem da regra, não a da lista recebida", () => {
    expect(textoCondicoes(R9).visivel).toBe("Impressões >= 123.456.789.012,123456 e Cliques <= 10");
  });
});

describe("valoresIniciais", () => {
  it("limiar volta normalizado, só como texto", () => {
    expect(valoresIniciais(R4).condicoes).toEqual([{ metrica: "cpc", operador: ">", limiar: "7.5" }]);
    expect(valoresIniciais(R3).condicoes.map((c) => c.limiar)).toEqual(["100", "0"]);
    expect(valoresIniciais(R1).condicoes[0]!.limiar).toBe("1");
  });

  it("ordena pela ordem e mantém os 18 algarismos do limiar grande", () => {
    expect(valoresIniciais(R9).condicoes).toEqual([
      { metrica: "impressoes", operador: ">=", limiar: "123456789012.123456" },
      { metrica: "cliques", operador: "<=", limiar: "10" },
    ]);
  });

  it("copia código, nome e situação (desativada continua desativada)", () => {
    const { codigo, nome, ativa } = valoresIniciais(R9);
    expect({ codigo, nome, ativa }).toEqual({ codigo: "R9_teste", nome: "Muitas impressões, poucos cliques", ativa: false });
  });

  it("limiar ilegível vai como veio, e a validação aponta o campo", () => {
    const valores = valoresIniciais({ ...R4, condicoes: [{ ...R4.condicoes[0]!, limiar: "abc" }] });
    expect(valores.condicoes[0]!.limiar).toBe("abc");
    const r = validarRegra(valores);
    expect(r.ok === false && "condicoes.0.limiar" in r.erros).toBe(true);
  });

  // Volta completa: regra da API → formulário → validarRegra devolve o corpo da regra original.
  const CORPOS: [Regra, CorpoRegra][] = [
    [R4, { codigo: "R4", nome: "CPC alto", ativa: true, condicoes: [{ metrica: "cpc", operador: ">", limiar: "7.5" }] }],
    [
      R9,
      {
        codigo: "R9_teste",
        nome: "Muitas impressões, poucos cliques",
        ativa: false,
        condicoes: [
          { metrica: "impressoes", operador: ">=", limiar: "123456789012.123456" },
          { metrica: "cliques", operador: "<=", limiar: "10" },
        ],
      },
    ],
  ];

  it.each(CORPOS)("valoresIniciais + validarRegra devolve o corpo da regra %#", (regra, esperado) => {
    expect(validarRegra(valoresIniciais(regra))).toEqual({ ok: true, corpo: esperado });
  });

  it("regra ativa: o mesmo corpo do corpoParaAtivar (dois caminhos, mesmo PUT)", () => {
    expect(validarRegra(valoresIniciais(R4))).toEqual(corpoParaAtivar(R4));
  });

  it("R1 a R3 não passam no formulário (a tela de edição delas é só leitura)", () => {
    for (const r of [R1, R3]) {
      const v = validarRegra(valoresIniciais(r));
      expect(v.ok === false && "codigo" in v.erros).toBe(true);
    }
  });
});

describe("valoresNovaRegra e novaCondicao", () => {
  it("nova regra: ativa, campos vazios, uma condição em branco", () => {
    expect(valoresNovaRegra()).toEqual({
      codigo: "",
      nome: "",
      ativa: true,
      condicoes: [{ metrica: "", operador: "", limiar: "" }],
    });
  });

  it("cada chamada devolve objetos novos (o useFieldArray não compartilha a condição)", () => {
    expect(novaCondicao()).not.toBe(novaCondicao());
    expect(valoresNovaRegra().condicoes).not.toBe(valoresNovaRegra().condicoes);
  });
});

describe("previaLimiar", () => {
  it.each([
    ["custo", "1.000", `${R$}1`], // pendência (a): "1.000" não é mil
    ["custo", "1000", `${R$}1000`], // sem separador de milhar na prévia
    ["ctr", " 1,50 ", "1,5%"],
    ["cpc", "7.500000", `${R$}7,5`],
    ["conversoes", "0", "0"],
    ["impressoes", "123456789012.123456", "123456789012,123456"],
  ])("(%s, %j) → %s", (metrica, texto, esperado) => {
    expect(previaLimiar(metrica, texto)).toBe(esperado);
  });

  it.each(["", "  ", "-1", "1.234,5", "1e3", ".5", "1.1234567"])("%j inválido → null", (texto) => {
    expect(previaLimiar("custo", texto)).toBeNull();
  });
});
