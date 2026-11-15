import { readdirSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  camposInvalidos,
  deveRepetir,
  ErroApi,
  erroDeRede,
  formatarEspera,
  lerErro,
  lerRetryAfter,
  MAXIMO_DE_REPETICOES,
  MENSAGENS,
  mensagemDoErro,
  TIPOS_DO_FRONTEND,
} from "./erros";

// --- Oráculo: os tipos que o backend emite --------------------------------------
//
// Lê todos os arquivos .py de backend/app (só .py: o backend/.env fica fora de
// backend/app e não é .py, então nunca é lido) e extrai os valores de `tipo`:
//   1. segundo argumento literal de `_erro(status, "tipo", ...)`;
//   2. valores de dicionários `_TIPO_...= { status: "tipo" }`;
//   3. padrão de `_TIPO_....get(status, "tipo")`;
//   4. pares literais `"tipo": "valor"` montados à mão.
// Se aparecer `_erro(...)` com um segundo argumento que não é literal nem a variável
// `tipo` (que vem do dicionário), o teste reprova: o oráculo não deixaria passar um
// tipo que ele não sabe ler.

const RAIZ_BACKEND = new URL("../../../backend/app/", import.meta.url);

function arquivosPython(): { caminho: string; texto: string }[] {
  return readdirSync(RAIZ_BACKEND, { recursive: true, encoding: "utf8" })
    .filter((caminho) => caminho.endsWith(".py") && !caminho.includes("__pycache__"))
    .map((caminho) => ({ caminho, texto: readFileSync(new URL(caminho, RAIZ_BACKEND), "utf8") }));
}

function tiposDoBackend() {
  const tipos = new Set<string>();
  const chamadasNaoLidas: string[] = [];
  let chamadas = 0;

  for (const { caminho, texto } of arquivosPython()) {
    // 1. _erro(status, "tipo", ...) — ignora a própria definição (def _erro).
    for (const m of texto.matchAll(/(?<!def )\b_erro\(\s*[^,]+?,\s*(?:"([a-z_]+)"|([A-Za-z_]\w*))/g)) {
      chamadas++;
      if (m[1]) tipos.add(m[1]);
      else if (m[2] !== "tipo") chamadasNaoLidas.push(`${caminho}: _erro(..., ${m[2]}, ...)`);
    }
    // 2. Dicionários _TIPO_... = { ...: "tipo", ... }
    for (const m of texto.matchAll(/\b_TIPO_\w*\s*=\s*\{([^}]*)\}/g)) {
      for (const v of m[1]!.matchAll(/:\s*"([a-z_]+)"/g)) tipos.add(v[1]!);
    }
    // 3. _TIPO_....get(status, "padrão")
    for (const m of texto.matchAll(/\b_TIPO_\w*\.get\([^,]+,\s*"([a-z_]+)"\)/g)) tipos.add(m[1]!);
    // 4. "tipo": "valor"
    for (const m of texto.matchAll(/"tipo"\s*:\s*"([a-z_]+)"/g)) tipos.add(m[1]!);
  }
  return { tipos: [...tipos].sort(), chamadas, chamadasNaoLidas };
}

const backend = tiposDoBackend();

describe("oráculo: tipos de erro do backend", () => {
  it("o leitor encontra as chamadas e não deixa nenhuma sem ler", () => {
    expect(backend.chamadas).toBeGreaterThan(0);
    expect(backend.chamadasNaoLidas).toEqual([]);
  });

  it("encontra pelo menos os tipos registrados na Fase 0 (o leitor não está vazio)", () => {
    expect(backend.tipos).toEqual(
      expect.arrayContaining([
        "validacao",
        "requisicao_invalida",
        "nao_autenticado",
        "nao_encontrado",
        "conflito",
        "token_google_ausente",
        "token_google_revogado",
        "erro_google_ads",
        "google_autenticacao_temporaria",
        "google_ads_indisponivel",
        "cota_excedida",
        "erro_http",
      ]),
    );
  });

  it.each(backend.tipos)("o tipo %s tem mensagem própria", (tipo) => {
    expect(Object.hasOwn(MENSAGENS, tipo)).toBe(true);
  });

  it("toda mensagem corresponde a um tipo do backend ou do frontend (sem chave esquecida ou com erro de digitação)", () => {
    const validos = new Set<string>([...backend.tipos, ...TIPOS_DO_FRONTEND]);
    expect(Object.keys(MENSAGENS).filter((tipo) => !validos.has(tipo))).toEqual([]);
  });

  it("o frontend não reaproveita um nome que o backend já usa", () => {
    expect(TIPOS_DO_FRONTEND.filter((t) => backend.tipos.includes(t))).toEqual([]);
  });
});

