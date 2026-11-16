// Testes de historico.ts. Oráculo: as linhas reais do banco limen (15/11/2026), lidas com
// uma consulta só de leitura (transação READ ONLY, default_transaction_read_only=on), um
// único usuário com avaliações (count(DISTINCT usuario_id) = 1):
//
//   SELECT id,
//          to_char(iniciada_em AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS iniciada_em,
//          to_char(iniciada_em AT TIME ZONE 'America/Fortaleza', 'DD/MM/YYYY "às" HH24:MI') AS data_fortaleza,
//          incluir_pausadas, campanha_id, inicio, fim,
//          registros_avaliados, registros_rejeitados, alertas_gerados, alertas_ja_existentes
//   FROM avaliacao ORDER BY iniciada_em DESC, id DESC LIMIT 50;
//   SELECT id, nome, status FROM campanha ORDER BY id;
//
// A coluna Data é conferida contra data_fortaleza (calculada pelo PostgreSQL, não pelo Intl).
// As duas avaliações reais são do IN-02b, anteriores à migração 0003 (parâmetros NULL); os
// casos depois da 0003 são sintéticos, montados sobre elas.

import { describe, expect, it } from "vitest";
import {
  celulasHistorico,
  NAO_REGISTRADO,
  textoResultado,
  textoStatus,
  type CelulasHistorico,
} from "./historico";

const FUSO = "America/Fortaleza";

// Saída da consulta, na ordem de GET /avaliacoes.
const REAIS = [
  {
    id: 2,
    iniciada_em: "2026-11-13T11:18:51.163734Z",
    data_fortaleza: "13/11/2026 às 08:18",
    incluir_pausadas: null,
    campanha_id: null,
    inicio: null,
    fim: null,
    registros_avaliados: 90,
    registros_rejeitados: 0,
    alertas_gerados: 9,
    alertas_ja_existentes: 18,
  },
  {
    id: 1,
    iniciada_em: "2026-11-13T11:16:41.333793Z",
    data_fortaleza: "13/11/2026 às 08:16",
    incluir_pausadas: null,
    campanha_id: null,
    inicio: null,
    fim: null,
    registros_avaliados: 60,
    registros_rejeitados: 0,
    alertas_gerados: 18,
    alertas_ja_existentes: 0,
  },
] as const;

// Campanhas reais (id interno, nome). O id 2 é a C: procurar pela posição na lista erraria.
const CAMPANHAS = [
  { id: 1, nome: "Limen A - Pesquisa" },
  { id: 2, nome: "Limen C - Pesquisa" },
  { id: 3, nome: "Limen B - Pesquisa" },
] as const;

const [REAL_2, REAL_1] = REAIS;

/** Avaliação depois da 0003: a nº 2 real com parâmetros registrados. */
function depois0003(parametros: {
  incluir_pausadas: boolean;
  campanha_id?: number | null;
  inicio?: string | null;
  fim?: string | null;
}) {
  return { ...REAL_2, campanha_id: null, inicio: null, fim: null, ...parametros };
}

describe("celulasHistorico — linhas reais (anteriores à 0003)", () => {
  it.each(REAIS)("avaliação nº $id: tudo como o banco, parâmetros 'não registrado'", (linha) => {
    expect(celulasHistorico(linha, CAMPANHAS, FUSO)).toEqual<CelulasHistorico>({
      data: linha.data_fortaleza,
      periodo: NAO_REGISTRADO,
      campanha: NAO_REGISTRADO,
      pausadas: NAO_REGISTRADO,
      alertasGerados: String(linha.alertas_gerados),
      alertasJaExistentes: String(linha.alertas_ja_existentes),
      parametrosAusentes: true,
    });
  });

  it("'não registrado' também sem a lista de campanhas", () => {
    const c = celulasHistorico(REAL_2, undefined, FUSO);
    expect([c.periodo, c.campanha, c.pausadas]).toEqual([NAO_REGISTRADO, NAO_REGISTRADO, NAO_REGISTRADO]);
  });

  it("alertas novos e já existentes ficam separados (9 e 18, nunca 27)", () => {
    const c = celulasHistorico(REAL_2, CAMPANHAS, FUSO);
    expect(c.alertasGerados).toBe("9");
    expect(c.alertasJaExistentes).toBe("18");
  });
});

