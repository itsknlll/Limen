// Oráculo: ids reais do banco limen (consulta só leitura de 15/11/2026: campanha 1 = A,
// 2 = C, 3 = B; regras 1 a 3 = R1 a R3). As regras de datas são as do POST /avaliacoes:
// o teste compara com montarPedidoAvaliacao (pedido.ts), cujo oráculo é o Pydantic.
import { describe, expect, it } from "vitest";
import { MENSAGENS_PEDIDO, montarPedidoAvaliacao } from "@/avaliacoes/pedido";
import {
  FILTROS_VAZIOS,
  LIMITE_ALERTAS,
  MENSAGENS_FILTROS,
  envioDosFiltros,
  errosVisiveis,
  filtrosParaUrl,
  lerFiltros,
  linkAlertas,
  listaParaFiltro,
  montarConsultaAlertas,
  opcoesRegraFiltro,
  primeiroFiltroComErro,
  temFiltro,
  valorDoCampoData,
  type FiltrosAlertas,
  type ResultadoFiltros,
} from "./filtros";

const CAMPANHAS = [
  { id: 1, nome: "Limen A - Pesquisa", status: "ENABLED" },
  { id: 2, nome: "Limen C - Pesquisa", status: "PAUSED" },
  { id: 3, nome: "Limen B - Pesquisa", status: "ENABLED" },
];
const REGRAS = [{ id: 1 }, { id: 2 }, { id: 3 }];

const f = (parcial: Partial<FiltrosAlertas>): FiltrosAlertas => ({ ...FILTROS_VAZIOS, ...parcial });

function pronta(r: ResultadoFiltros) {
  if (r.estado !== "pronta") throw new Error(`esperava "pronta", veio ${JSON.stringify(r)}`);
  return r.consulta;
}
function invalida(r: ResultadoFiltros) {
  if (r.estado !== "invalida") throw new Error(`esperava "invalida", veio ${JSON.stringify(r)}`);
  return r.erros;
}

describe("lerFiltros", () => {
  it("URL sem parâmetros: todos vazios", () => {
    expect(lerFiltros(new URLSearchParams(""))).toEqual(FILTROS_VAZIOS);
  });
  it("lê os quatro parâmetros pelos nomes em português", () => {
    expect(lerFiltros(new URLSearchParams("campanha=2&regra=1&inicio=2026-10-13&fim=2026-11-11"))).toEqual({
      campanhaId: "2",
      regraId: "1",
      inicio: "2026-10-13",
      fim: "2026-11-11",
    });
  });
  it("ignora parâmetros desconhecidos, inclusive os nomes do backend", () => {
    expect(lerFiltros(new URLSearchParams("campanha_id=2&regra_id=1&limite=5"))).toEqual(FILTROS_VAZIOS);
  });
  it("parâmetro repetido: vale o primeiro", () => {
    expect(lerFiltros(new URLSearchParams("campanha=2&campanha=3")).campanhaId).toBe("2");
  });
  it("valor vem como está; quem valida é montarConsultaAlertas", () => {
    expect(lerFiltros(new URLSearchParams("campanha=abc&inicio=ontem"))).toEqual(f({ campanhaId: "abc", inicio: "ontem" }));
  });
});

describe("filtrosParaUrl", () => {
  it("só os campos preenchidos", () => {
    expect(filtrosParaUrl(f({ regraId: "3" })).toString()).toBe("regra=3");
  });
  it("ordem fixa, a da tela", () => {
    const filtros = { fim: "2026-11-11", inicio: "2026-10-13", regraId: "1", campanhaId: "2" };
    expect(filtrosParaUrl(filtros).toString()).toBe("campanha=2&regra=1&inicio=2026-10-13&fim=2026-11-11");
  });
  it("sem filtro: texto vazio", () => {
    expect(filtrosParaUrl(FILTROS_VAZIOS).toString()).toBe("");
  });
  it.each([
    FILTROS_VAZIOS,
    f({ campanhaId: "2" }),
    f({ inicio: "2026-10-13", fim: "2026-11-11" }),
    { campanhaId: "3", regraId: "2", inicio: "2026-11-11", fim: "2026-11-11" },
  ])("ida e volta: %o", (filtros) => {
    expect(lerFiltros(filtrosParaUrl(filtros))).toEqual(filtros);
  });
});

