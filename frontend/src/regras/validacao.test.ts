// Oráculo: respostas reais do Pydantic (app/api/esquemas.py), colhidas em 15/11/2026 no
// venv do backend por um script temporário que só lê os esquemas (sem banco, sem .env):
// CondicaoEntrada/RegraEntrada.model_validate e RegraEntrada.model_json_schema(). As
// tabelas abaixo foram geradas da saída JSON do script, sem edição à mão.
import { describe, expect, it } from "vitest";
import { normalizarDecimal } from "@/lib/decimal";
import {
  CODIGOS_REFERENCIA,
  LIMITES,
  MENSAGENS,
  METRICAS,
  OPERADORES,
  PADRAO_CODIGO,
  lerLimiar,
  validarRegra,
  type ValoresFormulario,
} from "./validacao";

type Veredito = "aceito" | "recusado";

const ESQUEMA = {"metricas": ["impressoes", "cliques", "custo", "conversoes", "ctr", "cpc"], "operadores": ["<", "<=", ">", ">=", "=="], "codigo": {"minLength": 1, "maxLength": 20, "pattern": "^[A-Za-z0-9_-]+$"}, "nome": {"minLength": 1, "maxLength": 120}, "condicoes": {"minItems": 1, "maxItems": 10}, "codigosReferencia": ["R1", "R2", "R3"]};
const LIMIAR: [string, Veredito, string][] = [
  ["0", "aceito", "0"],
  ["1", "aceito", "1"],
  ["1.5", "aceito", "1.5"],
  ["0.10", "aceito", "0.10"],
  ["007", "aceito", "7"],
  ["1.0000000", "aceito", "1.0000000"],
  ["0.000001", "aceito", "0.000001"],
  ["0.0000001", "recusado", "decimal_max_places"],
  ["123456789012", "aceito", "123456789012"],
  ["1234567890123", "recusado", "decimal_whole_digits"],
  ["123456789012.123456", "aceito", "123456789012.123456"],
  ["123456789012.1234567", "recusado", "decimal_max_digits"],
  ["999999999999.999999", "aceito", "999999999999.999999"],
  ["00000000000001.5", "aceito", "1.5"],
  ["1000000000000", "recusado", "decimal_whole_digits"],
  ["0".repeat(13), "aceito", "0"],
  ["-1", "recusado", "greater_than_equal"],
  ["-0", "aceito", "-0"],
  ["+1", "aceito", "1"],
  ["", "recusado", "decimal_parsing"],
  [" ", "recusado", "decimal_parsing"],
  [".5", "aceito", "0.5"],
  ["5.", "aceito", "5"],
  ["1e3", "aceito", "1E+3"],
  ["1E-7", "recusado", "decimal_max_places"],
  ["1,5", "recusado", "decimal_parsing"],
  [" 1", "aceito", "1"],
  ["1 ", "aceito", "1"],
  ["abc", "recusado", "decimal_parsing"],
  ["1.2.3", "recusado", "decimal_parsing"],
];
const METRICA: [string, Veredito][] = [
  ["impressoes", "aceito"],
  ["cliques", "aceito"],
  ["custo", "aceito"],
  ["conversoes", "aceito"],
  ["ctr", "aceito"],
  ["cpc", "aceito"],
  ["CTR", "recusado"],
  ["custo ", "recusado"],
  ["", "recusado"],
];
const OPERADOR: [string, Veredito][] = [
  ["<", "aceito"],
  ["<=", "aceito"],
  [">", "aceito"],
  [">=", "aceito"],
  ["==", "aceito"],
  ["=", "recusado"],
  ["!=", "recusado"],
  ["=<", "recusado"],
  ["", "recusado"],
];
const CODIGO: [string, Veredito][] = [
  ["R4", "aceito"],
  ["r4", "aceito"],
  ["R_4-a", "aceito"],
  ["A".repeat(20), "aceito"],
  ["A".repeat(21), "recusado"],
  ["", "recusado"],
  ["R 4", "recusado"],
  [" R4", "recusado"],
  ["R4!", "recusado"],
  ["Ré", "recusado"],
  ["R1", "aceito"],
  ["r1", "aceito"],
];
const NOME: [string, Veredito][] = [
  ["a", "aceito"],
  ["a".repeat(120), "aceito"],
  ["a".repeat(121), "recusado"],
  ["", "recusado"],
  ["   ", "aceito"],
  [" CTR ", "aceito"],
  ["é".repeat(120), "aceito"],
  ["😀".repeat(120), "aceito"],
  ["😀".repeat(121), "recusado"],
];
const QUANTIDADE_CONDICOES: [number, Veredito][] = [
  [0, "recusado"],
  [1, "aceito"],
  [10, "aceito"],
  [11, "recusado"],
];

