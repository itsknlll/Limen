// Oráculo: respostas reais do Pydantic (AvaliacaoEntrada em app/api/esquemas.py),
// colhidas em 15/11/2026 no venv do backend por um script temporário que só lê os
// esquemas (sem banco, sem .env). Tabelas geradas da saída JSON, sem edição à mão.
import { describe, expect, it } from "vitest";
import { ehDataIso } from "@/visao-geral/dados";
import { MENSAGENS_PEDIDO, montarPedidoAvaliacao, type CorpoAvaliacao, type FormularioAvaliacao } from "./pedido";

type Veredito = "aceito" | "recusado";

const DATA: [string, Veredito][] = [
  ["2026-10-13", "aceito"],
  ["2024-02-29", "aceito"],
  ["2026-02-29", "recusado"],
  ["2026-13-01", "recusado"],
  ["2026-11-31", "recusado"],
  ["2026-00-10", "recusado"],
  ["2026-1-5", "recusado"],
  ["20261105", "recusado"],
  ["2026-11-11T00:00:00", "aceito"],
  ["", "recusado"],
  ["0000-01-01", "recusado"],
  ["0001-01-01", "aceito"],
  ["9999-12-31", "aceito"],
];
const AVALIACAO: [Record<string, unknown>, Veredito, Record<string, unknown> | null][] = [
  [{}, "aceito", {"campanha_id": null, "inicio": null, "fim": null, "incluir_pausadas": false}],
  [{"incluir_pausadas": true}, "aceito", {"campanha_id": null, "inicio": null, "fim": null, "incluir_pausadas": true}],
  [{"incluir_pausadas": false}, "aceito", {"campanha_id": null, "inicio": null, "fim": null, "incluir_pausadas": false}],
  [{"campanha_id": 1}, "aceito", {"campanha_id": 1, "inicio": null, "fim": null, "incluir_pausadas": false}],
  [{"campanha_id": "1"}, "aceito", {"campanha_id": 1, "inicio": null, "fim": null, "incluir_pausadas": false}],
  [{"campanha_id": 0}, "aceito", {"campanha_id": 0, "inicio": null, "fim": null, "incluir_pausadas": false}],
  [{"campanha_id": -1}, "aceito", {"campanha_id": -1, "inicio": null, "fim": null, "incluir_pausadas": false}],
  [{"campanha_id": 1.5}, "recusado", null],
  [{"campanha_id": null, "inicio": null, "fim": null}, "aceito", {"campanha_id": null, "inicio": null, "fim": null, "incluir_pausadas": false}],
  [{"inicio": "2026-10-13", "fim": "2026-11-11"}, "aceito", {"campanha_id": null, "inicio": "2026-10-13", "fim": "2026-11-11", "incluir_pausadas": false}],
  [{"inicio": "2026-11-11", "fim": "2026-11-11"}, "aceito", {"campanha_id": null, "inicio": "2026-11-11", "fim": "2026-11-11", "incluir_pausadas": false}],
  [{"inicio": "2026-11-12", "fim": "2026-11-11"}, "recusado", null],
  [{"inicio": "2026-10-13"}, "aceito", {"campanha_id": null, "inicio": "2026-10-13", "fim": null, "incluir_pausadas": false}],
  [{"fim": "2026-11-11"}, "aceito", {"campanha_id": null, "inicio": null, "fim": "2026-11-11", "incluir_pausadas": false}],
  [{"inicio": "2026-12-31", "fim": "2027-01-01"}, "aceito", {"campanha_id": null, "inicio": "2026-12-31", "fim": "2027-01-01", "incluir_pausadas": false}],
  [{"inicio": "2027-01-01", "fim": "2026-12-31"}, "recusado", null],
];

/** Data que o Pydantic aceita e a tela recusa de propósito (só "AAAA-MM-DD"). */
const DATA_MAIS_RIGIDA = ["2026-11-11T00:00:00"];

const CAMPANHAS = [
  { id: 1, nome: "A", status: "ENABLED" },
  { id: 2, nome: "B", status: "ENABLED" },
  { id: 3, nome: "C", status: "PAUSED" },
  { id: 4, nome: "D", status: "REMOVED" },
];
const VAZIO: FormularioAvaliacao = { campanhaId: "", inicio: "", fim: "", incluirPausadas: false };
const montar = (form: Partial<FormularioAvaliacao>) => montarPedidoAvaliacao({ ...VAZIO, ...form }, CAMPANHAS);

/** O corpo como o Pydantic o completa (ausente → null), para comparar com o `valor` do oráculo. */
const comoPydantic = (c: CorpoAvaliacao) => ({
  campanha_id: c.campanha_id ?? null,
  inicio: c.inicio ?? null,
  fim: c.fim ?? null,
  incluir_pausadas: c.incluir_pausadas,
});
const oraculoDe = (entrada: Record<string, unknown>) =>
  AVALIACAO.find(([e]) => JSON.stringify(e) === JSON.stringify(entrada));

