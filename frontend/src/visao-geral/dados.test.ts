import { beforeAll, describe, expect, it } from "vitest";
import {
  codigoNoTopo,
  codigosDaSerie,
  descricaoGrafico,
  diasEntre,
  estadoVazio,
  serieAlertasPorDia,
  textoAlertas,
  textoCampanhas,
  textoDuracao,
  textoMetricas,
  textoParametros,
  textoRegras,
  type Resumo,
} from "./dados";

// Fuso do processo em UTC-3: se diasEntre passar a usar `new Date("2026-10-13")`
// (meia-noite UTC), o dia sai 12/10 e os testes reprovam, em qualquer máquina.
beforeAll(() => {
  process.env.TZ = "America/Fortaleza";
});

// GET /resumo com os dados do banco limen em 14/11/2026 (IN-02b + as duas avaliações):
// 27 alertas em 20 dias, 9 por regra, de 2 avaliações; métricas de 13/10 a 11/11.
// Tipada com o contrato gerado (ResumoSaida): se a API mudar, o typecheck reprova aqui.
// Anotação e não `satisfies`: com `satisfies` o tipo literal de por_dia vira uma união
// ({ R2: number; R3?: undefined } | …) que não cabe em { [codigo]: number }.
const RESUMO_LIMEN: Resumo = {
  campanhas: { total: 3, por_status: { ENABLED: 2, PAUSED: 1, REMOVED: 0, UNKNOWN: 0 } },
  regras: { total: 3, ativas: 3 },
  metricas: { registros: 90, inicio: "2026-10-13", fim: "2026-11-11", por_origem: { sintetica: 90, google_ads: 0 } },
  alertas: {
    total: 27,
    avaliacoes: 2,
    por_regra: [
      { regra_id: 1, codigo: "R1", nome: "CTR baixo", ativa: true, total: 9 },
      { regra_id: 2, codigo: "R2", nome: "CPC alto", ativa: true, total: 9 },
      { regra_id: 3, codigo: "R3", nome: "Custo sem conversão", ativa: true, total: 9 },
    ],
    por_dia: [
      { data: "2026-10-13", por_regra: { R2: 1 } },
      { data: "2026-10-14", por_regra: { R3: 1 } },
      { data: "2026-10-16", por_regra: { R2: 1 } },
      { data: "2026-10-17", por_regra: { R1: 2, R2: 1 } },
      { data: "2026-10-19", por_regra: { R2: 1 } },
      { data: "2026-10-20", por_regra: { R3: 1 } },
      { data: "2026-10-22", por_regra: { R2: 1 } },
      { data: "2026-10-27", por_regra: { R2: 1, R3: 1 } },
      { data: "2026-10-28", por_regra: { R1: 1 } },
      { data: "2026-10-30", por_regra: { R3: 1 } },
      { data: "2026-10-31", por_regra: { R1: 2 } },
      { data: "2026-11-01", por_regra: { R2: 2, R3: 1 } },
      { data: "2026-11-02", por_regra: { R3: 1 } },
      { data: "2026-11-05", por_regra: { R3: 1 } },
      { data: "2026-11-06", por_regra: { R1: 1 } },
      { data: "2026-11-07", por_regra: { R1: 1 } },
      { data: "2026-11-08", por_regra: { R1: 1 } },
      { data: "2026-11-09", por_regra: { R3: 1 } },
      { data: "2026-11-10", por_regra: { R2: 1, R3: 1 } },
      { data: "2026-11-11", por_regra: { R1: 1 } },
    ],
  },
  ultima_avaliacao: {
    id: 2,
    iniciada_em: "2026-11-13T11:18:51.163734Z",
    concluida_em: "2026-11-13T11:18:51.173509Z",
    registros_avaliados: 90,
    registros_rejeitados: 0,
    alertas_gerados: 9,
    alertas_ja_existentes: 18,
    duracao_motor_ms: "0.870",
    incluir_pausadas: null,
    campanha_id: null,
    inicio: null,
    fim: null,
  },
};

const comAlertas = (alertas: Partial<Resumo["alertas"]>): Resumo => ({
  ...RESUMO_LIMEN,
  alertas: { ...RESUMO_LIMEN.alertas, ...alertas },
});