/** Onde a tela é mais rígida de propósito: o Pydantic aceita, a tela recusa. */
const LIMIAR_MAIS_RIGIDO = ["-0", "+1", ".5", "5.", "1e3"];
/** A tela aceita a forma digitada e envia outra, que o Pydantic aceita. */
const LIMIAR_CONVERTIDO: Record<string, string> = { "1,5": "1.5" };
const NOME_MAIS_RIGIDO = ["   "];

const BASE: ValoresFormulario = {
  codigo: "R4",
  nome: "CPC muito alto",
  ativa: true,
  condicoes: [{ metrica: "cpc", operador: ">", limiar: "7.5" }],
};
const CONDICAO = BASE.condicoes[0]!;
const veredito = (valores: ValoresFormulario): Veredito => (validarRegra(valores).ok ? "aceito" : "recusado");
const doOraculo = (entrada: string) => LIMIAR.find(([e]) => e === entrada);

describe("constantes iguais ao esquema do backend", () => {
  it("métricas e operadores", () => {
    expect([...METRICAS]).toEqual(ESQUEMA.metricas);
    expect([...OPERADORES]).toEqual(ESQUEMA.operadores);
  });
  it("código: tamanho e padrão", () => {
    expect(ESQUEMA.codigo.minLength).toBe(1);
    expect(LIMITES.codigo).toBe(ESQUEMA.codigo.maxLength);
    expect(PADRAO_CODIGO.source).toBe(ESQUEMA.codigo.pattern);
  });
  it("nome e quantidade de condições", () => {
    expect(ESQUEMA.nome.minLength).toBe(1);
    expect(LIMITES.nome).toBe(ESQUEMA.nome.maxLength);
    expect([LIMITES.condicoesMin, LIMITES.condicoesMax]).toEqual([ESQUEMA.condicoes.minItems, ESQUEMA.condicoes.maxItems]);
  });
  it("códigos de referência", () => {
    expect([...CODIGOS_REFERENCIA]).toEqual(ESQUEMA.codigosReferencia);
  });
});

describe("limiar contra o oráculo", () => {
  const iguais = LIMIAR.filter(([e]) => !LIMIAR_MAIS_RIGIDO.includes(e) && !Object.hasOwn(LIMIAR_CONVERTIDO, e));

  it.each(iguais)("%j: Pydantic %s (%s)", (entrada, esperado, valor) => {
    const leitura = lerLimiar(entrada);
    expect(leitura.ok ? "aceito" : "recusado").toBe(esperado);
    if (leitura.ok) expect(leitura.valor).toBe(normalizarDecimal(valor));
  });

  it.each(LIMIAR_MAIS_RIGIDO)("%j: o Pydantic aceita e a tela recusa (diferença de propósito)", (entrada) => {
    expect(doOraculo(entrada)?.[1]).toBe("aceito");
    expect(lerLimiar(entrada).ok).toBe(false);
  });

  it.each(Object.entries(LIMIAR_CONVERTIDO))("%j vira %j, que o Pydantic aceita com o mesmo valor", (digitado, enviado) => {
    expect(doOraculo(digitado)?.[1]).toBe("recusado");
    const oraculo = doOraculo(enviado);
    expect(oraculo?.[1]).toBe("aceito");
    expect(lerLimiar(digitado)).toEqual({ ok: true, valor: normalizarDecimal(oraculo![2]) });
  });

  it("nunca envia algo que o Pydantic recusa (fora as conversões)", () => {
    const aceitosRecusados = LIMIAR.filter(([e, v]) => v === "recusado" && lerLimiar(e).ok).map(([e]) => e);
    expect(aceitosRecusados).toEqual(Object.keys(LIMIAR_CONVERTIDO));
  });

  it("mensagem de cada motivo", () => {
    expect(lerLimiar("")).toEqual({ ok: false, erro: MENSAGENS.limiarVazio });
    expect(lerLimiar("-1")).toEqual({ ok: false, erro: MENSAGENS.limiarSinal });
    expect(lerLimiar("abc")).toEqual({ ok: false, erro: MENSAGENS.limiarFormato });
    expect(lerLimiar("0.0000001")).toEqual({ ok: false, erro: MENSAGENS.limiarCasas });
    expect(lerLimiar("1234567890123")).toEqual({ ok: false, erro: MENSAGENS.limiarInteiros });
  });

  it.each(["1.234,5", "1,234.5", "1,2,3"])("%j: separador de milhar não é aceito", (entrada) => {
    expect(lerLimiar(entrada)).toEqual({ ok: false, erro: MENSAGENS.limiarFormato });
  });

  it("vírgula e espaços nas pontas", () => {
    expect(lerLimiar("  0,50 ")).toEqual({ ok: true, valor: "0.5" });
  });
});

