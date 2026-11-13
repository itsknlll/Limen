# Limen — contexto do projeto para o Claude Code

TCC de Kauan Negreiros Lima (Engenharia de Software, iCEV), orientador Prof. Ítalo César
Carvalho Lima. Modalidade: artigo científico. Título: "Desenvolvimento e avaliação de um
motor de regras para geração de alertas sobre métricas de campanhas digitais integrado à
Google Ads API". O **motor de regras é o objeto central**; integração, persistência e
dashboard dão suporte a ele.

## Como trabalhar com o Kauan

- Responder **sempre em português**.
- Ir **por partes**, uma etapa de cada vez, confirmando antes de seguir. Ele prefere entender
  cada passo.
- Ele precisa **entender o código** para escrever o artigo: ao final de cada etapa, explicar
  em poucas linhas o que foi feito e as decisões tomadas (com a alternativa descartada).
- Ao final da aplicação, ele quer um **relatório técnico completo** do que foi feito, para
  servir de base ao artigo (ele escreve o artigo com as próprias palavras). Por isso, manter
  o registro de decisões abaixo **atualizado** a cada etapa.
- Prazo: aplicação pronta até **segunda, 16/11/2026**; artigo até **27/11/2026**.

## Regras que não podem ser quebradas

1. A tabela `docs/avaliacao/Tabela_limiares_TCC_motor_de_regras.xlsx` foi **congelada** no
   commit `29de91d` (12/11/2026), antes de qualquer código. **Não alterar limiares, políticas
   nem resultados esperados.** Se algo precisar mudar, gerar nova versão (v1.1) e registrar
   o motivo.
2. Os nomes de endpoint registrados na aba Desempenho são fixos: `GET /campanhas/{id}/metricas`,
   `GET /alertas`, `POST /regras`, `POST /avaliacoes`.
3. Erro de validação da API devolve **400** (não 422), como registrado no caso IN-09.
4. Segredos nunca vão para o git: `backend/.env`, `~/.config/limen/client_secret.json`,
   tokens OAuth. Conferir `git status` antes de cada commit.
5. Valores monetários e limiares sempre em `Decimal`/`NUMERIC`, nunca float.

## Stack e estrutura

Python 3.12 + FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 (Docker, porta **5433**),
pytest. Frontend previsto: React + TypeScript (Vite) + Recharts. SO do Kauan: Zorin OS 18
(base Ubuntu 24.04).

```
docker-compose.yml          PostgreSQL 16 (bancos limen e limen_teste; container: limen-db)
infra/postgres/init/        cria o banco limen_teste
backend/
  app/motor/                motor puro (sem banco/rede): metricas, validacao, regras, avaliador
  app/modelos.py            modelo relacional + view vw_metrica_diaria (somente leitura)
  app/servicos/             regras, campanhas, avaliacao, alertas, erros
  app/servicos/sincronizacao/  porta Google Ads, cliente real, sincronizador
  app/servicos/sinteticas/  gerador (puro, semente fixa) e semeador (IN-02b)
  app/api/                  esquemas Pydantic, deps (sessão/usuário), rotas
  app/main.py               FastAPI (SessionMiddleware, handlers 400/404/409)
  alembic/versions/         0001 modelo inicial · 0002 refresh token no usuário ·
                            0003 parâmetros da avaliação
  tests/                    motor (tabela + unidade), banco, api
docs/avaliacao/             tabela congelada
docs/evidencias/            prints e saídas do pytest (nome: AAAA-MM-DD_caso_descricao)
```

## Comandos

```bash
cd ~/projetos/limen && docker compose up -d        # banco (após reiniciar o PC)
cd backend && source .venv/bin/activate
pytest -q                                           # 211 testes passando em 13/11
alembic upgrade head
uvicorn app.main:app --reload --port 8080           # /docs; POST /dev/login (só em desenvolvimento)
pytest | tee ../docs/evidencias/AAAA-MM-DD_<etapa>_pytest.txt   # evidência antes do commit
```

Commits no padrão `tipo(escopo): descrição` em português, seguidos de `git push`
(repositório privado `github.com/itsknlll/Limen`).

## Google Ads (dados não secretos)

- Projeto Google Cloud `tcc-motor-regras` com acesso **Test** à Google Ads API.
  **Developer tokens foram descontinuados em 09/09/2026**: o nível de acesso fica no projeto
  do Cloud; não enviar developer token.
- Cliente OAuth tipo Aplicativo da Web; redirect URIs cadastradas:
  `http://localhost:8080/api/oauth/google/callback` e `https://developers.google.com/oauthplayground`.
  App em modo "Testando" (refresh token expira em ~7 dias). Escopo `https://www.googleapis.com/auth/adwords`.
- Credenciais: `~/.config/limen/client_secret.json` (fora do repositório).
- MCC de teste: **1137051091** (`login-customer-id`). Conta cliente de teste: **4327030343** (`customer_id`).
- Campanhas (testAccount = true, métricas sempre zeradas):
  A `24444020070` ENABLED R$50/dia · B `24464752468` ENABLED R$80/dia · C `24458906837` PAUSED R$40/dia.
- API **v26** funcionando (Playground, 12/11): `listAccessibleCustomers` e `googleAds:search`.
  Evidência: `docs/evidencias/2026-11-12_IN-02_campanhas_api_parte*.png`.
- Desenho: **API real para autorização e estrutura das campanhas; métricas sintéticas**
  (contas de teste não veiculam), associadas aos IDs reais e marcadas `origem='sintetica'`.

## Situação (13/11/2026, atualizado após a Fase 0 do dashboard)

Feito: tabela congelada (`29de91d`) · motor + 45 testes (`cfb8ac0`) · banco + migração
(`6aa88ba`) · API REST (`1e22777`) · OAuth + cifragem (`f49faf9`) · sincronização campanhas
(sub-etapas 3 e 4 concluídas) · métricas sintéticas nas campanhas reais (IN-02b, `0cf461e`) ·
Fase 0 do dashboard (backend). Total **211 testes passando** (13/11, após a Fase 0).

