import { describe, expect, it } from "vitest";
import { diasEntre } from "@/visao-geral/dados";
import {
  type Campanha,
  celulaCpc,
  celulaCtr,
  celulaDecimal,
  celulaInteiro,
  celulaMoeda,
  descricaoPeriodo,
  encontrarCampanha,
  formatarOrcamento,
  lerIdCampanha,
  mensagemSincronizacao,
  rotuloOrigem,
  textoAcessivel,
  textoSincronizacao,
} from "./dados";

const R$ = "R$\u00A0";

// Banco limen (14/11/2026): SELECT id, nome, status, orcamento_micros FROM campanha ORDER BY nome;
const CAMPANHAS: Campanha[] = [
  { id: 1, google_campaign_id: 24444020070, nome: "Limen A - Pesquisa", status: "ENABLED", orcamento_micros: 50000000, sincronizada_em: "2026-11-12T19:29:24.123456+00:00" },
  { id: 3, google_campaign_id: 24464752468, nome: "Limen B - Pesquisa", status: "ENABLED", orcamento_micros: 80000000, sincronizada_em: "2026-11-12T19:29:24.123456+00:00" },
  { id: 2, google_campaign_id: 24458906837, nome: "Limen C - Pesquisa", status: "PAUSED", orcamento_micros: 40000000, sincronizada_em: "2026-11-12T19:29:24.123456+00:00" },
];

// Banco limen, campanha A, 4 primeiros dias: ctr/cpc como a API manda (texto da view) e
// o esperado tirado de round(ctr, 2) e round(cpc, 2) no próprio PostgreSQL.
const LINHAS_REAIS = [
  { data: "2026-10-13", impressoes: 7938, cliques: 431, custo: "4710.83", conversoes: "6.000000", ctr: "5.4295792391030486", cpc: "10.9300000000000000", esperado: { ctr: "5,43%", cpc: `${R$}10,93`, custo: `${R$}4.710,83`, impressoes: "7.938", conversoes: "6" } },
  { data: "2026-10-14", impressoes: 5804, cliques: 280, custo: "515.20", conversoes: "7.000000", ctr: "4.8242591316333563", cpc: "1.8400000000000000", esperado: { ctr: "4,82%", cpc: `${R$}1,84`, custo: `${R$}515,20`, impressoes: "5.804", conversoes: "7" } },
  { data: "2026-10-15", impressoes: 3538, cliques: 90, custo: "205.20", conversoes: "7.000000", ctr: "2.5438100621820237", cpc: "2.2800000000000000", esperado: { ctr: "2,54%", cpc: `${R$}2,28`, custo: `${R$}205,20`, impressoes: "3.538", conversoes: "7" } },
  { data: "2026-10-16", impressoes: 9932, cliques: 472, custo: "1080.88", conversoes: "2.000000", ctr: "4.7523157470801450", cpc: "2.2900000000000000", esperado: { ctr: "4,75%", cpc: `${R$}2,29`, custo: `${R$}1.080,88`, impressoes: "9.932", conversoes: "2" } },
];

describe("lerIdCampanha", () => {
  it.each([
    ["1", 1],
    ["42", 42],
    ["9007199254740991", 9007199254740991],
  ])("%j → %i", (texto, id) => {
    expect(lerIdCampanha(texto)).toBe(id);
  });

  it.each([undefined, "", "abc", "0", "-1", "1.5", "007", " 1", "1e3", "0x1", "9007199254740993"])(
    "%j → null (não chama a API)",
    (texto) => {
      expect(lerIdCampanha(texto)).toBeNull();
    },
  );
});

describe("encontrarCampanha", () => {
  it("acha pelo id do banco, não pela posição", () => {
    expect(encontrarCampanha(CAMPANHAS, 3)?.nome).toBe("Limen B - Pesquisa");
    expect(encontrarCampanha(CAMPANHAS, 2)?.nome).toBe("Limen C - Pesquisa");
  });

  it("id que não está na lista → null", () => {
    expect(encontrarCampanha(CAMPANHAS, 99)).toBeNull();
  });
});

describe("formatarOrcamento", () => {
  it("os três orçamentos reais (A, B, C)", () => {
    expect(CAMPANHAS.map((c) => formatarOrcamento(c.orcamento_micros))).toEqual([`${R$}50,00`, `${R$}80,00`, `${R$}40,00`]);
  });

  it.each([
    [0, `${R$}0,00`], // orçamento zero existe e é diferente de ausente
    [1234567, `${R$}1,23`],
    [1005000, `${R$}1,01`], // 1,005: float daria 1,00 (toFixed); o round() do PostgreSQL dá 1,01
    [123456789000000, `${R$}123.456.789,00`],
  ])("%i micros → %s", (micros, esperado) => {
    expect(formatarOrcamento(micros)).toBe(esperado);
  });

  it("null (sem orçamento vinculado) não vira R$ 0,00", () => {
    expect(formatarOrcamento(null)).toBe("sem orçamento");
  });

  it.each([-1, 1.5, Number.NaN, 2 ** 53])("%s → orçamento inválido", (micros) => {
    expect(formatarOrcamento(micros)).toBe("orçamento inválido");
  });
});

describe("textoSincronizacao", () => {
  it("hora local a partir do UTC da API (Fortaleza = UTC−3)", () => {
    expect(textoSincronizacao(CAMPANHAS[0]!.sincronizada_em, "America/Fortaleza")).toBe("12/11/2026 às 16:29");
  });

  it("null → nunca", () => {
    expect(textoSincronizacao(null)).toBe("nunca");
  });
});