describe("métrica e operador contra o oráculo", () => {
  it.each(METRICA)("métrica %j: Pydantic %s", (metrica, esperado) => {
    expect(veredito({ ...BASE, condicoes: [{ ...CONDICAO, metrica }] })).toBe(esperado);
  });
  it.each(OPERADOR)("operador %j: Pydantic %s", (operador, esperado) => {
    expect(veredito({ ...BASE, condicoes: [{ ...CONDICAO, operador }] })).toBe(esperado);
  });
});

describe("código contra o oráculo", () => {
  const referencia = (c: string) => (CODIGOS_REFERENCIA as readonly string[]).includes(c.toUpperCase());

  it.each(CODIGO.filter(([c]) => !referencia(c)))("%j: Pydantic %s", (codigo, esperado) => {
    expect(veredito({ ...BASE, codigo })).toBe(esperado);
  });

  it.each(CODIGO.filter(([c]) => referencia(c)))("%j: o Pydantic aceita; a tela recusa como o serviço (409)", (codigo, esperado) => {
    expect(esperado).toBe("aceito");
    expect(validarRegra({ ...BASE, codigo })).toEqual({ ok: false, erros: { codigo: MENSAGENS.codigoReferencia } });
  });

  it.each(["R1", "R2", "R3", "r2", "r3"])("%j é de referência", (codigo) => {
    expect(validarRegra({ ...BASE, codigo })).toEqual({ ok: false, erros: { codigo: MENSAGENS.codigoReferencia } });
  });
});

describe("nome contra o oráculo", () => {
  it.each(NOME.filter(([n]) => !NOME_MAIS_RIGIDO.includes(n)))("%j: Pydantic %s", (nome, esperado) => {
    expect(veredito({ ...BASE, nome })).toBe(esperado);
  });

  it.each(NOME_MAIS_RIGIDO)("%j: o Pydantic aceita e a tela recusa (diferença de propósito)", (nome) => {
    expect(NOME.find(([n]) => n === nome)?.[1]).toBe("aceito");
    expect(validarRegra({ ...BASE, nome })).toEqual({ ok: false, erros: { nome: MENSAGENS.nomeVazio } });
  });

  it("envia o nome sem espaços nas pontas", () => {
    const resultado = validarRegra({ ...BASE, nome: " CTR " });
    expect(resultado.ok && resultado.corpo.nome).toBe("CTR");
  });
});

describe("quantidade de condições contra o oráculo", () => {
  it.each(QUANTIDADE_CONDICOES)("%i condições: Pydantic %s", (quantidade, esperado) => {
    expect(veredito({ ...BASE, condicoes: Array.from({ length: quantidade }, () => ({ ...CONDICAO })) })).toBe(esperado);
  });
});

describe("corpo enviado e caminho dos erros", () => {
  it("normaliza limiar e nome e mantém o resto", () => {
    expect(
      validarRegra({
        codigo: "R4",
        nome: "  CPC muito alto ",
        ativa: false,
        condicoes: [
          { metrica: "cpc", operador: ">", limiar: " 7,50 " },
          { metrica: "ctr", operador: "<", limiar: "0,5" },
        ],
      }),
    ).toEqual({
      ok: true,
      corpo: {
        codigo: "R4",
        nome: "CPC muito alto",
        ativa: false,
        condicoes: [
          { metrica: "cpc", operador: ">", limiar: "7.5" },
          { metrica: "ctr", operador: "<", limiar: "0.5" },
        ],
      },
    });
  });

  it("cada erro aponta o seu campo", () => {
    expect(
      validarRegra({ ...BASE, codigo: "", condicoes: [CONDICAO, { metrica: "ctr", operador: "<", limiar: "-1" }] }),
    ).toEqual({ ok: false, erros: { codigo: MENSAGENS.codigoVazio, "condicoes.1.limiar": MENSAGENS.limiarSinal } });
  });
});