describe("temFiltro", () => {
  it.each([
    [FILTROS_VAZIOS, false],
    [f({ campanhaId: "1" }), true],
    [f({ regraId: "1" }), true],
    [f({ inicio: "2026-10-13" }), true],
    [f({ fim: "2026-11-11" }), true],
  ])("%o → %s", (filtros, esperado) => {
    expect(temFiltro(filtros)).toBe(esperado);
  });
});

describe("primeiroFiltroComErro", () => {
  it("segue a ordem da tela, não a ordem das chaves", () => {
    expect(primeiroFiltroComErro({ fim: "x", regraId: "y" })).toBe("regraId");
  });
  it("sem erro: null", () => {
    expect(primeiroFiltroComErro({})).toBeNull();
  });
});

describe("linkAlertas", () => {
  it("avaliação sem filtros: /alertas puro", () => {
    expect(linkAlertas({})).toBe("/alertas");
    expect(linkAlertas({ campanha_id: null, inicio: null, fim: null })).toBe("/alertas");
  });
  it("campanha e período da execução; incluir_pausadas não vira filtro", () => {
    const corpo = { campanha_id: 2, inicio: "2026-10-13", fim: "2026-11-11", incluir_pausadas: true };
    expect(linkAlertas(corpo)).toBe("/alertas?campanha=2&inicio=2026-10-13&fim=2026-11-11");
  });
  it("ida e volta: o corpo enviado em POST /avaliacoes vira a mesma campanha e o mesmo período em GET /alertas", () => {
    const pedido = montarPedidoAvaliacao(
      { campanhaId: "2", inicio: "2026-10-13", fim: "2026-11-11", incluirPausadas: true },
      CAMPANHAS,
    );
    if (!pedido.ok) throw new Error("pedido do teste deveria ser válido");
    const url = new URL(linkAlertas(pedido.corpo), "http://localhost");
    expect(url.pathname).toBe("/alertas");
    const consulta = pronta(montarConsultaAlertas(lerFiltros(url.searchParams), CAMPANHAS, REGRAS));
    expect(consulta).toEqual({ campanha_id: 2, inicio: "2026-10-13", fim: "2026-11-11", limite: LIMITE_ALERTAS });
  });
});