**Dashboard — plano aprovado (13/11/2026):** React + TypeScript (Vite), Tailwind v4,
shadcn/ui, lucide, Recharts, TanStack Query, React Router, react-hook-form + zod, sonner.
Destaque índigo; R1 âmbar, R2 rosa, R3 violeta (sempre com código e ícone); Inter
auto-hospedada; claro/escuro/sistema. Proxy do Vite: `/api/oauth/*` → 8080 sem reescrever;
demais `/api/*` → 8080 sem o prefixo (evita colisão com as rotas do React). Tipos gerados
do `openapi.json` (`openapi-typescript` + `openapi-fetch`). Ponta a ponta com Playwright
contra o backend real num banco de teste preparado por script (login Google validado à mão).
Fases: 0 backend ✅ → 1 base visual (aprovação do visual) → 2 campanhas → 3 regras e
avaliações → 4 alertas, acessibilidade, ponta a ponta, evidências. Plano de corte (se
atrasar) vale só para o dashboard, **nunca** para os testes de desempenho e a execução da
tabela.
- ✅ Fase 0 (backend do dashboard): `tipo` nos erros, callback → `URL_FRONTEND`, `GET /eu`,
  `POST /sessao/sair`, migração 0003 + `GET /avaliacoes`, `GET /resumo`. 46 testes novos
  (tipo 16, OAuth 2, sessão 6, histórico 12, resumo 10); os 165 anteriores sem alteração.
  Migração 0003 aplicada no `limen` (13/11): as 2 avaliações reais do IN-02b ficaram com
  parâmetros NULL, números inalterados. Evidência:
  `docs/evidencias/2026-11-13_fase0_dashboard_pytest.txt` (211/211).

**Integração Google Ads — estado (13/11/2026):**
- ✅ Sub-etapa 1: Login OAuth (CSRF + PKCE S256, `email_verified`)
- ✅ Sub-etapa 2: Refresh token cifrado em `Usuario.refresh_token_cifrado` (Fernet)
- ✅ Sub-etapa 3: Sincronização de campanhas — 109/109 passando + caso IN-02 aprovado.
  Evidências (12/11): `2026-11-12_IN-02_sincronizacao_real.png` (endpoint retornou
  `{"campanhas_sincronizadas": 3}`) e `2026-11-12_IN-02_campanhas_banco.png` (banco limen:
  campanhas A ENABLED 50 M, B ENABLED 80 M, C PAUSED 40 M com IDs reais e
  sincronizada_em = 2026-11-12 19:29:24 UTC).
- ✅ Sub-etapa 4: Falhas simuladas — IN-03 a IN-06 aprovados por testes com dublê da porta
  (a tabela define esses casos como "Simulada"). 131/131 passando. Evidência:
  `2026-11-12_etapa4_falhas_pytest.txt`.
- ✅ IN-02b: Métricas sintéticas associadas às campanhas reais sincronizadas — aprovado
  (13/11). Testes: 34 novos (gerador 16, semeador 9, API 9), incluindo
  `test_in02b_resultado_da_tabela`; 165/165 passando. Execução real no banco `limen`,
  todos os números iguais ao esperado: `POST /dev/metricas-sinteticas` → 200, lote
  `in02b-s20261112`, 13/10 a 11/11/2026, 30 inseridos em A, B e C (segunda execução:
  0 inseridos, 30 já existentes); banco com 3 campanhas de IDs reais, origem `sintetica`,
  30 dias cada; `POST /avaliacoes {}` → 60 avaliados, 0 rejeitados, 18 alertas
  (A 3/3/3, B 3/3/3, C 0/0/0), `duracao_motor_ms` 0.504; `POST /avaliacoes
  {"incluir_pausadas": true}` → 90 avaliados, 9 gerados, 18 já existentes (C 3/3/3).
  Evidências: `docs/evidencias/2026-11-13_IN-02b_*` (pytest.txt, precondicao_sincronizacao,
  semeadura_resposta, semeadura_idempotente, metricas_banco, avaliacao_ativas,
  alertas_ativas, avaliacao_com_pausadas, alertas_com_pausadas).

Depois: dashboard (React) → testes de desempenho (aba Desempenho: 5 aquecimentos,
30 repetições, 9 combinações volume × regras, 4 endpoints; tempo do motor medido isolado)
→ execução completa da planilha → README → relatório técnico.

## Registro de decisões (para o relatório técnico)

- **Método**: tabela de resultados esperados congelada antes do código; os testes do motor
  leem a própria tabela como oráculo (método dedutivo). Teste garante que os limiares do
  código = limiares da tabela. Mutação `<`→`<=` foi detectada por FM-01, FM-04 e FM-07.
- **Motor**: função pura `avaliar(registro, regras)`; regra = condições (métrica, operador,
  limiar) ligadas por E → novas regras por configuração. CTR em %, CPC em R$, `Decimal`.
  Ausente ≠ zero; razão com denominador ausente/zero é indefinida (N/A). Se qualquer
  métrica da regra é indefinida, a regra é N/A (independe da ordem das condições).
  Conversões em `Decimal` (Google Ads admite fracionárias).
- **Banco**: CTR/CPC não são colunas (3FN) — view `vw_metrica_diaria`, mesma política do
  motor (NULLIF). CHECKs repetem a validação (defesa em profundidade). UNIQUE
  (campanha, data) e UNIQUE (regra, registro) no alerta. Alerta guarda cópia das condições
  e valores medidos. Regras são desativadas, não apagadas. Migração testada nos dois sentidos.
- **API**: mesma função `validar_registro` em motor, API (Pydantic) e banco (CHECK).
  Ingestão em lote "tudo ou nada"; dia repetido → 409. `duracao_motor_ms` mede só o motor.
  `ON CONFLICT DO NOTHING` evita alerta duplicado (IN-11). Campanha pausada não é avaliada
  por padrão (`incluir_pausadas`). Decimais saem como texto no JSON. Rotas `/dev/*` só em
  desenvolvimento. Teste `test_fluxo_tabela` leva os 20 casos válidos da tabela pela
  aplicação inteira e compara os alertas gravados com o esperado.
- **Versões** (12/11): FastAPI 0.162.5, SQLAlchemy 2.1.8, Alembic 1.20.1, Pydantic 2.14.3,
  psycopg 3.3.9, pytest 9.1.1. Aviso conhecido: Starlette recomenda `httpx2` no TestClient
  (inofensivo, adiado).
- **OAuth — credenciais Google**: `GOOGLE_CLIENT_SECRET_FILE` no `.env` aponta para
  `~/.config/limen/client_secret.json` (fora do repositório). A aplicação lê o arquivo
  em tempo de execução via `configuracoes.credenciais_google` (property em `app/config.py`).
  Decisão: o segredo nunca passa pela conversa nem fica duplicado no `.env`. Testes fazem
  mock da property para não depender do arquivo. Alternativa descartada: copiar client_id
  e client_secret direto no `.env` — isso duplica o segredo e o expõe em conversas de IA.