// --- Leitura da resposta ----------------------------------------------------------

const cabecalhos = (valores: Record<string, string>) => new Headers(valores);

describe("lerErro", () => {
  it("usa o tipo do corpo no formato do backend", () => {
    const erro = lerErro(409, { detail: "Regra R1 já existe", tipo: "conflito" });
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro).toMatchObject({ status: 409, tipo: "conflito", detail: "Regra R1 já existe", retryAfter: null });
  });

  it("lê o Retry-After da cota excedida", () => {
    const erro = lerErro(503, { detail: "Cota excedida", tipo: "cota_excedida" }, cabecalhos({ "Retry-After": "3600" }));
    expect(erro.retryAfter).toBe(3600);
  });

  it("502 sem tipo (proxy do Vite com o backend parado) vira sem_conexao", () => {
    expect(lerErro(502, "").tipo).toBe("sem_conexao");
    expect(lerErro(502, undefined).tipo).toBe("sem_conexao");
  });

  it("502 do próprio backend continua erro_google_ads", () => {
    expect(lerErro(502, { detail: "Erro na comunicação", tipo: "erro_google_ads" }).tipo).toBe("erro_google_ads");
  });

  it.each([
    ["texto puro", 500, "Internal Server Error"],
    ["sem corpo", 404, undefined],
    ["tipo vazio", 400, { detail: "x", tipo: "" }],
    ["tipo que não é texto", 400, { detail: "x", tipo: 7 }],
    ["lista", 400, [{ tipo: "validacao" }]],
  ])("corpo fora do formato (%s) vira desconhecido", (_, status, corpo) => {
    const erro = lerErro(status, corpo);
    expect(erro.tipo).toBe("desconhecido");
    expect(erro.status).toBe(status);
  });
});

describe("lerRetryAfter", () => {
  it.each([
    ["3600", 3600],
    [" 60 ", 60],
    ["0", 0],
    ["Wed, 21 Oct 2026 07:28:00 GMT", null],
    ["-1", null],
    ["1.5", null],
    ["", null],
    [null, null],
    [undefined, null],
  ])("%j → %j", (valor, esperado) => {
    expect(lerRetryAfter(valor)).toBe(esperado);
  });
});

describe("erroDeRede", () => {
  it("falha do fetch vira sem_conexao sem status", () => {
    const erro = erroDeRede(new TypeError("Failed to fetch"));
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro).toMatchObject({ status: null, tipo: "sem_conexao" });
  });

  it("cancelamento (AbortError) sai como veio: não é erro de conexão", () => {
    const cancelamento = new DOMException("cancelado", "AbortError");
    expect(erroDeRede(cancelamento)).toBe(cancelamento);
  });
});

// --- Mensagens --------------------------------------------------------------------

const erro = (tipo: string, extra: Partial<{ status: number | null; detail: unknown; retryAfter: number | null }> = {}) =>
  new ErroApi({ status: 400, tipo, ...extra });