describe("diasEntre", () => {
  it("13/10 a 11/11/2026 → 30 dias, do primeiro ao último", () => {
    const dias = diasEntre("2026-10-13", "2026-11-11");
    expect(dias).toHaveLength(30);
    expect(dias[0]).toBe("2026-10-13");
    expect(dias.at(-1)).toBe("2026-11-11");
  });

  it.each([
    ["virada de mês (31 dias)", "2026-10-30", "2026-11-02", ["2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"]],
    ["virada de mês (30 dias)", "2026-11-29", "2026-12-01", ["2026-11-29", "2026-11-30", "2026-12-01"]],
    ["virada de ano", "2026-12-30", "2027-01-02", ["2026-12-30", "2026-12-31", "2027-01-01", "2027-01-02"]],
    ["fevereiro bissexto", "2028-02-28", "2028-03-01", ["2028-02-28", "2028-02-29", "2028-03-01"]],
    ["fevereiro comum", "2026-02-28", "2026-03-01", ["2026-02-28", "2026-03-01"]],
    ["2000 é bissexto (÷400)", "2000-02-28", "2000-03-01", ["2000-02-28", "2000-02-29", "2000-03-01"]],
    ["2100 não é bissexto (÷100)", "2100-02-28", "2100-03-01", ["2100-02-28", "2100-03-01"]],
    ["um dia só", "2026-11-11", "2026-11-11", ["2026-11-11"]],
  ])("%s", (_, inicio, fim, esperado) => {
    expect(diasEntre(inicio, fim)).toEqual(esperado);
  });

  it("início depois do fim → []", () => {
    expect(diasEntre("2026-11-11", "2026-10-13")).toEqual([]);
  });

  it.each(["2026-13-01", "2026-02-30", "11/11/2026", "2026-11-1", ""])("data inválida %j lança erro", (data) => {
    expect(() => diasEntre(data, "2026-12-31")).toThrow();
    expect(() => diasEntre("2026-01-01", data)).toThrow();
  });
});

describe("serieAlertasPorDia", () => {
  const { alertas, metricas } = RESUMO_LIMEN;
  const codigos = codigosDaSerie(alertas.por_regra, alertas.por_dia);
  const serie = serieAlertasPorDia(alertas.por_dia, metricas.inicio, metricas.fim, codigos);

  it("um ponto por dia do período das métricas, em ordem e sem buracos", () => {
    expect(serie.map((p) => p.data)).toEqual(diasEntre("2026-10-13", "2026-11-11"));
  });

  it("preenche com 0 os 10 dias sem alerta", () => {
    const vazios = serie.filter((p) => p.total === 0);
    expect(vazios).toHaveLength(10);
    for (const p of vazios) expect(p.valores).toEqual({ R1: 0, R2: 0, R3: 0 });
  });

  it("todo ponto tem todas as regras", () => {
    for (const p of serie) expect(Object.keys(p.valores)).toEqual(["R1", "R2", "R3"]);
  });

  // Invariantes (oráculo): a série é derivada de por_dia, e por_regra vem de outra
  // consulta do backend; as duas contagens têm de bater.
  it("soma da série = alertas.total (27)", () => {
    expect(serie.reduce((s, p) => s + p.total, 0)).toBe(alertas.total);
  });

  it("soma de cada regra na série = total dela em por_regra", () => {
    for (const regra of alertas.por_regra) {
      expect(serie.reduce((s, p) => s + p.valores[regra.codigo]!, 0), regra.codigo).toBe(regra.total);
    }
  });

  it("total de cada ponto = soma das regras do dia", () => {
    for (const p of serie) expect(p.total).toBe(Object.values(p.valores).reduce((s, n) => s + n, 0));
  });

  it("dias com valor batem com por_dia (17/10: R1 2, R2 1)", () => {
    expect(serie.find((p) => p.data === "2026-10-17")).toEqual({
      data: "2026-10-17",
      valores: { R1: 2, R2: 1, R3: 0 },
      total: 3,
    });
  });

  it("dia de por_dia fora do período estende o eixo em vez de sumir", () => {
    const s = serieAlertasPorDia([{ data: "2026-10-10", por_regra: { R1: 1 } }], "2026-10-12", "2026-10-13", ["R1"]);
    expect(s.map((p) => [p.data, p.total])).toEqual([
      ["2026-10-10", 1],
      ["2026-10-11", 0],
      ["2026-10-12", 0],
      ["2026-10-13", 0],
    ]);
  });

  it("sem alertas, mas com período → todos os dias com 0", () => {
    const s = serieAlertasPorDia([], "2026-10-13", "2026-10-15", ["R1", "R2"]);
    expect(s).toHaveLength(3);
    expect(s.every((p) => p.total === 0)).toBe(true);
  });

  it("sem período e sem alertas → []", () => {
    expect(serieAlertasPorDia([], null, null, ["R1"])).toEqual([]);
  });
});