- **OAuth — fluxo de login**: rotas `GET /api/oauth/google/login` e
  `GET /api/oauth/google/callback` (prefix `/api/oauth` para bater com a URI cadastrada no
  Google Cloud: `http://localhost:8080/api/oauth/google/callback`). Proteção CSRF via
  parâmetro `state` (aleatório, gravado na sessão, consumido uma única vez). PKCE S256
  (RFC 7636, recomendado pela RFC 9700 para todas as aplicações web): `code_verifier`
  (64 chars URL-safe) gerado em `/login` e guardado na sessão; `code_challenge =
  BASE64URL(SHA-256(verifier))` enviado ao Google; `code_verifier` enviado na troca do
  código — impede interceptação do authorization code. `email_verified` obrigatório:
  recusa contas Google com e-mail não confirmado. Sessão limpa antes de gravar
  `usuario_id`. Usuário identificado pelo e-mail (único); primeiro login cria o usuário e
  as regras padrão; re-login atualiza o nome. Refresh token armazenado cifrado em
  `Usuario.refresh_token_cifrado` (ver decisão abaixo). Redirecionava para `/docs`; desde
  a Fase 0 do dashboard, redireciona para `URL_FRONTEND` (ver decisão abaixo).
  Uvicorn deve rodar na porta 8080 (`--port 8080`) para bater com a URI cadastrada.
- **OAuth — refresh token cifrado** (migration 0002): token armazenado em
  `usuario.refresh_token_cifrado` (não em `conta_google_ads`). Decisão: fonte única —
  o token autoriza o *usuário*, não a conta; `ContaGoogleAds` lê pela FK em vez de guardar
  cópia. Coluna `conta_google_ads.refresh_token_cifrado` removida na migration 0002
  (downgrade a restaura). Cifragem: Fernet (AES-128-CBC + HMAC-SHA256,
  `app/servicos/cifra.py`); chave em `CHAVE_CIFRAGEM` no `.env` (`str | None = None` —
  ausente ou inválida levanta `ValueError` com instrução de como gerar, sem default
  silencioso). Fernet garante autenticação do ciphertext (adulteração levanta
  `InvalidToken`). IV aleatório a cada `cifrar()`: dois tokens idênticos → ciphertexts
  distintos. Google obrigado a devolver `refresh_token` (`prompt=consent`); ausente
  levanta 400 e nenhum usuário é criado. Alternativa descartada: duplicar o token em
  `conta_google_ads` — dois locais = risco de desincronização.
- **OpenAPI**: `app.openapi()` sobrescrito em `main.py` para substituir 422 → 400 em
  todos os endpoints (IN-09). Alternativa descartada: `responses=` em cada rota —
  verboso e fácil de esquecer em rotas novas.
- **Sincronização Google Ads — `TokenGoogleAusente`**: exceção própria em `servicos/erros.py`
  lançada pelo sincronizador quando `refresh_token_cifrado` é None; tratada em `main.py` com
  409 (estado inconsistente do usuário). Alternativa descartada: verificação duplicada no
  endpoint com HTTPException — criava dois pontos de falha e confundia com o `ValueError` de
  chave de cifragem inválida.
- **Sincronização Google Ads — `ids_google_ads`**: property em `Configuracoes` valida
  `GOOGLE_CUSTOMER_ID` e `GOOGLE_LOGIN_CUSTOMER_ID` (exatamente 10 dígitos; `str | None = None`
  sem default string). Levanta `ValueError` com instrução clara sobre qual variável configurar
  — mesmo padrão da `chave_cifragem`. Testada isoladamente (sem banco).
- **Sincronização Google Ads — `CampanhaGoogle` imutável**: `@dataclass(frozen=True)` em
  `interface.py`, coerente com o padrão do motor (`RegistroMetricas` também é imutável).
  Instâncias não podem ser alteradas após criação, o que evita mutações acidentais no
  sincronizador ou nos testes. Alternativa descartada: dataclass mutável — sem vantagem
  concreta nesse contexto.
- **Sincronização Google Ads — `_orcamento(amount_micros, resource_name)`**: função pura em
  `cliente_real.py`; retorna `None` apenas quando `resource_name == ""` (sem orçamento
  vinculado). `0` é orçamento válido e é mantido como `0` (ausente ≠ zero, coerente com
  a política do motor). Testada sem banco e sem Google.
- **Sincronização Google Ads — biblioteca**: `google-ads==35.1.0` (padrão v26,
  `developer_token` em `_OPTIONAL_KEYS` — não enviado quando ausente, compatível com a
  descontinuação de 09/09/2026). Alternativa descartada: httpx REST direto (Playground) —
  funcionaria, mas exigiria gerenciar o ciclo de vida do `access_token` manualmente; a
  biblioteca faz isso automaticamente a partir do `refresh_token`.
- **Sincronização Google Ads — interface (porta)**: `app/servicos/sincronizacao/interface.py`
  define `CampanhaGoogle` (dataclass) e `PortaGoogleAds` (Protocol). A porta retorna objetos
  do projeto, não da biblioteca; sincronizador e testes são independentes do `google-ads`.
  Implementação real: `ClienteRealGoogleAds` (import lazy — não quebra testes sem a lib).
  Dublê: `PortaFalsa` em `tests/test_sincronizacao.py`.
- **Sincronização Google Ads — idempotência**: `INSERT … ON CONFLICT DO UPDATE` na constraint
  `uq_campanha_conta_google_id` — rodar duas vezes atualiza sem duplicar. Status fora de
  ENABLED/PAUSED/REMOVED normalizado para UNKNOWN antes de gravar (defesa em profundidade
  contra futuros valores da API). `ContaGoogleAds` criada ou reaproveitada por
  `(usuario_id, customer_id)`. Token decifrado só no momento da chamada, nunca logado.
  Endpoint: `POST /campanhas/sincronizar` (usuário logado).
- **Variáveis de ambiente (não segredos)**: `GOOGLE_CUSTOMER_ID=4327030343` (conta cliente),
  `GOOGLE_LOGIN_CUSTOMER_ID=1137051091` (MCC). Lidas em `configuracoes.google_customer_id`
  e `configuracoes.google_login_customer_id`.
- **Falhas simuladas (sub-etapa 4) — hierarquia de exceções**: `ErroGoogleAds` (base, HTTP
  502) → `TokenExpirado` (503), `TokenRevogado` (409), `ApiIndisponivel` (503),
  `CotaExcedida` (503 + `Retry-After: 3600`). `GoogleAdsException` **não** herda de
  `grpc.RpcError` (confirmado por inspeção do venv) — por isso é capturada em ramo próprio
  com `except GoogleAdsException`.