describe("mensagemSincronizacao", () => {
  it.each([
    [0, "Nenhuma campanha encontrada no Google Ads."],
    [1, "1 campanha sincronizada."],
    [3, "3 campanhas sincronizadas."],
    [1000, "1.000 campanhas sincronizadas."],
  ])("%i → %s", (n, esperado) => {
    expect(mensagemSincronizacao(n)).toBe(esperado);
  });
});

describe("rotuloOrigem", () => {
  it.each([
    ["sintetica", "sintética"],
    ["google_ads", "Google Ads"],
    ["outra", "outra"],
    ["toString", "toString"],
    ["__proto__", "__proto__"],
  ])("%s → %s", (origem, esperado) => {
    expect(rotuloOrigem(origem)).toBe(esperado);
  });
});

describe("descricaoPeriodo", () => {
  const trintaDias = diasEntre("2026-10-13", "2026-11-11").map((data) => ({ data }));

  it("os 30 dias do IN-02b", () => {
    expect(descricaoPeriodo(trintaDias)).toBe("30 dias · 13/10 a 11/11/2026");
  });

  it("não depende da ordem que a API mandou", () => {
    expect(descricaoPeriodo([...trintaDias].reverse())).toBe("30 dias · 13/10 a 11/11/2026");
  });

  it("um dia, virada de ano e lista vazia", () => {
    expect(descricaoPeriodo([{ data: "2026-11-11" }])).toBe("1 dia · 11/11/2026");
    expect(descricaoPeriodo([{ data: "2026-01-01" }, { data: "2025-12-31" }])).toBe("2 dias · 31/12/2025 a 01/01/2026");
    expect(descricaoPeriodo([])).toBeNull();
  });
});

describe("células com as linhas reais da campanha A", () => {
  it.each(LINHAS_REAIS)("$data", (linha) => {
    expect({
      ctr: celulaCtr(linha).texto,
      cpc: celulaCpc(linha).texto,
      custo: celulaMoeda(linha.custo).texto,
      impressoes: celulaInteiro(linha.impressoes).texto,
      conversoes: celulaDecimal(linha.conversoes).texto,
    }).toEqual(linha.esperado);
  });
});

describe("ausente ≠ zero nas células", () => {
  it("ausente vira — com descrição; zero continua zero", () => {
    expect(celulaInteiro(null)).toEqual({ texto: "—", descricao: "sem dado" });
    expect(celulaMoeda(null)).toEqual({ texto: "—", descricao: "sem dado" });
    expect(celulaDecimal(null)).toEqual({ texto: "—", descricao: "sem dado" });
    expect(celulaInteiro(0)).toEqual({ texto: "0", descricao: null });
    expect(celulaMoeda("0.00")).toEqual({ texto: `${R$}0,00`, descricao: null });
    expect(celulaDecimal("0.000000")).toEqual({ texto: "0", descricao: null });
  });
});

describe("CTR e CPC indefinidos (mesma ordem do motor)", () => {
  it("CTR zero chega como 0E-16 e é 0,00%, não N/A", () => {
    expect(celulaCtr({ ctr: "0E-16", impressoes: 100, cliques: 0 })).toEqual({ texto: "0,00%", descricao: null });
  });

  it.each([
    [null, null, "indefinido: impressões e cliques ausentes"],
    [null, 5, "indefinido: impressões ausentes"],
    [100, null, "indefinido: cliques ausentes"],
    [0, null, "indefinido: cliques ausentes"], // o motor testa ausência antes do zero
    [0, 0, "indefinido: 0 impressões"],
    [0, 5, "indefinido: 0 impressões"],
  ])("CTR com impressões %s e cliques %s → N/A (%s)", (impressoes, cliques, descricao) => {
    expect(celulaCtr({ ctr: null, impressoes, cliques })).toEqual({ texto: "N/A", descricao });
  });

  it.each([
    [null, null, "indefinido: custo e cliques ausentes"],
    [null, 5, "indefinido: custo ausente"],
    ["10.00", null, "indefinido: cliques ausentes"],
    ["0.00", null, "indefinido: cliques ausentes"],
    ["10.00", 0, "indefinido: 0 cliques"],
  ])("CPC com custo %s e cliques %s → N/A (%s)", (custo, cliques, descricao) => {
    expect(celulaCpc({ cpc: null, custo, cliques })).toEqual({ texto: "N/A", descricao });
  });

  it("cliques 0: CTR é 0,00% e CPC é N/A (a mesma linha tem os dois casos)", () => {
    const linha = { impressoes: 100, cliques: 0, custo: "10.00", ctr: "0E-16", cpc: null };
    expect([celulaCtr(linha).texto, celulaCpc(linha).texto]).toEqual(["0,00%", "N/A"]);
  });
});

describe("textoAcessivel (o que o leitor de tela ouve)", () => {
  it("valor definido: o próprio texto", () => {
    expect(textoAcessivel(celulaInteiro(1234))).toBe("1.234");
    expect(textoAcessivel(celulaCtr({ ctr: "0E-16", impressoes: 100, cliques: 0 }))).toBe("0,00%");
  });

  it("ausente: 'sem dado' no lugar de —", () => {
    expect(textoAcessivel(celulaInteiro(null))).toBe("sem dado");
    expect(textoAcessivel(celulaMoeda(null))).toBe("sem dado");
  });

  it("indefinido: N/A seguido do motivo", () => {
    expect(textoAcessivel(celulaCpc({ cpc: null, custo: "10.00", cliques: 0 }))).toBe("N/A, indefinido: 0 cliques");
    expect(textoAcessivel(celulaCtr({ ctr: null, impressoes: null, cliques: 5 }))).toBe("N/A, indefinido: impressões ausentes");
  });
});