describe("codigosDaSerie", () => {
  it("ordem de por_regra; código só em por_dia entra no fim, em ordem alfabética", () => {
    const porRegra = RESUMO_LIMEN.alertas.por_regra;
    const porDia = [{ data: "2026-10-13", por_regra: { Z9: 1, R1: 1, A1: 2 } }];
    expect(codigosDaSerie(porRegra, porDia)).toEqual(["R1", "R2", "R3", "A1", "Z9"]);
  });
});

describe("codigoNoTopo", () => {
  const codigos = ["R1", "R2", "R3"];
  it.each([
    [{ R1: 0, R2: 2, R3: 1 }, "R3"], // 01/11: R3 está no topo
    [{ R1: 2, R2: 1, R3: 0 }, "R2"], // 17/10: R3 vazio, o topo é R2
    [{ R1: 1, R2: 0, R3: 0 }, "R1"],
    [{ R1: 0, R2: 0, R3: 0 }, null],
    [{}, null],
  ])("%j → %s", (valores, esperado) => {
    expect(codigoNoTopo(valores, codigos)).toBe(esperado);
  });

  it("na série do limen, todo dia com alerta tem exatamente um topo, e é uma regra com valor", () => {
    const { alertas, metricas } = RESUMO_LIMEN;
    const serie = serieAlertasPorDia(alertas.por_dia, metricas.inicio, metricas.fim, codigos);
    for (const p of serie) {
      const topo = codigoNoTopo(p.valores, codigos);
      if (p.total === 0) expect(topo).toBeNull();
      else expect(p.valores[topo!]).toBeGreaterThan(0);
    }
  });
});

describe("descricaoGrafico", () => {
  it("dados do limen", () => {
    expect(descricaoGrafico(RESUMO_LIMEN)).toBe(
      "27 alertas em 20 dias de 13/10 a 11/11/2026: R1 9, R2 9, R3 9.",
    );
  });

  it("singular: 1 alerta em 1 dia", () => {
    const r = comAlertas({
      total: 1,
      por_regra: [{ regra_id: 1, codigo: "R1", nome: "CTR baixo", ativa: true, total: 1 }],
      por_dia: [{ data: "2026-10-17", por_regra: { R1: 1 } }],
    });
    expect(descricaoGrafico(r)).toBe("1 alerta em 1 dia de 13/10 a 11/11/2026: R1 1.");
  });

  it("sem alertas", () => {
    expect(descricaoGrafico(comAlertas({ total: 0, por_dia: [] }))).toBe("Nenhum alerta de 13/10 a 11/11/2026.");
  });
});