- **Falhas simuladas — classificação de erros gRPC**: `invalid_grant` verificado nos
  detalhes **antes** do status code — pode vir disfarçado como UNAVAILABLE ou UNAUTHENTICATED.
  Apenas UNAVAILABLE e DEADLINE_EXCEEDED entram no loop de retry (IN-05). RESOURCE_EXHAUSTED
  → `CotaExcedida` sem retry (IN-06). Qualquer outro código → `ErroGoogleAds` genérico
  (HTTP 502), também sem retry. Alternativa descartada: tratar todos os erros gRPC como
  transitórios — oculta falhas permanentes de configuração (ex.: PERMISSION_DENIED).
- **Falhas simuladas — retryable=False por padrão**: `google.auth.exceptions.RefreshError`
  com `retryable=False` → `TokenRevogado`. Na dúvida, pede reautorização (política
  conservadora). `retryable=True` → `TokenExpirado` (falha temporária, repete uma vez sem
  espera). Alternativa descartada: tratar toda `RefreshError` como recuperável — mascararia
  `invalid_grant` e tentaria renovar sem chance de sucesso, atrasando o pedido de reautorização.
- **Falhas simuladas — porta chamada antes do banco**: `sincronizar()` chama
  `porta.listar_campanhas()` **antes** de criar `ContaGoogleAds` ou executar qualquer
  `flush/commit`. Se a porta falhar, o banco fica intacto. `TokenRevogado` é capturado após
  os laços: apaga `usuario.refresh_token_cifrado` e faz `commit` isolado (só isso), depois
  repropaga. A próxima chamada já cai em `TokenGoogleAusente` (409).
- **Falhas simuladas — retries aninhados**: laço externo (`TokenExpirado`, `range(2)`) sobre
  laço interno (`ApiIndisponivel`, `range(1 + tentativas_indisp=3)`). Pior caso:
  2 × 4 = 8 chamadas à porta. Espera crescente injetável (`espera: Callable[[int], None]`,
  default `time.sleep`): 1 s, 2 s, 4 s entre as tentativas de IN-05. `CotaExcedida` e
  `ErroGoogleAds` genérico saem imediatamente de ambos os laços. Alternativa descartada:
  retry único sem distinção de tipo — CotaExcedida e PERMISSION_DENIED não se beneficiam
  de retry e apenas atrasariam a resposta de erro.
- **Falhas simuladas — logging sem token**: `logging.getLogger(__name__)` em
  `sincronizador.py`. Logs incluem o caso (IN-03 a IN-06), tipo da falha e código da API
  quando disponível; nunca o valor do refresh token. Testado via `caplog` do pytest.
- **Falhas simuladas — handlers HTTP (main.py)**: `TokenRevogado` → 409 (não 401; 401 é
  "não logado no Limen"); `TokenExpirado` → 503; `ApiIndisponivel` → 503; `CotaExcedida`
  → 503 + `Retry-After: 3600`; `ErroGoogleAds` base → 502. Se `codigo` for None,
  o trecho `[codigo]` é omitido do `detail` (sem `[None]`). Os handlers específicos
  prevalecem sobre o handler base porque o FastAPI/Starlette escolhe o handler pela classe
  mais específica da exceção (MRO), não por ordem de registro.
- **IN-02b — gerador puro e reproduzível** (`app/servicos/sinteticas/gerador.py`): sem
  banco, rede ou relógio. Um `random.Random` por campanha, semeado com
  `"semente:google_campaign_id"` (semente padrão 20261112): incluir ou remover campanha
  não altera as demais. Só `rng.random()` é usado (a documentação do Python garante essa
  sequência entre versões; `randint`/`choice`/`shuffle` não), com sorteio de inteiros e
  Fisher-Yates próprios. Nenhum float: sorteiam-se inteiros (impressões, pontos-base de CTR,
  centavos de CPC) e o custo vira `Decimal` com 2 casas (`scaleb(-2)`). Período fixo
  13/10 a 11/11/2026 (30 dias, sem `date.today()`); 3 campanhas × 30 = 90 registros.
  O nome do lote registra a semente (`in02b-s20261112`). Um teste guarda o SHA-256 do
  conjunto padrão: se a geração mudar, falha (gerar novo lote em vez de alterar o hash).
- **IN-02b — perfis com quantidade fixa**: em cada campanha, 21 dias normais + 3 "CTR
  baixo" (R1) + 3 "CPC alto" (R2) + 3 "custo sem conversão" (R3); a semente só decide em
  que dias caem. Faixas longe dos limiares da tabela, então cada perfil dispara só a sua
  regra (testado com os limiares lidos da tabela). Resultado esperado conhecido: 9 alertas
  por campanha avaliada.
- **IN-02b — orçamento ignorado na geração**: a R3 exige custo > R$ 100, mas a campanha A
  tem R$ 50/dia (teto de gasto do Google = 2× o diário = R$ 100). Decisão: ignorar o
  orçamento, pois os dados são declaradamente sintéticos e o teto de gasto não faz parte da
  tabela congelada. Limitação a declarar no artigo. Alternativa descartada: limitar o custo
  a 2× o orçamento (mais realista, mas a R3 nunca dispararia na A e o gerador passaria a
  depender de uma regra fora da tabela).
- **IN-02b — mesma validação, sem atalho**: o semeador valida cada registro com
  `validar_registro` (a mesma função que o `MetricaEntrada` da API chama) e grava pelo
  mesmo código do `POST /campanhas/{id}/metricas`; os CHECKs do banco continuam valendo.
  O gerador produz um dataclass próprio (`MetricaGerada`) em vez do esquema Pydantic,
  para não inverter a dependência entre camadas (`servicos` não importa de `api`).
- **IN-02b — `adicionar_` × `ingerir_` e transação única**: `ingerir_metricas_sinteticas`
  fazia commit por chamada; no laço do semeador, uma falha na 2ª campanha deixaria a 1ª
  gravada. Separado em `adicionar_metricas_sinteticas` (verificações + `flush`, que aciona
  CHECK/UNIQUE na hora; sem commit) e `ingerir_metricas_sinteticas` (chama a anterior +
  commit/rollback; comportamento do endpoint inalterado). O semeador chama `adicionar_`
  por campanha e faz um único `commit` no final, com `rollback` em qualquer falha.
  Tudo ou nada em duas camadas: (1) gera, valida e confere conflitos de todas as campanhas
  antes de gravar; (2) transação única cobre o que (1) não prevê (ex.: CHECK do banco).
  Alternativa descartada: `begin_nested` dentro da função antiga (manteria commits no meio
  do laço e esconderia onde a transação começa e termina).