describe("mensagemDoErro", () => {
  it.each([...backend.tipos, ...TIPOS_DO_FRONTEND])("%s tem título e texto em português", (tipo) => {
    const m = mensagemDoErro(erro(tipo));
    expect(m.titulo.length).toBeGreaterThan(0);
    expect(m.texto.length).toBeGreaterThan(0);
  });

  it("token_google_revogado pede reconexão com o Google", () => {
    const m = mensagemDoErro(erro("token_google_revogado", { status: 409 }));
    expect(m.acao).toBe("reconectar_google");
    expect(m.texto).toMatch(/revogado/);
  });

  it("token_google_ausente também pede reconexão (outro 409, outra ação que conflito)", () => {
    expect(mensagemDoErro(erro("token_google_ausente", { status: 409 })).acao).toBe("reconectar_google");
    expect(mensagemDoErro(erro("conflito", { status: 409 })).acao).toBeNull();
  });

  it("cota_excedida diz quanto esperar e não oferece repetir", () => {
    const m = mensagemDoErro(erro("cota_excedida", { status: 503, retryAfter: 3600 }));
    expect(m.texto).toContain("em cerca de 1 hora");
    expect(m.acao).toBeNull();
  });

  it("cota_excedida sem Retry-After diz 'mais tarde'", () => {
    expect(mensagemDoErro(erro("cota_excedida", { status: 503 })).texto).toContain("mais tarde");
  });

  it.each([
    [120, "em 2 minutos"],
    [5400, "em cerca de 2 horas"],
  ])("cota_excedida usa o Retry-After real, não um texto fixo (%i s → %s)", (segundos, trecho) => {
    const m = mensagemDoErro(erro("cota_excedida", { status: 503, retryAfter: segundos }));
    expect(m.texto).toContain(trecho);
    expect(m.texto).not.toContain("1 hora");
    expect(m.acao).toBeNull();
  });

  it("cota_excedida: do cabeçalho Retry-After até o texto (lerErro → mensagemDoErro)", () => {
    const corpo = { detail: "Cota excedida", tipo: "cota_excedida" };
    const m = mensagemDoErro(lerErro(503, corpo, cabecalhos({ "Retry-After": "5400" })));
    expect(m.texto).toContain("em cerca de 2 horas");
  });

  it("nao_autenticado leva a entrar", () => {
    expect(mensagemDoErro(erro("nao_autenticado", { status: 401 })).acao).toBe("entrar");
  });

  it("sem_conexao fala do backend na porta 8080 e oferece repetir", () => {
    const m = mensagemDoErro(erro("sem_conexao", { status: null }));
    expect(m.texto).toContain("8080");
    expect(m.acao).toBe("tentar_novamente");
  });

  it("conflito e requisicao_invalida mostram o detail (o backend o escreve em português)", () => {
    expect(mensagemDoErro(erro("conflito", { detail: "Já existe métrica para 13/10" })).texto).toBe(
      "Já existe métrica para 13/10",
    );
    expect(mensagemDoErro(erro("requisicao_invalida", { detail: "inicio deve ser anterior ou igual a fim" })).texto).toBe(
      "inicio deve ser anterior ou igual a fim",
    );
  });

  it("validacao cita os campos, não a mensagem em inglês do Pydantic", () => {
    const m = mensagemDoErro(
      erro("validacao", { detail: [{ local: ["query", "limite"], mensagem: "Input should be less than or equal to 500" }] }),
    );
    expect(m.texto).toBe("Confira o campo: limite.");
    expect(m.texto).not.toMatch(/Input should/);
  });

  it("detalhe técnico só quando o detail é texto", () => {
    expect(mensagemDoErro(erro("erro_google_ads", { detail: "Erro na comunicação com o Google Ads [X]." })).detalhe).toBe(
      "Erro na comunicação com o Google Ads [X].",
    );
    expect(mensagemDoErro(erro("validacao", { detail: [] })).detalhe).toBeNull();
  });

  it.each(["tipo_que_nao_existe", "toString", "__proto__", "constructor"])("tipo desconhecido (%s) cai na mensagem genérica", (tipo) => {
    const m = mensagemDoErro(erro(tipo, { status: 500 }));
    expect(m.titulo).toBe("Erro inesperado");
    expect(m.texto).toContain("500");
  });

  it("erro que não é da API (bug no frontend) também tem mensagem", () => {
    expect(mensagemDoErro(new Error("x")).titulo).toBe("Erro inesperado");
    expect(mensagemDoErro("texto solto").acao).toBe("tentar_novamente");
  });
});