describe("montarConsultaAlertas", () => {
  it("o limite é 500 e vai sempre", () => {
    expect(LIMITE_ALERTAS).toBe(500);
    expect(pronta(montarConsultaAlertas(FILTROS_VAZIOS, CAMPANHAS, REGRAS))).toEqual({ limite: 500 });
  });
  it("campanha pelo id, não pela posição: 2 é a C", () => {
    expect(pronta(montarConsultaAlertas(f({ campanhaId: "2" }), CAMPANHAS, REGRAS))).toEqual({ campanha_id: 2, limite: 500 });
  });
  it("regra pelo id", () => {
    expect(pronta(montarConsultaAlertas(f({ regraId: "3" }), CAMPANHAS, REGRAS))).toEqual({ regra_id: 3, limite: 500 });
  });
  it("os quatro filtros juntos", () => {
    const filtros = { campanhaId: "3", regraId: "1", inicio: "2026-10-13", fim: "2026-11-11" };
    expect(pronta(montarConsultaAlertas(filtros, CAMPANHAS, REGRAS))).toEqual({
      campanha_id: 3,
      regra_id: 1,
      inicio: "2026-10-13",
      fim: "2026-11-11",
      limite: 500,
    });
  });
  it('campo vazio nunca vai, nem como "" nem como null', () => {
    const consulta = pronta(montarConsultaAlertas(f({ inicio: "2026-10-13" }), CAMPANHAS, REGRAS));
    expect(Object.keys(consulta).sort()).toEqual(["inicio", "limite"]);
  });
  it.each(["0", "007", "-1", "1.5", "abc", " 2", "99"])("campanha %j: erro no campo, sem consulta", (valor) => {
    expect(invalida(montarConsultaAlertas(f({ campanhaId: valor }), CAMPANHAS, REGRAS))).toEqual({
      campanhaId: MENSAGENS_FILTROS.campanha,
    });
  });
  it.each(["0", "4", "99", "R1"])("regra %j: erro no campo, sem consulta", (valor) => {
    expect(invalida(montarConsultaAlertas(f({ regraId: valor }), CAMPANHAS, REGRAS))).toEqual({
      regraId: MENSAGENS_FILTROS.regra,
    });
  });
  it("período invertido: erro na data final", () => {
    expect(invalida(montarConsultaAlertas(f({ inicio: "2026-11-12", fim: "2026-11-11" }), CAMPANHAS, REGRAS))).toEqual({
      fim: MENSAGENS_PEDIDO.periodo,
    });
  });
  it("início igual ao fim é aceito", () => {
    expect(pronta(montarConsultaAlertas(f({ inicio: "2026-11-11", fim: "2026-11-11" }), CAMPANHAS, REGRAS))).toEqual({
      inicio: "2026-11-11",
      fim: "2026-11-11",
      limite: 500,
    });
  });

  // Mesmas regras de datas do POST /avaliacoes: o veredito e os erros têm de ser os do pedido.ts.
  const PERIODOS: [string, string][] = [
    ["", ""],
    ["2026-10-13", "2026-11-11"],
    ["2026-11-11", "2026-11-11"],
    ["2026-11-12", "2026-11-11"],
    ["2026-12-31", "2027-01-01"],
    ["2024-02-29", ""],
    ["2026-02-29", ""],
    ["", "2026-11-31"],
    ["2026-11-11T00:00:00", ""],
    ["0000-01-01", ""],
    ["ontem", "2026-11-11"],
    ["2026-13-01", "2026-00-10"],
  ];
  it.each(PERIODOS)("datas %j a %j: mesmo resultado do pedido de avaliação", (inicio, fim) => {
    const pedido = montarPedidoAvaliacao({ campanhaId: "", inicio, fim, incluirPausadas: false }, CAMPANHAS);
    const filtros = montarConsultaAlertas(f({ inicio, fim }), CAMPANHAS, REGRAS);
    if (pedido.ok) {
      const consulta = pronta(filtros);
      expect(consulta.inicio).toBe(pedido.corpo.inicio);
      expect(consulta.fim).toBe(pedido.corpo.fim);
    } else {
      expect(invalida(filtros)).toEqual(pedido.erros);
    }
  });

  describe("listas ainda carregando", () => {
    it("sem filtro de campanha nem de regra, não espera as listas", () => {
      expect(pronta(montarConsultaAlertas(FILTROS_VAZIOS, undefined, undefined))).toEqual({ limite: 500 });
    });
    it("com filtro de campanha e a lista carregando: aguarda", () => {
      expect(montarConsultaAlertas(f({ campanhaId: "2" }), undefined, REGRAS)).toEqual({ estado: "aguardando" });
    });
    it("com filtro de regra e a lista carregando: aguarda", () => {
      expect(montarConsultaAlertas(f({ regraId: "1" }), CAMPANHAS, undefined)).toEqual({ estado: "aguardando" });
    });
    it("id mal escrito não espera a lista", () => {
      expect(invalida(montarConsultaAlertas(f({ campanhaId: "abc" }), undefined, undefined))).toEqual({
        campanhaId: MENSAGENS_FILTROS.campanha,
      });
    });
    it("data inválida vence a espera", () => {
      expect(invalida(montarConsultaAlertas(f({ campanhaId: "2", inicio: "ontem" }), undefined, REGRAS))).toEqual({
        inicio: MENSAGENS_PEDIDO.data,
      });
    });
    it("lista que falhou chega vazia: o id não é conferido e o campo mostra o erro", () => {
      expect(invalida(montarConsultaAlertas(f({ campanhaId: "2" }), [], REGRAS))).toEqual({
        campanhaId: MENSAGENS_FILTROS.campanha,
      });
    });
    it("quando a lista chega, a mesma URL vira consulta", () => {
      const filtros = f({ campanhaId: "2" });
      expect(montarConsultaAlertas(filtros, undefined, REGRAS).estado).toBe("aguardando");
      expect(pronta(montarConsultaAlertas(filtros, CAMPANHAS, REGRAS))).toEqual({ campanha_id: 2, limite: 500 });
    });
  });
});