- **IN-02b — teste de mutação da transação**: `test_falha_na_segunda_campanha_nao_deixa_a_
  primeira_no_banco` provoca falha real do CHECK `ck_metrica_cliques_ate_impressoes` na
  campanha B (validação Python desligada só nesse teste) e usa um espião para provar que A
  chegou a ser gravada (flush) antes da falha. Com o mutante "commit por campanha"
  (aplicado só em memória), o teste reprovou com `assert 30 == 0`: os 30 registros de A
  sobravam no banco.
- **IN-02b — idempotência por lote**: por campanha, o semeador classifica o período como
  vazio (grava), completo com o mesmo lote (pula; conta em `ja_existentes`) ou conflito
  (dias de outro lote ou período incompleto → `ConflitoDados`, HTTP 409, nada gravado).
  Alternativa descartada: `ON CONFLICT DO NOTHING`, que misturaria lotes em silêncio.
  Só recebem métricas as campanhas vindas da sincronização (`sincronizada_em` preenchido)
  e não REMOVED; sem nenhuma → 409 (pré-condição IN-02 não cumprida). Campanha PAUSED
  recebe métricas; quem decide avaliá-la é `incluir_pausadas`.
- **IN-02b — rota `POST /dev/metricas-sinteticas`**: no roteador `/dev`, que `criar_app()`
  só inclui com `AMBIENTE=desenvolvimento` (fora dele, 404: a rota nem é registrada).
  Exige login com `obter_usuario_atual` (401 sem sessão), a mesma dependência das rotas
  autenticadas (`/dev/login` e `/dev/logout` não usam dependência de usuário). Parâmetros
  opcionais `semente`, `inicio`, `dias` (9 a 3660; inválido → 400). Os 4 endpoints fixos
  não foram alterados. Testes da rota montam a própria aplicação com `criar_app()` e o
  AMBIENTE controlado, para o 404 ser real e nada depender do `.env`.
- **IN-02b — oráculo do teste literal**: `test_in02b_resultado_da_tabela` lê a linha IN-02b
  da planilha e confere o texto; cumpre a pré-condição pelo `POST /campanhas/sincronizar`
  (dublê `PortaFalsa` com os IDs reais) e verifica cada parte do resultado esperado:
  (a) ID real, (b) `origem='sintetica'` e lote, (c) motor avalia normalmente — 0 rejeitados,
  A=9/B=9/C=0 e C=9 com `incluir_pausadas`, e o conjunto exato (campanha, dia, regra)
  igual ao calculado pelo motor puro com os limiares da tabela. O IN-02b verifica a
  integração; a correção das regras é coberta pelos casos RA/FM.
- **Fase 0 — `tipo` nos erros**: formato único `{"detail": ..., "tipo": ...}` montado por
  `_erro()` em `main.py`; o `detail` não mudou (os 165 testes anteriores passaram sem
  alteração). Valores: 400 `validacao` (o `tipo` interno de cada item da lista é o do
  Pydantic) e `requisicao_invalida`; 401 `nao_autenticado`; 404 `nao_encontrado`; 409
  `conflito`, `token_google_ausente`, `token_google_revogado`; 502 `erro_google_ads`; 503
  `google_autenticacao_temporaria`, `google_ads_indisponivel`, `cota_excedida` (mantém
  `Retry-After: 3600`); outros `erro_http`. Handler para `StarletteHTTPException` cobre
  também os 404/405 do roteador e preserva os cabeçalhos (`Allow` do 405 testado). Motivo:
  dois 409 pedem ações diferentes no frontend (regra duplicada × reconectar o Google) sem
  depender do texto. Alternativa descartada: `tipo` à mão em cada handler (formato repetido
  10 vezes). Testes: caminhos reais quando é possível provocar o erro; para os erros do
  Google, uma aplicação própria do teste (`criar_app()`) com rota que levanta cada exceção.
- **Fase 0 — callback → `URL_FRONTEND`**: `url_frontend` em `Configuracoes` (padrão
  `http://localhost:5173/`; não é segredo, por isso tem padrão). O destino vem só da
  configuração, nunca de parâmetro da URL (evita redirecionamento aberto). Erros do
  callback continuam 400 em JSON. Alternativa descartada: redirecionar erros para
  `/entrar?erro=…` (mais amigável, mas mudaria 8 testes do IN-01 por um caso raro). Os 14
  testes de OAuth não conferiam o destino; 2 novos conferem o `Location` (com valor
  trocado por monkeypatch) e o padrão.
- **Fase 0 — `GET /eu` e `POST /sessao/sair`**: `/eu` devolve id, nome, e-mail,
  `google_conectado` (existe refresh token?) e `conta_google_ads` (null até a primeira
  sincronização; a mais recente se houver mais de uma). Nunca devolve o token: o teste
  procura no corpo o texto do token cifrado e qualquer chave com "token". Depois de
  `TokenRevogado`, `google_conectado=false` e a conta continua. `/sessao/sair` limpa a
  sessão e devolve 204, mesmo sem login (idempotente); testado com sessão de verdade
  aberta por `/dev/login`, sem sobrescrever o usuário.
- **Fase 0 — migração 0003 (parâmetros da avaliação)**: `avaliacao` ganha
  `incluir_pausadas`, `campanha_id`, `inicio`, `fim`, todos NULL. NULL = "não registrado"
  nas avaliações anteriores à 0003, e não `false`, que seria falso para a execução real
  com pausadas (ausente ≠ zero). `campanha_id` com FK `ON DELETE SET NULL` (o histórico
  sobrevive à remoção da campanha). CHECK `ck_avaliacao_periodo` (`inicio <= fim`) repete
  a validação do `AvaliacaoEntrada`, e um teste prova que o banco recusa sozinho. SQL
  revisado em modo offline (`alembic upgrade 0002:0003 --sql`) antes de aplicar no
  `limen`. `POST /avaliacoes` (endpoint fixo) grava os parâmetros; a resposta só ganha
  campos (nome e corpo inalterados). Motivo: sem isso o histórico não explica 60 × 90
  avaliados.