describe("textos dos KPIs", () => {
  it.each([
    [{ ENABLED: 2, PAUSED: 1, REMOVED: 0, UNKNOWN: 0 }, "2 ativas · 1 pausada"],
    [{ ENABLED: 1, PAUSED: 0, REMOVED: 0, UNKNOWN: 0 }, "1 ativa"],
    [{ PAUSED: 3, ENABLED: 1 }, "1 ativa · 3 pausadas"],
    [{ ENABLED: 0, PAUSED: 0, REMOVED: 0, UNKNOWN: 0 }, "nenhuma campanha"],
  ])("campanhas %j → %s", (porStatus, esperado) => {
    expect(textoCampanhas(porStatus)).toBe(esperado);
  });

  it.each([
    [{ total: 3, ativas: 3 }, "3 ativas de 3"],
    [{ total: 3, ativas: 1 }, "1 ativa de 3"],
    [{ total: 0, ativas: 0 }, "nenhuma regra"],
  ])("regras %j → %s", (regras, esperado) => {
    expect(textoRegras(regras)).toBe(esperado);
  });

  it("métricas do limen", () => {
    expect(textoMetricas(RESUMO_LIMEN.metricas)).toBe("13/10 a 11/11/2026 · 90 sintéticos");
  });

  it("métricas de duas origens e sem nenhuma", () => {
    const m = { registros: 31, inicio: "2026-10-13", fim: "2026-10-13", por_origem: { sintetica: 1, google_ads: 30 } };
    expect(textoMetricas(m)).toBe("13/10/2026 · 1 sintético · 30 do Google Ads");
    expect(textoMetricas({ registros: 0, inicio: null, fim: null, por_origem: { sintetica: 0, google_ads: 0 } })).toBe(
      "nenhum registro",
    );
  });

  // Ajuste (1) da etapa 4: o 27 soma alertas de mais de uma avaliação.
  it.each([
    [2, "gerados em 2 avaliações"],
    [1, "gerados em 1 avaliação"],
    [0, "nenhuma avaliação gerou alertas"],
  ])("alertas.avaliacoes = %i → %s", (avaliacoes, esperado) => {
    expect(textoAlertas({ ...RESUMO_LIMEN.alertas, avaliacoes })).toBe(esperado);
  });
});

describe("textoParametros", () => {
  const SEM_PARAMETROS = { incluir_pausadas: null, campanha_id: null, inicio: null, fim: null };

  it('avaliação anterior à 0003 (tudo NULL) → "não registrado", nunca "só ativas"', () => {
    expect(textoParametros(RESUMO_LIMEN.ultima_avaliacao!)).toBe("não registrado");
    expect(textoParametros(SEM_PARAMETROS)).not.toContain("só ativas");
  });

  it.each([
    [{ ...SEM_PARAMETROS, incluir_pausadas: true }, "com pausadas · todas as campanhas · período todo"],
    [{ ...SEM_PARAMETROS, incluir_pausadas: false }, "só ativas · todas as campanhas · período todo"],
    [
      { incluir_pausadas: false, campanha_id: 5, inicio: "2026-10-13", fim: "2026-11-11" },
      "só ativas · campanha nº 5 · 13/10 a 11/11/2026",
    ],
    [{ ...SEM_PARAMETROS, incluir_pausadas: true, inicio: "2026-10-13" }, "com pausadas · todas as campanhas · a partir de 13/10/2026"],
    [{ ...SEM_PARAMETROS, incluir_pausadas: true, fim: "2026-11-11" }, "com pausadas · todas as campanhas · até 11/11/2026"],
  ])("%j → %s", (parametros, esperado) => {
    expect(textoParametros(parametros)).toBe(esperado);
  });
});

describe("textoDuracao", () => {
  it.each([
    ["0.870", "0,870 ms"],
    ["1234.5", "1.234,5 ms"],
    [null, "—"],
  ])("%j → %s", (ms, esperado) => {
    expect(textoDuracao(ms)).toBe(esperado);
  });
});

describe("estadoVazio", () => {
  const base = RESUMO_LIMEN;

  it("dados do limen → null (há alertas)", () => {
    expect(estadoVazio(base)).toBeNull();
  });

  it.each([
    ["sem_campanhas", { ...base, campanhas: { total: 0, por_status: {} }, metricas: { ...base.metricas, registros: 0 } }],
    ["sem_metricas", { ...base, metricas: { ...base.metricas, registros: 0 } }],
    ["sem_avaliacoes", { ...base, ultima_avaliacao: null }],
    ["sem_alertas", comAlertas({ total: 0, avaliacoes: 0, por_dia: [] })],
  ] as const)("%s", (esperado, resumo) => {
    expect(estadoVazio(resumo)).toBe(esperado);
  });

  it("a ordem do fluxo vale: sem campanhas vence os outros vazios", () => {
    const tudoVazio = { ...comAlertas({ total: 0 }), campanhas: { total: 0, por_status: {} }, ultima_avaliacao: null };
    expect(estadoVazio(tudoVazio)).toBe("sem_campanhas");
  });
});