describe("listaParaFiltro", () => {
  it("carregando: undefined (espera)", () => {
    expect(listaParaFiltro({ data: undefined, isError: false })).toBeUndefined();
  });
  it("erro sem dados: [] (o id não pode ser conferido)", () => {
    expect(listaParaFiltro({ data: undefined, isError: true })).toEqual([]);
  });
  it("com dados, os dados, mesmo se a releitura falhou", () => {
    expect(listaParaFiltro({ data: CAMPANHAS, isError: true })).toBe(CAMPANHAS);
  });
  it("lista vazia de verdade continua vazia", () => {
    expect(listaParaFiltro({ data: [], isError: false })).toEqual([]);
  });
});

describe("envioDosFiltros", () => {
  it("válido: grava a busca e não foca nada", () => {
    const e = envioDosFiltros(f({ campanhaId: "2", inicio: "2026-10-13" }), CAMPANHAS, REGRAS);
    expect([e.busca.toString(), e.foco]).toEqual(["campanha=2&inicio=2026-10-13", null]);
  });
  it("período invertido: grava a URL mesmo assim (ela é a fonte) e foca a data final", () => {
    const e = envioDosFiltros(f({ inicio: "2026-11-12", fim: "2026-11-11" }), CAMPANHAS, REGRAS);
    expect([e.busca.toString(), e.foco]).toEqual(["inicio=2026-11-12&fim=2026-11-11", "fim"]);
  });
  it("vários erros: foca o primeiro da tela", () => {
    expect(envioDosFiltros(f({ campanhaId: "99", inicio: "ontem" }), CAMPANHAS, REGRAS).foco).toBe("campanhaId");
  });
  it("lista carregando: sem erro, sem foco", () => {
    expect(envioDosFiltros(f({ campanhaId: "2" }), undefined, REGRAS).foco).toBeNull();
  });
});

describe("errosVisiveis", () => {
  const filtros = f({ campanhaId: "99", fim: "2026-11-11" });
  const erros = { campanhaId: MENSAGENS_FILTROS.campanha, fim: MENSAGENS_PEDIDO.periodo };
  it("rascunho igual à URL: todos os erros aparecem", () => {
    expect(errosVisiveis(erros, filtros, filtros)).toEqual(erros);
  });
  it("campo editado: o erro dele some até o próximo envio; o dos outros fica", () => {
    expect(errosVisiveis(erros, { ...filtros, campanhaId: "2" }, filtros)).toEqual({ fim: MENSAGENS_PEDIDO.periodo });
  });
});

describe("opcoesRegraFiltro", () => {
  it("Todas primeiro; código · nome; desativada marcada (sintético: R4)", () => {
    expect(
      opcoesRegraFiltro([
        { id: 1, codigo: "R1", nome: "CTR baixo", ativa: true },
        { id: 4, codigo: "R4", nome: "CTR muito baixo", ativa: false },
      ]),
    ).toEqual([
      { valor: "todas", rotulo: "Todas as regras" },
      { valor: "1", rotulo: "R1 · CTR baixo" },
      { valor: "4", rotulo: "R4 · CTR muito baixo (desativada)" },
    ]);
  });
});

describe("valorDoCampoData", () => {
  it.each([
    ["", ""],
    ["2026-10-13", "2026-10-13"],
    ["2024-02-29", "2024-02-29"],
    ["ontem", ""],
    ["2026-02-29", ""],
    ["2026-11-31", ""],
    ["2026-11-11T00:00:00", ""],
    ["0000-01-01", ""],
    ["2026-1-5", ""],
  ])("%j → %j", (texto, esperado) => {
    expect(valorDoCampoData(texto)).toBe(esperado);
  });
});