- **Fase 0 — `GET /avaliacoes`**: histórico do usuário, mais recente primeiro (desempate
  por id, porque `now()` do PostgreSQL é o mesmo dentro de uma transação); `limite` 1 a
  500 (inválido → 400 `validacao`).
- **Fase 0 — `GET /resumo`**: campanhas por status (todos os status, mesmo com 0), regras
  (total/ativas), métricas no período (registros, primeira e última data, por origem),
  alertas por regra e por dia, última avaliação. Tudo agregado no banco (`GROUP BY`).
  Alertas por regra com `LEFT JOIN` de uma subconsulta já filtrada pelo período: o filtro
  no WHERE externo faria sumir as regras sem alerta. `por_dia` traz só os dias com alerta
  (o frontend preenche os vazios). O período filtra métricas e alertas pela data do
  registro; campanhas, regras e última avaliação não dependem dele. Período invertido →
  400 `requisicao_invalida` (checado na rota). Oráculo do teste: totais por dia e por
  regra iguais à contagem sobre `GET /alertas` (endpoint fixo). Números com os dados do
  IN-02b: 18 alertas (6/6/6) só com ativas; 27 (9/9/9) com pausadas. Alternativa
  descartada: contar no navegador (truncaria no limite de 5.000 alertas; a base de
  desempenho tem 10.000 registros).
- **Fase 1 — instalação do frontend (13/11)**: versões conferidas com `npm view` no dia e
  fixadas exatas (`.npmrc` com `save-exact=true` e `engine-strict=true`; `package-lock.json`
  no git): React 19.3.1, Vite 8.3.8, @vitejs/plugin-react 6.3.0, Tailwind 4.3.5, React Router
  8.5.1, TanStack Query 5.107.1, openapi-fetch 0.17.0 / openapi-typescript 7.13.0, Recharts
  3.10.1, zod 4.6.7, react-hook-form 7.92.0, lucide-react 1.72.0, sonner 2.0.8, radix-ui
  1.8.1, Inter (@fontsource-variable) 5.3.0, ESLint 10.14.0, Vitest 5.1.0. Node 24.14.1.
  **TypeScript 5.9.3, não 7.0.2**: o `openapi-typescript` exige `^5.x` e o `typescript-eslint`
  `<6.1`; a 6.0.3 resolveria só o ESLint. `@types/node` 24.x (mesma versão maior do Node).
  Projeto montado à mão (não `npm create vite`, que impõe versões próprias). Vitest só para
  funções puras (`environment: node`, sem jsdom/Testing Library); interface fica com o
  Playwright (Fase 4). `npm audit`: 10 moderadas, todas do `minimatch` dentro do
  ESLint/typescript-eslint (só desenvolvimento; `--omit=dev` → 0). Aceitas e registradas:
  a correção é o `minimatch` 11, fora da faixa `^10` que o ESLint declara;
  `npm audit fix --force` rebaixaria o ESLint para 9. Proxy do Vite: `/api/oauth` antes de
  `/api` (o Vite usa a primeira chave que casa). Cookie de sessão é por host, não por porta:
  a sessão criada no callback (8080) vale no Vite (5173).
- **Fase 1 — shadcn/ui (13/11)**: `shadcn@4.23.0 init --base radix --preset nova` (estilo
  `radix-nova`, ícones lucide). Sem `--preset` o CLI abre um menu interativo; sem
  `src/index.css` com `@import "tailwindcss"` ele não reconhece o Tailwind v4 (não há arquivo
  de configuração). O init pôs a fonte Geist (`@fontsource-variable/geist`), removida e trocada
  pela Inter, e pôs `shadcn` em `dependencies`; movido para `devDependencies` (o app só usa o
  arquivo `shadcn/tailwind.css`, que o Vite embute no CSS; o CLI não vai para o navegador).
  **`cn` no lugar de `clsx` + `tailwind-merge`**: o shadcn 4.23 gera `export { cn } from "cn"`
  e os componentes importam `cn` direto. Verificado com `npm view` em 13/11: pacote `cn`
  0.5.2 (publicado em 02/11/2026), mantenedor `shadcn <m@shadcn.com>`, repositório
  `github.com/shadcn-ui/cn`, licença MIT, existe desde 22/09/2026. Por ser 0.x e novo,
  `src/lib/utils.test.ts` guarda o comportamento usado (`cn("px-2","px-4") === "px-4"`,
  valores falsos ignorados, `className` externo vence). `clsx` e `tailwind-merge` removidos
  só depois de um grep não achar nenhum import; o `clsx` segue como dependência indireta de
  `class-variance-authority` e `recharts`. Alternativa descartada: manter `clsx` +
  `tailwind-merge` reescrevendo o `utils.ts` (cada `shadcn add` voltaria a instalar `cn`).
  **`npm audit`**: total foi de 10 para 15 (2 baixas, 13 moderadas): as 5 novas vêm do CLI do
  shadcn (`deepmerge`, outra cópia do `minimatch`); todas só de desenvolvimento,
  `npm audit --omit=dev` → 0. Componentes gerados (`src/components/ui/`) não são editados, para
  continuarem iguais ao registro; por isso a regra `react-refresh/only-export-components`
  está desligada só nessa pasta (eles exportam `buttonVariants`/`badgeVariants`).