describe("camposInvalidos", () => {
  it("tira o lugar (body/query/path) e repete cada campo uma vez", () => {
    expect(
      camposInvalidos([
        { local: ["body", "campanha_id"] },
        { local: ["query", "limite"] },
        { local: ["body", "campanha_id"] },
        { local: ["body", "condicoes", 0, "limiar"] },
      ]),
    ).toEqual(["campanha_id", "limite", "condicoes.0.limiar"]);
  });

  it("local com um só elemento é o próprio campo", () => {
    expect(camposInvalidos([{ local: ["body"] }])).toEqual(["body"]);
  });

  it.each([undefined, "texto", {}, [{ sem_local: 1 }], [null]])("formato inesperado (%j) → nenhum campo", (detail) => {
    expect(camposInvalidos(detail)).toEqual([]);
  });
});

describe("formatarEspera", () => {
  it.each([
    [null, "mais tarde"],
    [0, "em alguns segundos"],
    [59, "em alguns segundos"],
    [60, "em 1 minuto"],
    [61, "em 2 minutos"],
    [300, "em 5 minutos"],
    [3599, "em cerca de 1 hora"],
    [3600, "em cerca de 1 hora"],
    [5400, "em cerca de 2 horas"],
  ])("%j s → %s", (segundos, esperado) => {
    expect(formatarEspera(segundos)).toBe(esperado);
  });
});

// --- Repetição automática ---------------------------------------------------------

describe("deveRepetir", () => {
  const casos: [string, number, unknown, boolean][] = [
    // Transitórios: repete até MAXIMO_DE_REPETICOES vezes
    ["sem_conexao (proxy 502), 1ª falha", 0, erro("sem_conexao", { status: 502 }), true],
    ["sem_conexao (proxy 502), 2ª falha", 1, erro("sem_conexao", { status: 502 }), true],
    ["sem_conexao (proxy 502), 3ª falha", 2, erro("sem_conexao", { status: 502 }), false],
    ["sem_conexao (fetch lançou), 1ª falha", 0, erro("sem_conexao", { status: null }), true],
    ["google_ads_indisponivel", 0, erro("google_ads_indisponivel", { status: 503 }), true],
    ["google_autenticacao_temporaria", 0, erro("google_autenticacao_temporaria", { status: 503 }), true],
    // 401: nunca. Repetir não abre sessão; o certo é ir para Entrar.
    ["401 nao_autenticado, 1ª falha", 0, erro("nao_autenticado", { status: 401 }), false],
    ["401 mesmo com tipo transitório", 0, erro("google_ads_indisponivel", { status: 401 }), false],
    // Outros 4xx: o pedido está errado; repetir dá o mesmo resultado
    ["400 validacao", 0, erro("validacao", { status: 400 }), false],
    ["404 nao_encontrado", 0, erro("nao_encontrado", { status: 404 }), false],
    ["409 conflito", 0, erro("conflito", { status: 409 }), false],
    ["409 token_google_revogado", 0, erro("token_google_revogado", { status: 409 }), false],
    // 5xx permanentes ou que gastariam cota (IN-06)
    ["503 cota_excedida", 0, erro("cota_excedida", { status: 503, retryAfter: 3600 }), false],
    ["502 erro_google_ads", 0, erro("erro_google_ads", { status: 502 }), false],
    ["500 erro_http", 0, erro("erro_http", { status: 500 }), false],
    ["500 desconhecido", 0, erro("desconhecido", { status: 500 }), false],
    // Não é da API
    ["Error comum", 0, new Error("bug"), false],
    ["AbortError", 0, new DOMException("cancelado", "AbortError"), false],
  ];

  it.each(casos)("%s (falhas=%i) → %s", (_, falhas, e, esperado) => {
    expect(deveRepetir(falhas, e)).toBe(esperado);
  });

  it("o limite é de 2 repetições (3 tentativas no total)", () => {
    expect(MAXIMO_DE_REPETICOES).toBe(2);
  });

  it("401 não é repetido em nenhuma contagem de falhas", () => {
    for (let falhas = 0; falhas < 10; falhas++) {
      expect(deveRepetir(falhas, erro("nao_autenticado", { status: 401 }))).toBe(false);
    }
  });
});