describe("ehDataIso contra o oráculo", () => {
  it.each(DATA.filter(([d]) => !DATA_MAIS_RIGIDA.includes(d)))("%j: Pydantic %s", (data, esperado) => {
    expect(ehDataIso(data) ? "aceito" : "recusado").toBe(esperado);
  });
  it.each(DATA_MAIS_RIGIDA)("%j: o Pydantic aceita e a tela recusa (diferença de propósito)", (data) => {
    expect(DATA.find(([d]) => d === data)?.[1]).toBe("aceito");
    expect(ehDataIso(data)).toBe(false);
  });
});

describe("pedido aceito: o corpo enviado é aceito pelo Pydantic com o mesmo valor", () => {
  const casos: [string, Partial<FormularioAvaliacao>, CorpoAvaliacao][] = [
    ["formulário vazio", {}, { incluir_pausadas: false }],
    ["incluir pausadas", { incluirPausadas: true }, { incluir_pausadas: true }],
    ["uma campanha", { campanhaId: "1" }, { campanha_id: 1, incluir_pausadas: false }],
    ["período", { inicio: "2026-10-13", fim: "2026-11-11" }, { inicio: "2026-10-13", fim: "2026-11-11", incluir_pausadas: false }],
    ["início = fim", { inicio: "2026-11-11", fim: "2026-11-11" }, { inicio: "2026-11-11", fim: "2026-11-11", incluir_pausadas: false }],
    ["só início", { inicio: "2026-10-13" }, { inicio: "2026-10-13", incluir_pausadas: false }],
    ["só fim", { fim: "2026-11-11" }, { fim: "2026-11-11", incluir_pausadas: false }],
    ["virada de ano", { inicio: "2026-12-31", fim: "2027-01-01" }, { inicio: "2026-12-31", fim: "2027-01-01", incluir_pausadas: false }],
  ];

  it.each(casos)("%s", (_, form, corpo) => {
    const resultado = montar(form);
    // Corpo exato: campo vazio omitido, incluir_pausadas sempre presente.
    expect(resultado).toEqual({ ok: true, corpo, aviso: null });
    const valor = comoPydantic(corpo);
    expect(AVALIACAO.some(([, v, saida]) => v === "aceito" && JSON.stringify(saida) === JSON.stringify(valor))).toBe(true);
  });

  it("incluir_pausadas vai explícito mesmo quando falso", () => {
    const resultado = montar({});
    expect(resultado.ok && Object.hasOwn(resultado.corpo, "incluir_pausadas")).toBe(true);
  });
});

describe("pedido recusado", () => {
  it.each([
    ["2026-11-12", "2026-11-11"],
    ["2027-01-01", "2026-12-31"],
  ])("período %s a %s: o Pydantic recusa, e a tela também", (inicio, fim) => {
    expect(oraculoDe({ inicio, fim })?.[1]).toBe("recusado");
    expect(montar({ inicio, fim })).toEqual({ ok: false, erros: { fim: MENSAGENS_PEDIDO.periodo } });
  });

  it.each(["2026-02-29", "2026-11-11T00:00:00", "11/11/2026"])("data inválida %j", (inicio) => {
    expect(montar({ inicio })).toEqual({ ok: false, erros: { inicio: MENSAGENS_PEDIDO.data } });
  });

  it.each(["99", "0", "-1", "01", "1.5", "abc"])("campanha %j fora da lista", (campanhaId) => {
    expect(montar({ campanhaId })).toEqual({ ok: false, erros: { campanhaId: MENSAGENS_PEDIDO.campanha } });
  });

  it("0 e -1: o Pydantic aceita; a tela só envia ids da lista (mais rígida por construção)", () => {
    expect(oraculoDe({ campanha_id: 0 })?.[1]).toBe("aceito");
    expect(oraculoDe({ campanha_id: -1 })?.[1]).toBe("aceito");
  });
});

describe("aviso de campanha não ativa", () => {
  it("pausada sem incluir pausadas", () => {
    const resultado = montar({ campanhaId: "3" });
    expect(resultado.ok && resultado.aviso).toBe(
      'A campanha C está pausada: sem "Incluir campanhas pausadas", nenhum registro dela será avaliado.',
    );
  });
  it("removida sem incluir pausadas", () => {
    const resultado = montar({ campanhaId: "4" });
    expect(resultado.ok && resultado.aviso).toContain("está removida");
  });
  it.each([[{ campanhaId: "3", incluirPausadas: true }], [{ campanhaId: "1" }], [{}]])("sem aviso: %j", (form) => {
    const resultado = montar(form);
    expect(resultado.ok && resultado.aviso).toBe(null);
  });
});