- **Fase 1 — tokens (13/11)**: `src/index.css` é a fonte da verdade. OKLCH, todas as cores
  dentro da gama sRGB (fora dela o navegador ajusta a cor e o contraste calculado deixa de
  valer). Neutros com matiz 264; índigo 277 (claro `0.51 0.225`, branco por cima; escuro
  `0.72 0.14`, texto escuro por cima, porque também serve de link). Regras: forte (ícone,
  texto, gráfico) + suave (fundo do selo): R1 âmbar 55/80, R2 rosa 355, R3 violeta 302
  (afastado do índigo 277). Âmbar no claro fica queimado (`0.53`): o âmbar vivo dá ~2:1.
  Borda de campo (`--input`, 3:1, WCAG 1.4.11) separada da borda decorativa (`--border`).
  `--chart-1..3` = R1..R3. **Oráculo**: `contraste.test.ts` lê `:root` e `.dark` do CSS,
  resolve `var()` e exige ≥ 4,5:1 para 8 tokens de texto × 4 superfícies, cada regra sobre o
  próprio fundo suave, `primary-foreground` sobre `primary`, ≥ 3:1 para `input` e `ring`, e
  `text-destructive` sobre `bg-destructive/10` (claro) e `/20` (escuro), compondo a
  transparência como o navegador. Ele pegou dois pares que a conta manual do plano não
  cobria (ajustados): `--input` claro sobre o fundo da página deu 2,98 (L 0,66 → 0,65) e
  `text-destructive` sobre `bg-destructive/10` deu 4,40 (L 0,55 → 0,53). O estilo Nova usa
  `destructive` como texto, nunca branco por cima, por isso o destructive escuro é um
  vermelho claro. Mutação: R1 clara (L 0,70) → 5 testes reprovaram.
  **Ajuste do tema escuro após ver a vitrine (13/11)**: o cartão quase sumia no fundo.
  `--card`/`--popover` 0,205 → 0,235; `--border` 0,30 → 0,33 (mesma distância do cartão);
  `--muted`/`--accent`/`--secondary` 0,25 → 0,28, porque a 0,25 ficavam quase iguais ao
  cartão novo (razão 1,04) e o hover do menu sumia. Resultado: degraus iguais, fundo 0,165 <
  cartão 0,235 < suave 0,28 (razões 1,16 e 1,14). Simulado antes de editar (0,27/0,28/0,29):
  a 0,28 o pior texto sobre `--muted` fica 5,67 (`muted-foreground`). O teste reprovou
  `text-destructive` sobre `bg-destructive/20` no cartão novo (4,41); destructive escuro de
  `0.71 0.17 22` para `0.73 0.16 22` (4,66). Alternativa descartada: cartão 0,225 com o
  vermelho antigo (4,53, folga mínima e degrau menor). `contraste.test.ts` não foi alterado.
- **Fase 1 — tema (13/11)**: preferência `claro | escuro | sistema` em `localStorage`
  (`limen:tema`); inválida ou armazenamento bloqueado → `sistema`, sem erro. Classe `dark` no
  `<html>` + `color-scheme`. Anti-flash no `index.html`: `<script id="tema-inicial">` (ES5,
  `try/catch`) aplica o tema antes da primeira pintura e `<style id="fundo-inicial">` pinta o
  fundo antes do CSS (no dev o Vite injeta o CSS por JS). A lógica fica em dois lugares (script
  e `tema.ts`); `script-inline.test.ts` executa o script do HTML com `node:vm` (localStorage e
  matchMedia falsos, que só respondem à chave e à consulta certas) em 12 combinações e compara
  com `tema.ts`; `contraste.test.ts` confere que o `<style>` usa o mesmo `--background`.
  `ProvedorTema` acompanha a troca do sistema (`useSyncExternalStore` sobre `matchMedia`) e de
  outras abas (evento `storage`). Testes com APIs do Node têm `tsconfig.test.json` próprio:
  o código da aplicação continua sem tipos do Node.
- **Fase 1 — selos de regra (13/11)**: `aparenciaDaRegra(codigo)` (pura) → tom, ícone
  (R1 `MousePointerClick`, R2 `Coins`, R3 `Target`, outras `Bell`), classes literais (o
  Tailwind só gera classes que encontra escritas no código) e `corCss` para o Recharts.
  Código exato e `Object.hasOwn` ("r1", "R4", "toString", "__proto__" → neutro). `SeloRegra`
  sempre mostra ícone (`aria-hidden`) + código; nome opcional (da API ou padrão da tabela).
  Vitrine provisória (`src/paginas/Vitrine.tsx`) para aprovar o visual; sai com o roteador.
  Vitest: 145 testes em 6 arquivos (contraste 92, script inline 13, tema 21, aparência 12,
  cn 4, favicon 3), medidos em 13/11.
- **Fase 1 — KPI com 14 px (13/11)**: o `CardTitle` do shadcn traz
  `group-data-[size=sm]/card:text-sm`; essa variante tem especificidade maior que
  `.text-3xl` e o `cn` não a remove (é outra variante), então num `Card size="sm"` o número
  saía com 14 px. Correção fora de `components/ui`: repetir a variante com o tamanho certo
  (`group-data-[size=sm]/card:text-3xl`), que o `cn` substitui; teste em `utils.test.ts`.