describe("celulasHistorico — depois da 0003 (sintéticos)", () => {
  it("incluir_pausadas false é 'não', e não 'não registrado'", () => {
    const c = celulasHistorico(depois0003({ incluir_pausadas: false }), CAMPANHAS, FUSO);
    expect(c.pausadas).toBe("não");
    expect(c.parametrosAusentes).toBe(false);
  });

  it("incluir_pausadas true é 'sim'", () => {
    expect(celulasHistorico(depois0003({ incluir_pausadas: true }), CAMPANHAS, FUSO).pausadas).toBe("sim");
  });

  it("campanha_id NULL depois da 0003 é 'todas'", () => {
    const c = celulasHistorico(depois0003({ incluir_pausadas: false }), CAMPANHAS, FUSO);
    expect(c.campanha).toBe("todas");
    expect(celulasHistorico(depois0003({ incluir_pausadas: false }), undefined, FUSO).campanha).toBe("todas");
  });

  it.each([
    [1, "Limen A - Pesquisa"],
    [2, "Limen C - Pesquisa"],
    [3, "Limen B - Pesquisa"],
  ])("campanha_id %i → %s (pelo id, não pela posição)", (id, nome) => {
    const c = celulasHistorico(depois0003({ incluir_pausadas: true, campanha_id: id }), CAMPANHAS, FUSO);
    expect(c.campanha).toBe(nome);
  });

  it("campanha fora da lista mostra o número e diz que está fora", () => {
    const c = celulasHistorico(depois0003({ incluir_pausadas: true, campanha_id: 99 }), CAMPANHAS, FUSO);
    expect(c.campanha).toBe("campanha nº 99 (fora da lista)");
  });

  it("sem a lista (não carregou), mostra só o número", () => {
    const c = celulasHistorico(depois0003({ incluir_pausadas: true, campanha_id: 2 }), undefined, FUSO);
    expect(c.campanha).toBe("campanha nº 2");
  });

  it.each([
    [null, null, "período todo"],
    ["2026-10-13", "2026-11-11", "13/10 a 11/11/2026"],
    ["2026-10-17", "2026-10-17", "17/10/2026"],
    ["2025-12-28", "2026-01-03", "28/12/2025 a 03/01/2026"],
    ["2026-10-13", null, "a partir de 13/10/2026"],
    [null, "2026-11-11", "até 11/11/2026"],
  ])("período %s a %s → %s", (inicio, fim, esperado) => {
    const c = celulasHistorico(depois0003({ incluir_pausadas: false, inicio, fim }), CAMPANHAS, FUSO);
    expect(c.periodo).toBe(esperado);
  });

  it("contagens com separador de milhar", () => {
    const linha = { ...depois0003({ incluir_pausadas: false }), alertas_gerados: 1234, alertas_ja_existentes: 10000 };
    const c = celulasHistorico(linha, CAMPANHAS, FUSO);
    expect([c.alertasGerados, c.alertasJaExistentes]).toEqual(["1.234", "10.000"]);
  });
});

describe("textoResultado", () => {
  it("avaliação nº 1 real (só ativas, primeira execução)", () => {
    expect(textoResultado(REAL_1)).toBe(
      "Avaliação nº 1 concluída: 18 alertas novos. 60 registros avaliados, 0 rejeitados.",
    );
  });

  it("avaliação nº 2 real (com pausadas, depois da primeira)", () => {
    expect(textoResultado(REAL_2)).toBe(
      "Avaliação nº 2 concluída: 9 alertas novos, 18 já existiam. 90 registros avaliados, 0 rejeitados.",
    );
  });

  it("zero alertas novos não parece falha", () => {
    const s = { ...REAL_2, id: 3, alertas_gerados: 0, alertas_ja_existentes: 27 };
    expect(textoResultado(s)).toBe(
      "Avaliação nº 3 concluída: nenhum alerta novo, 27 já existiam. 90 registros avaliados, 0 rejeitados.",
    );
  });

  it("singulares", () => {
    const s = { id: 4, alertas_gerados: 1, alertas_ja_existentes: 1, registros_avaliados: 1, registros_rejeitados: 1 };
    expect(textoResultado(s)).toBe(
      "Avaliação nº 4 concluída: 1 alerta novo, 1 já existia. 1 registro avaliado, 1 rejeitado.",
    );
  });

  it("zero registros avaliados ganha a dica", () => {
    const s = { id: 5, alertas_gerados: 0, alertas_ja_existentes: 0, registros_avaliados: 0, registros_rejeitados: 0 };
    expect(textoResultado(s)).toBe(
      "Avaliação nº 5 concluída: nenhum alerta novo. 0 registros avaliados, 0 rejeitados." +
        " Nenhum registro foi avaliado: confira o período e se a campanha está pausada.",
    );
  });

  it("contagens com separador de milhar", () => {
    const s = { id: 6, alertas_gerados: 0, alertas_ja_existentes: 0, registros_avaliados: 10000, registros_rejeitados: 1234 };
    expect(textoResultado(s)).toContain("10.000 registros avaliados, 1.234 rejeitados.");
  });
});

describe("textoStatus", () => {
  it("ocioso: vazio (a região existe, sem texto)", () => {
    expect(textoStatus({ fase: "ocioso" })).toBe("");
  });

  it("executando", () => {
    expect(textoStatus({ fase: "executando" })).toBe("Executando a avaliação…");
  });

  it("concluída: a mesma frase do resultado", () => {
    expect(textoStatus({ fase: "concluida", saida: REAL_2 })).toBe(textoResultado(REAL_2));
  });

  it("erro", () => {
    expect(textoStatus({ fase: "erro" })).toBe("A avaliação não foi executada.");
  });
});
