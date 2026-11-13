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
- **Pendências a mencionar no artigo**: declarar o uso de IA conforme regra do iCEV
  (confirmar com o orientador); justificar Liang et al. (2009) na seção 2.5; buscar fonte
  recente (IEEE/ACM, "rule engine evaluation"); deixar explícito na metodologia o que usou
  dado real × sintético.