- **Fase 1 — favicon (13/11)**: `public/favicon.svg`, "L" branco sobre `#4f47e2` (o
  `--primary` claro convertido por `contraste.ts`; hex porque favicon nem sempre entende
  `oklch`); resolve o 404 do `favicon.ico`. Bug encontrado no navegador: o comentário do
  SVG citava `--primary`, e em XML "--" é proibido dentro de comentário ("Comment must not
  contain '--'"), o que invalida o arquivo inteiro; reescrito como "token primary".
  `src/favicon.test.ts` guarda isso (arquivo começa com `<svg`, nenhum comentário contém
  "--", todo `<!--` fechado). Mutação: "token primary" → "--primary" na cópia de trabalho →
  "nenhum comentário contém '--'" reprovou (1 de 3); arquivo restaurado e conferido com `cmp`.
- **Fase 1, parte 2 — componentes do shadcn (13/11)**: `sheet`, `skeleton`, `separator`,
  `table` pelo CLI, um por vez, com `--dry-run` e `--view` antes (imports só de `react`,
  `radix-ui`, `lucide-react`, `cn`) e SHA-256 do `package.json`/lock antes e depois de cada
  um: inalterados. O CLI roda `npm install cn` sem versão; seguro porque o `cn` mais recente
  (`npm view`) é o 0.5.2 já fixado. `sonner` do shadcn não foi adicionado: importa
  `next-themes` (pacote novo e segundo controle de tema); `Notificacoes.tsx` usa o `Toaster`
  do sonner direto, com o nosso tema e rótulos em português. Nenhum pacote npm novo na parte 2.
- **Fase 1, parte 2 — cliente da API e erros (13/11)**: `src/api/esquema.d.ts` gerado por
  `npm run tipos:api` e **versionado** (build/typecheck sem backend; o diff mostra mudança de
  contrato). Mensagem e ação decididas pelo `tipo`, nunca pelo texto do `detail` (exceto
  `conflito`/`requisicao_invalida`, cujo `detail` o backend já escreve em português;
  `validacao` cita só os campos, porque o `msg` do Pydantic é em inglês). Com o backend
  parado, o proxy do Vite responde 502 `text/plain` vazio (conferido no código do Vite);
  502 sem `tipo` → `sem_conexao` (o 502 do backend sempre traz `erro_google_ads`). Fetch que
  lança → `sem_conexao`; AbortError passa adiante. `deveRepetir`: só `sem_conexao`,
  `google_ads_indisponivel` e `google_autenticacao_temporaria`, até 2 repetições (no TanStack
  a 1ª falha chega com `failureCount = 0`); nunca 4xx (401 incluso) nem `cota_excedida`
  (mesma lógica de IN-05/IN-06). **Oráculo** (`erros.test.ts`): lê todos os `.py` de
  `backend/app` (o `.env` não é lido: fica fora dessa pasta e não é `.py`), extrai os `tipo`
  de 4 formas e reprova se alguma chamada `_erro(...)` tiver um tipo que ele não sabe ler;
  exige mensagem para cada tipo e que toda mensagem seja de um tipo existente. Achou os 12 da
  Fase 0. Mutações: sem a mensagem de `token_google_revogado` → 2 reprovações; sem a barreira
  de 4xx no `deveRepetir` → "401 mesmo com tipo transitório" reprovou.
- **Fase 1, parte 2 — formatação (13/11)**: datas sem hora formatadas partindo o texto
  (`new Date("2026-11-11")` é meia-noite UTC e mostraria 10/11 no Brasil; o teste fixa
  `TZ=America/Fortaleza` e a mutação com `new Date` reprovou 7 casos); data e hora só com
  fuso explícito; decimais como texto, sem `parseFloat`. **`formatarInteiro` usa o mesmo
  `agruparMilhares` do `formatarDecimal`, não o Intl**: o agrupamento do Intl depende dos
  dados de localização do navegador (há locais que só agrupam a partir de 5 dígitos) e os
  testes rodam no Node. Teste exige `formatarInteiro(n) === formatarDecimal(String(n))`.
  Achado: a mutação com `minimumGroupingDigits: 2` sobreviveu porque essa opção não existe
  no `Intl.NumberFormat` (foi ignorada); a forma certa, `useGrouping: "min2"`, reprovou 5.
- **Fase 1, parte 2 — roteador e sessão (13/11)**: `createBrowserRouter`; caminhos em
  `src/rotas.ts` (teste: nenhum começa com `/api`, para não colidir com o proxy). Entrar é a
  única rota pública; as demais passam pela `RotaProtegida` (GET `/eu`) e ficam no `Layout`;
  o 404 fica dentro do layout (sem sessão, qualquer endereço leva a Entrar). `/eu` com 401 →
  Entrar; outro erro (backend parado) → tela de erro com "tentar de novo", e não Entrar,
  porque o problema não é falta de login. 401 em qualquer outra consulta → `invalidateQueries`
  de `/eu` (não `reset`: o último usuário fica em `data`, e é assim que a `RotaProtegida` sabe
  que a sessão terminou no meio do uso e Entrar avisa). Sair: `POST /sessao/sair` →
  `queryClient.clear()` (nada do usuário anterior em memória) → `/entrar`; nessa ordem, senão
  Entrar veria `/eu` ainda em cache e voltaria para "/". Alternativa descartada: `loader` do
  React Router chamando `/eu` (segundo cache paralelo ao TanStack Query).
  **Limitação (declarar no artigo): depois do login com Google, a aplicação volta sempre
  para "/", e não para a tela em que a pessoa estava.** O callback redireciona para
  `URL_FRONTEND`, que vem só da configuração; aceitar o destino por parâmetro da URL abriria
  um redirecionamento aberto (decisão da Fase 0). Vale também para sessão expirada e para
  "Reconectar Google".
- **Fase 1, parte 2 — layout e acessibilidade (13/11)**: barra lateral própria a partir de
  `md` (descartado o `sidebar` do shadcn: ~700 linhas, recolher para ícones, cookie, Ctrl+B);
  abaixo de `md`, a mesma `Navegacao` num `Sheet`. Item ativo: `aria-current="page"` (do
  `NavLink`) + `text-primary` sobre `bg-primary/10` + negrito (a cor não é o único sinal); par
  novo em `contraste.test.ts` sobre `--sidebar`, nos dois temas. "Pular para o conteúdo" é o
  primeiro focável e foca `<main id="conteudo" tabIndex={-1}>` sem pôr `#conteudo` na URL. Na
  troca de rota, o foco vai para o `h1` (`TituloPagina`, `tabIndex={-1}`) e o título da aba
  vira "Página · Limen"; o efeito compara com o caminho anterior (no StrictMode ele roda duas
  vezes na montagem e focaria o h1 na primeira carga). O `Sheet` gerado tem "Close" em inglês:
  desligado (`showCloseButton={false}`) e trocado por "Fechar menu". Fechar o `Sheet` por um
  link manda o foco ao h1, e não de volta ao botão do menu (padrão do Radix). Selo
  "Campanhas reais · Métricas sintéticas" em todas as larguras (no celular, numa segunda
  linha). `errorElement` próprio em português no lugar da página padrão do React Router.
  **Correções após o teste no navegador (13/11)**: (1) aviso "Blocked aria-hidden… descendant
  retained focus" ao navegar pelo menu do celular. Causa (conferida no código do Radix): o
  Sheet aplica `aria-hidden` no resto da página (`hideOthers`) e só o retira ao desmontar,
  depois da animação de fechar; o efeito do Layout focava o h1 no mesmo instante da troca de
  rota, ainda dentro da área escondida. O `onCloseAutoFocus` não era a causa: roda num
  `setTimeout` após a desmontagem. Correção: o Layout não foca se o h1 estiver dentro de
  `[aria-hidden="true"]` (o diálogo cuida do foco), e `anterior.current` é atualizado antes
  dessa saída. Descartados: atrasar com `setTimeout` (depende da duração da animação) e um
  contexto "menu aberto" (prende o Layout ao MenuCelular e a cada diálogo futuro).
  (2) "Pular para o conteúdo" sem espaçamento: `.focus\:not-sr-only:focus` zera o padding e
  tem especificidade maior que `.px-4`; o espaçamento passou para `focus:px-4 focus:py-2`
  (mesma especificidade, vem depois no CSS gerado), mais `focus:shadow-lg`.
  **Confirmado no navegador pelo Kauan (13/11)**: navegando para Campanhas pelo menu do
  celular, o console ficou vazio (sem o aviso de `aria-hidden`); Esc fecha o menu; o link
  "Pular para o conteúdo" aparece com espaçamento e sombra.
- **Pendências a mencionar no artigo**: declarar o uso de IA conforme regra do iCEV
  (confirmar com o orientador); justificar Liang et al. (2009) na seção 2.5; buscar fonte
  recente (IEEE/ACM, "rule engine evaluation"); deixar explícito na metodologia o que usou
  dado real × sintético.
