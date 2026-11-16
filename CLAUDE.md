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
- **Segredos fora do alcance**: nunca ler nem editar `backend/.env` nem nada em
  `~/.config/limen/`. Buscas de segredo só com `grep -l` (mostra o nome do arquivo,
  nunca a linha).
- **Critério do ✅**: uma etapa só é marcada ✅ com testes passando, mutação documentada
  (o que foi mudado, qual teste reprovou, arquivo restaurado e conferido) e execução real
  (no navegador, na API ou no banco, conforme a etapa).

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
pytest -q                                           # 438 testes passando em 16/11
alembic upgrade head
uvicorn app.main:app --reload --port 8080           # /docs; POST /dev/login (só em desenvolvimento)
pytest | tee ../docs/evidencias/AAAA-MM-DD_<etapa>_pytest.txt   # evidência antes do commit
# execução formal (banco limen_execucao; a URL vai no comando, nunca no .env)
DATABASE_URL=<url do limen_execucao, sem credenciais no documento> python -m execucao.<script>
python -m execucao.preencher_planilha --in10-dashboard sim   # sem banco; lê os .json
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
Fase 0 do dashboard (backend). Total **211 testes passando** (13/11, após a Fase 0);
**213** em 14/11, com o campo `alertas.avaliacoes` do `/resumo` (Fase 1, etapa 4).
✅ **Fase 1, etapa 4 — Visão geral (14/11)**: KPIs de `GET /resumo`, alertas por dia
(Recharts, cores das regras), alertas por regra e últimas avaliações de `GET /avaliacoes`,
com estados de carregando, vazio e erro. Teste no navegador aprovado pelo Kauan (8 itens).
pytest 213/213, Vitest 491/491. Evidências: `docs/evidencias/2026-11-14_fase1_visao-geral_*`.
✅ **Fase 1, etapa 5 — limpeza (14/11)**: Vitrine removida; teste do número do KPI ligado à
constante real (com mutação). Vitest 492/492, typecheck, lint e build ok. Execução real
aprovada pelo Kauan no navegador (KPIs com 30 px).
✅ **Fase 2, etapas 1 a 3 — telas Campanhas e Campanha (15/11)**: lista, sincronização e
métricas diárias. Teste no navegador aprovado pelo Kauan. Vitest 653/653, typecheck, lint e
build ok. Evidência: `docs/evidencias/2026-11-15_fase2_telas_vitest.txt`.
✅ **Fase 3, etapa 4 — tela de Regras (15/11)**: lista com ativar e desativar (R1 a R3 só
leitura), nova regra e edição com "Será salvo como" e erros do servidor nos campos.
Teste no navegador aprovado pelo Kauan. Vitest 893/893, typecheck, lint e build ok.
Evidência: `docs/evidencias/2026-11-15_fase3_regras_vitest.txt`.
✅ **Fase 3, etapa 5 — tela de Avaliações (15/11)**: executar avaliação (campanha, período,
incluir pausadas, aviso de pausada) e histórico com "não registrado" para os parâmetros
anteriores à 0003. Teste no navegador aprovado pelo Kauan. Vitest 950/950, typecheck, lint
e build ok. Evidência: `docs/evidencias/2026-11-15_fase3_avaliacoes_vitest.txt`.
✅ **Fase 4 — tela de Alertas (16/11)**: lista de `GET /alertas` com filtros por campanha,
regra e período guardados na URL, o que disparou (valor medido e limiar da cópia gravada no
alerta), aviso de limite e "Ver alertas" das Avaliações com campanha e período. Teste no
navegador aprovado pelo Kauan (8 itens). Vitest 1079/1079, typecheck, lint e build ok.
Evidência: `docs/evidencias/2026-11-16_fase4_alertas_vitest.txt`. Playwright fica para depois.
✅ **Execução formal da tabela congelada (16/11)**: banco `limen_execucao`, scripts em
`backend/execucao/` (commit `2fd5bcf`, código igual ao commit em todas as execuções).
Cenários: **23/23 corretos, 0 alertas indevidos, 0 omitidos** (aplicação e motor).
Integração: **12/12 conferem** (IN-01 e IN-02 reais refeitos no navegador; IN-10 conferido
no dashboard). Resumo da planilha recalculado no LibreOffice: 23 de 23, 0, 0, 12 de 12.
Evidências: `docs/evidencias/2026-11-16_execucao_*` e `_IN-01_*`, `_IN-02_*`, `_IN-10_*`.
✅ **Desempenho — scripts e testes (16/11, antes de medir)**: `backend/execucao/desempenho/`
(preparar, medir_motor, medir_endpoints, medir_google_ads, preencher_planilha) e 202 testes
novos; pytest **438/438**; 32 mutações, todas como previsto. Evidência:
`docs/evidencias/2026-11-16_desempenho_scripts_pytest.txt`.
✅ **Desempenho — medição (16/11)**: commit `970049d` em todas as medições (código fora do
commit: 0). Motor (DM) 9/9 e endpoints (DE) 4/4 sem falhas; Google Ads à parte, 30/30.
Planilha preenchida (66 células), coluna H recalculada no LibreOffice e conferida nas 13
linhas, sem salvar por cima. Evidências: `docs/evidencias/2026-11-16_desempenho_*`.

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

Depois: README → relatório técnico. (Dashboard, execução da planilha e desempenho concluídos.)

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
- **Fase 1, etapa 4 — `alertas.avaliacoes` no `/resumo` (14/11)**: o cartão
  de Alertas mostra 27, que soma alertas de duas execuções (18 da primeira + 9 da segunda,
  com pausadas); sem contexto seria confundido com os 18 da primeira. O `/resumo` não dizia
  quantas avaliações havia. Campo novo `alertas.avaliacoes` = `COUNT(DISTINCT
  alerta.avaliacao_id)` no banco, só das regras do usuário e no mesmo período dos alertas:
  são as avaliações que **geraram** os alertas contados. Descartados: (a) total de
  avaliações do usuário (contaria execuções sem alerta novo, por causa do `ON CONFLICT DO
  NOTHING`, e ignoraria o período: rodar de novo daria "27 alertas em 3 avaliações");
  (b) contar no navegador com `GET /avaliacoes?limite=500` (contradiz a decisão da Fase 0
  de agregar no banco; trunca acima de 500); (c) texto sem número. A resposta só ganha um
  campo; o nome do endpoint não muda. Testes: `test_resumo_vazio` ganhou
  `"avaliacoes": 0` (único teste antigo alterado, porque compara o dicionário inteiro);
  asserções de 1 (só ativas) e 2 (com pausadas), e oráculo independente no teste de
  período (`avaliacao_id` distintos em `GET /alertas`, endpoint fixo). Dois testes novos:
  `test_avaliacao_sem_alerta_novo_nao_conta` (3ª execução sem alerta novo: `GET
  /avaliacoes` tem 3, o campo continua 2) e `test_avaliacoes_de_outro_usuario_nao_contam`
  (segundo usuário com conta, campanha A, métricas e avaliação que gera 9 alertas; o banco
  fica com 36 alertas de 3 avaliações e o `/resumo` do primeiro continua 27 e 2). O
  `test_resumo_so_do_usuario` já existia, mas só cria regras do outro usuário, sem alertas:
  uma asserção ali passaria mesmo sem o filtro. **Mutação** (cópia no scratchpad, restaurada
  e conferida com `cmp` e `git diff`): sem o `.where(Regra.usuario_id == usuario_id)` da
  contagem nova, só `test_avaliacoes_de_outro_usuario_nao_contam` reprovou, com
  `(27, 3) == (27, 2)`. pytest: **213/213** (211 + 2). `esquema.d.ts` regenerado com o
  uvicorn em `--reload` (o `openapi.json` servido foi conferido antes): diff de 2 linhas,
  só `avaliacoes: number` em `ResumoAlertas`.
- **Fase 1, etapa 4 — cores do gráfico (14/11)**: paleta conferida com o validador da skill
  dataviz (`validate_palette.js`): faixa de luminosidade (claro L 0,43 a 0,77; escuro 0,48 a
  0,67), saturação mínima 0,10, separação sob daltonismo (CVD, ΔE ≥ 8; de 6 a 8 só com
  segunda codificação), distância em visão normal (ΔE OKLab ×100 ≥ 15) e contraste ≥ 3:1.
  **Claro**: as regras usam a própria cor de texto (`--chart-1..3 = var(--regra-r*)`); tudo
  passa (CVD pior 11,4, distância pior 18,5). **Escuro**: as cores de texto (L 0,75 a 0,82,
  claras para dar 4,5:1) reprovavam como barra (fora da faixa, e R2 × R3 a 13,9). Tons
  próprios com os mesmos matizes: `--chart-1 oklch(0.66 0.135 80)`, `--chart-2 oklch(0.56
  0.2 355)`, `--chart-3 oklch(0.66 0.19 302)`; passam em tudo (CVD 16,8, distância 20,1).
  Os tokens de texto `--regra-*` não mudaram. **`--chart-5`** (regras criadas pelo usuário):
  no claro era o `--muted-foreground` (L 0,50), a ΔE 6,4 do R2 sob protanopia; passou a
  `oklch(0.64 0.02 264)`, que dá CVD 8,1, 3,36:1 sobre o cartão, 3,22:1 sobre o fundo e
  distância mínima de 18,4 (a 0,66 o contraste sobre o fundo cai para 2,98). No escuro
  continua `var(--muted-foreground)` (CVD 14,2, distância 15,8 do R1). `aparencia.ts` ganhou
  `corGrafico` (`var(--chart-N)`; barra e amostra da legenda); `corCss` continua sendo a
  cor de texto. `contraste.ts` ganhou `deltaEOk`. **Testes em arquivos novos**, para
  `contraste.test.ts` e `aparencia.test.ts` ficarem idênticos ao commit (conferido com
  `git diff`). `grafico.test.ts` lê `--chart-1..5` do `index.css` (nenhuma cor repetida no
  teste) e confere, em cada tema: gama sRGB, ≥ 3:1 sobre `--card` e `--background`,
  distância ≥ 15 nos 6 pares (com `--chart-5`) e faixa de luminosidade (exceção escrita só
  para o `--chart-5` do escuro). A `deltaEOk` é conferida contra a saída do validador.
  `aparencia-grafico.test.ts`: mapeamento R1 a R3 → `--chart-1..3`, outros → `--chart-5`, e
  todo token entre as séries conferidas. **Mutações** (cópia no scratchpad, restaurada e
  conferida com `cmp` após cada uma):

  | Mutação | Reprovou | Valor |
  |---|---|---|
  | só `--chart-2` do escuro → `var(--regra-r2)` (1ª tentativa) | nada (sobreviveu) | R2 × R3 = 18,7 |
  | os três do escuro → `var(--regra-r*)` (1a) | R2 × R3; R3 × `--chart-5` | 13,897; 14,41 |
  | só `--chart-2` do escuro, depois do teste de faixa | faixa no escuro | L 0,76 > 0,67 |
  | `--chart-5` do claro → L 0,66 | `--chart-5` sobre `--background` | 2,98 < 3 |

  A 1ª tentativa sobreviveu porque a previsão estava errada: o 13,9 era com R2 e R3 ambos na
  cor de texto. Ela revelou que nenhum teste conferia a faixa de luminosidade, e por isso o
  teste de faixa foi acrescentado. **Limitações (declarar no artigo)**: o cinza das regras do
  usuário tem saturação baixa nos dois temas (inerente a um cinza, neutro de propósito) e,
  no escuro, L 0,71, acima da faixa de barras: nenhum cinza dentro da faixa se separa do R2
  sob daltonismo (CVD entre 1,9 e 5,3 no intervalo testado). Todas as regras do usuário
  dividem essa cor; o código na legenda e no selo as distingue. **Estado do frontend**:
  Vitest **416/416** em 13 arquivos (358 anteriores + 58 novos), typecheck, lint e build ok.
  O aviso de 500 kB do build foi tratado na entrada seguinte (`lazy()` e decisão).
- **Fase 1, etapa 4 — Visão geral (14/11, concluída)**: **dados** (`src/visao-geral/dados.ts`,
  funções puras): série de alertas por dia do período das métricas (13/10 a 11/11 = 30
  pontos), com os 10 dias sem alerta preenchidos com 0 (o backend só manda os dias com
  alerta); dia fora do período estende o eixo em vez de sumir; código só em `por_dia` entra
  no fim. Datas puras sem `new Date`: `diasEntre` parte o texto e avança o calendário
  (bissexto ÷4/÷100/÷400 à mão); data inválida lança erro em vez de virar gráfico vazio sem
  aviso. Textos dos KPIs ("2 ativas · 1 pausada", "3 ativas de 3", "13/10 a 11/11/2026 · 90
  sintéticos", "gerados em 2 avaliações" a partir de `alertas.avaliacoes`); parâmetros NULL
  → "não registrado" (nunca "só ativas"; ausente ≠ falso); `estadoVazio` na ordem do fluxo
  (sem campanhas → sem métricas → sem avaliações; "sem alertas" não é vazio: o gráfico
  mostra os zeros); `codigoNoTopo` (só o segmento do topo da pilha ganha o canto de 4 px).
  Testes: fixture com os números do banco `limen`, tipada com
  `components["schemas"]["ResumoSaida"]` por **anotação** (com `satisfies`, o tipo literal de
  `por_dia` vira uma união que não cabe em `{ [codigo]: number }` e o typecheck reprovou);
  invariantes como oráculo (soma da série = `alertas.total`; soma de cada regra = total dela
  em `por_regra`, que vem de outra consulta do backend); `TZ=America/Fortaleza`.
  **Mutações** (cópia no scratchpad, restaurada e conferida com `cmp` após cada uma):

  | Mutação | Reprovaram | Exemplo |
  |---|---|---|
  | sem preencher os dias vazios | 4 | 20 dias em vez de 30; 0 dias com zero em vez de 10 |
  | `diasEntre` com `new Date` | 13 | `'2026-10-12'` em vez de `'2026-10-13'`; soma 26 ≠ 27 |
  | NULL tratado como `false` | 1 | `'só ativas · …'` em vez de `'não registrado'` |
  | sem a regra CSS de menos movimento | 5 | `expected null not to be null` (bloco ausente) |

  Na 1ª, os invariantes de soma passaram (zeros não mudam soma): quem pegou foi o teste dos
  30 dias, por isso ele existe separado. **Componentes**: `CartoesKpi` (4 cartões com
  `role="group"` + `aria-labelledby`; o de Alertas diz de quantas avaliações vieram),
  `GraficoAlertasPorDia` (barras empilhadas ≤ 24 px, 2 px na cor do cartão entre os
  segmentos, eixo Y só com inteiros; legenda própria com a amostra em `corGrafico` e o
  texto em `corCss`; o SVG fica `aria-hidden` com `accessibilityLayer={false}`, porque o
  padrão do Recharts 3 torna o SVG focável, e foco dentro de área escondida é erro;
  descrição em texto visível no cabeçalho do cartão; botão "Ver dados em tabela" com
  `aria-expanded`/`aria-controls`, a tabela fica no DOM com `hidden` para o `aria-controls`
  apontar para algo que existe), `AlertasPorRegra` (`<dl>`, regra sem alerta aparece com 0,
  marca "desativada"; `self-start` na grade para não esticar até a altura do gráfico),
  `UltimasAvaliacoes` (consulta própria `useAvaliacoes(5)`: se falhar, KPIs e gráfico
  continuam), `EstadoVazio` genérico (sem `role="alert"`: vazio não é erro). **Um status de
  carregando por consulta**: os esqueletos individuais anunciam o próprio status; o
  `EsqueletoResumo` (uma consulta: KPIs, gráfico, alertas por regra) e o
  `EsqueletoVisaoGeral` (fallback do Suspense) desligam os internos (`comStatus={false}`) e
  anunciam uma mensagem só. Alternativa descartada: um status por bloco (o leitor de tela
  anunciaria quatro mensagens seguidas). **Carregamento sob demanda**: o conteúdo
  (`ConteudoVisaoGeral`, com o Recharts) vem por `React.lazy` + `Suspense`; o **h1 fica fora
  do Suspense**, porque o Layout foca o h1 ao trocar de rota, e um h1 dentro do fallback
  seria desmontado quando o conteúdo chegasse, mandando o foco para o `<body>`. Falha ao
  baixar o pedaço sobe até o `errorElement` da raiz (`ErroDeRota`, com "Recarregar").
  Alternativa descartada: `lazy` do React Router (a navegação esperaria o download sem
  fallback visível). **Menos movimento** (WCAG 2.3.3): `src/lib/movimento.ts`
  (`matchMedia("(prefers-reduced-motion: reduce)")` com `useSyncExternalStore`, reage se a
  preferência mudar com a página aberta; teste com `matchMedia` falso que só responde à
  consulta exata) desliga a animação do Recharts, que é por JavaScript. Para as animações de
  CSS (o Sheet do menu do celular ainda deslizava), regra global no `index.css`, fora das
  camadas e com `!important`: `animation-duration` e `transition-duration` em `0.01ms` (não
  0: com 0 o `animationend` pode não disparar, e o Radix espera por ele para desmontar o
  Sheet) e `animation-iteration-count: 1`, em `*`, `*::before`, `*::after`; sem editar
  `src/components/ui`. `movimento-css.test.ts` lê o CSS sem os comentários (o comentário
  cita a consulta) e confere seletores, propriedades, valores e `!important`.
  **Build** (JS):

  | | Principal | Visão geral | Baixado ao abrir |
  |---|---|---|---|
  | antes da etapa 4 | 549,97 kB (174,80 gzip) | — | 549,97 kB |
  | import estático | 941,76 kB (287,75 gzip) | — | 941,76 kB |
  | com `lazy()` | 556,31 kB (176,84 gzip) | 387,23 kB (112,43 gzip) | 556,31 kB |

  **Aviso de 500 kB aceito por enquanto**: a base (React, roteador, Radix, TanStack) já tinha
  549,97 kB antes do Recharts, e separar as bibliotecas num pedaço próprio não diminui o que
  é baixado no início. As outras telas entram com `lazy()` nas Fases 2 e 3; decisão final na
  etapa 5. **Teste no navegador (Kauan, 14/11), 8 itens aprovados**: valores dos KPIs,
  gráfico, dica, tabela, alertas por regra e últimas avaliações iguais ao banco; tema
  escuro; Tab não entra no gráfico; com `prefers-reduced-motion` as barras aparecem sem
  animação e, sem ele, animam; com Slow 3G aparece o esqueleto e `document.activeElement` é
  o h1; bloqueando `ConteudoVisaoGeral.tsx` aparece o `ErroDeRota`, sem tela branca; no
  celular os KPIs ficam em 2 colunas e só a tabela rola para o lado; console sem erros.
  Depois do teste: a regra CSS de menos movimento e o `self-start`. **Melhoria opcional**:
  o `ErroDeRota` fica na rota raiz e ocupa a tela toda, escondendo o menu lateral; um
  `errorElement` dentro do Layout manteria a navegação, mas exigiria uma versão sem o
  próprio `<main id="conteudo">` (senão haveria dois). Totais: pytest **213/213**, Vitest
  **491/491** (16 arquivos), typecheck, lint e build ok. Evidências:
  `docs/evidencias/2026-11-14_fase1_visao-geral_pytest.txt` e `_vitest.txt` (verbose).
- **Fase 1, etapa 5 — limpeza (14/11)**: `src/paginas/Vitrine.tsx` removida (`git rm`);
  antes, uma busca por "vitrine" e `CLASSE_KPI` em todo o frontend (fora `node_modules` e
  `dist`) só achou o próprio arquivo, e o roteador não a importava. O build ficou com os
  mesmos tamanhos (556,31 kB e 387,23 kB), sinal de que ela já não entrava no pacote.
  **Teste do KPI com 14 px**: o teste antigo de `utils.test.ts` conferia o `cn` com classes
  escritas à mão, mas nada garantia que o `CartoesKpi` usasse a variante; tirá-la do
  componente passaria em todos os testes. A constante foi para `src/visao-geral/classes.ts`
  (`export const CLASSE_NUMERO`), importada pelo `CartoesKpi.tsx`; teste novo:
  `cn(<classes do CardTitle>, CLASSE_NUMERO)` contém `group-data-[size=sm]/card:text-3xl`
  e não contém `…:text-sm`. As classes do `CardTitle` ficam escritas à mão no teste
  (decisão do Kauan; ler `card.tsx` acompanharia o shadcn, mas complicaria o teste).
  Alternativa descartada: exportar a constante de dentro do `CartoesKpi.tsx` (a regra
  `react-refresh/only-export-components` reclamaria e teria de ser desligada no arquivo).
  **Mutação** (cópia no scratchpad, restaurada e conferida com `cmp`): sem a variante no
  `CLASSE_NUMERO`, só o teste novo reprovou (1 de 5 no arquivo), com "expected
  'font-heading group-data-[size=sm]/car…' to contain 'group-data-[size=sm]/card:text-3xl'".
  **Aviso de 500 kB**: mantido como aceito na etapa 4, sem mudar o build. Totais: Vitest
  **492/492** (16 arquivos), typecheck, lint e build ok; pytest não rodado (backend
  intocado, 213/213 desde 14/11). Evidência: `docs/evidencias/2026-11-14_fase1_etapa5_vitest.txt`.
  **Execução real (Kauan, 14/11)**: na Visão geral, os números dos KPIs com `font-size`
  30px no DevTools (classe com `group-data-[size=sm]/card:text-3xl`, sem `text-sm`); o
  cartão "Alertas por regra" com a altura do conteúdo (`self-start` da etapa 4). Etapa ✅.
- **Fase 2 — plano e decisões (14/11)**: telas Campanhas (lista, sincronizar) e Campanha
  (métricas diárias). Sem `GET /campanhas/{id}` no backend: o detalhe usa a lista de
  `GET /campanhas` já em cache (nenhum endpoint novo). **CTR zero chega como `"0E-16"`**:
  a view divide `NUMERIC` sem arredondar e o Pydantic serializa `Decimal` com expoente
  (conferido no venv: `0.0000000000000000` → `"0E-16"`); o frontend normaliza e arredonda
  o texto (`lib/decimal.ts`, sem float, empate longe do zero como o `round()` do
  PostgreSQL). Alternativa descartada: arredondar na view ou no Pydantic (mudaria o
  contrato e o valor que o motor usa). Cota excedida: a mensagem usa o `Retry-After` real
  via `formatarEspera` (já era assim em `erros.ts`; testes com outros valores além de
  3600). **Decisões do Kauan**: (1) erros do Google (cota, indisponível, token revogado)
  testados no Playwright da Fase 4 com respostas simuladas; sem rota `/dev/` nova e sem
  revogar o acesso real agora; (2) selos de alerta (R1/R2/R3) na tabela diária ficam para
  a Fase 4; (3) totais do período (CTR = Σcliques × 100 / Σimpressões, não média dos CTRs
  diários) entram no plano de corte.
- **Fase 2 — `lib/decimal.ts` (14/11)**: `normalizarDecimal` (sem expoente nem zeros à
  direita), `arredondarDecimal(texto, casas)` (empate longe do zero), `formatarPercentual`,
  `formatarMoeda` (`R$` + espaço inseparável) e `formatarDecimalCurto`. O texto vira
  dígitos inteiros + escala e as contas são em `BigInt`; nenhum float. Expoente acima de
  1000 → `null` (evita montar texto gigante); casas inválidas → `RangeError`. **Oráculo**:
  as respostas do PostgreSQL 16 (`round()` e `trim_scale()` no `limen_teste`), copiadas no
  teste como vieram, com a consulta no comentário; inclui `0E-16` e um número de 20
  dígitos que um float estraga (`12345678901234567890.125` → float dá
  `12345678901234600000`). 79 testes. **Mutações** (script no scratchpad: cópia antes,
  `trap` que restaura em qualquer saída, `cmp` após cada uma):

  | Mutação | Reprovaram (de 79) | Exemplo |
  |---|---|---|
  | M1 truncar (nunca soma 1) | 16 | `round(2.345, 2) = 2.35` |
  | M2 empate para o par (como o Decimal do Python) | 12 | `round(2.5, 0) = 3` |
  | M3 ignorar o expoente | 6 | `trim_scale(1.25E-1) = 0.125` |
  | M4 empate negativo em direção ao zero (como `Math.round`) | 2 | `round(-2.5, 0) = -3` |
  | M5 passar os dígitos por float | 4 | `round(12345678901234567890.125, 2)` |
  | M6 zero com sinal | 3 | `round(-0.004, 2) = 0.00` |

  M4 só é pega pelos dois empates negativos do oráculo (`-2.345` e `-2.5`): sem eles,
  sobreviveria. **Caractere invisível**: a ferramenta de escrita gravou o espaço
  inseparável literal onde o código mostrado tinha o escape barra-invertida u00A0 (1 vez
  no `decimal.ts`, 4 no `decimal.test.ts`, 1 no `dados.test.ts`); o lint pegou o do
  `decimal.ts` (`no-irregular-whitespace`, dentro de template literal). Trocados pelo
  escape com `sed` e conferidos com `grep -c` (0 ocorrências); lint ok. Como o arquivo
  mudou, as 6 mutações foram refeitas: números idênticos. Prova da restauração: sha256
  do `decimal.ts` igual antes e depois (`16d36fb2…6aa06e5c`, 2ª rodada; o
  `72b7deb5…061cceed` da 1ª era do arquivo com o caractere literal); o `git diff` sai
  vazio de qualquer jeito, porque o arquivo ainda não está no git.
- **Fase 2 — `campanhas/dados.ts` (14/11)**: funções puras das telas. `lerIdCampanha`
  (só inteiro positivo sem zero à esquerda; inválido → `null` e a tela não chama a API),
  `encontrarCampanha` (o detalhe usa a lista), `formatarOrcamento` (micros viram o texto
  `"50000000E-6"` e passam pelo `decimal.ts`; `null` → "sem orçamento", diferente de
  `R$ 0,00`), `textoSincronizacao`, `mensagemSincronizacao`, `rotuloOrigem`
  (`Object.hasOwn`), `descricaoPeriodo` (ordena as datas ISO como texto) e as células
  da tabela diária: ausente → "—" ("sem dado"); CTR/CPC nulo → "N/A" com o motivo, na
  mesma ordem de verificação de `calcular_ctr`/`calcular_cpc` do motor (ausência antes do
  zero). O CTR zero (`0E-16`) é 0,00%, não N/A; com 0 cliques a mesma linha tem CTR
  0,00% e CPC N/A. Oráculo: 4 linhas reais da campanha A no banco `limen`, com o
  esperado tirado de `round(ctr, 2)`/`round(cpc, 2)` no PostgreSQL; orçamentos reais de
  A, B e C. Os dados do IN-02b não têm CTR nem CPC nulos (0 de 90): o N/A só é coberto
  por teste, não aparece no navegador. 58 testes. **Mutações** (mesmo script: cópia,
  `trap`, `cmp`, sha256 `1f2c4fd0…6d64a9a8` antes e depois):

  | Mutação | Reprovaram (de 58) | Quais |
  |---|---|---|
  | D1 ausente vira zero (`valor ?? 0`) | 1 | ausente vira — |
  | D2 orçamento por float (`toFixed`) | 1 | 1.005.000 micros → R$ 1,01 (float dá 1,00) |
  | D3 id frouxo (`/^\d+$/`) | 2 | `"0"` e `"007"` |
  | D4 zero antes da ausência no CTR | 1 | impressões 0 e cliques ausentes → "cliques ausentes" |
  | D5 período sem ordenar | 2 | lista invertida e virada de ano fora de ordem |
  | D6 origem sem `Object.hasOwn` | 2 | `toString` e `__proto__` |
- **Fase 2 — consultas de campanhas (14/11)**: `useCampanhas`, `useMetricas` e
  `useSincronizar` em `api/consultas.ts`; chaves novas `campanhas`, `metricas(id)` e o
  prefixo `todasAsMetricas`. As opções ficam em funções (`opcoesMetricas`,
  `opcoesSincronizar`) que recebem a chamada à API como parâmetro, para o teste usar um
  `QueryClient` de verdade sem React e sem rede. `useMetricas` só roda com id válido
  (`enabled: campanhaId !== null`; a `queryFn` ainda lança se receber null, em vez de
  pedir `/campanhas/null`). `useSincronizar`: `retry: false` explícito (o backend já
  repete o transitório, IN-05, e não repete a cota, IN-06); no sucesso invalida
  campanhas, métricas (de todas as campanhas) e resumo, e o `onSuccess` devolve a
  promessa para o botão seguir em "Sincronizando…" até os dados novos chegarem; em
  `token_google_ausente`/`token_google_revogado` invalida `/eu` (o 401 continua com o
  `MutationCache` global). Alternativa descartada: testar só funções auxiliares soltas
  (provaria as listas, não que a mutação as usa). Testes: 17 em `consultas.test.ts`
  (cliente de teste com `retry: 3` e `retryDelay: 0` nas consultas e mutações, para o
  `retry: false` ter de vir da mutação) e 3 novos em `erros.test.ts` (cota com
  `Retry-After` de 120 e 5400 s e o caminho cabeçalho → `lerErro` → `mensagemDoErro`;
  16 linhas acrescentadas, 0 removidas). **Mutações** (cópia dos dois arquivos, `trap`,
  `cmp`; sha256 iguais antes e depois: `consultas.ts` `7313a11f…06616895`, `erros.ts`
  `70499756…4ce26367`):

  | Mutação | Reprovaram | Testes reprovados |
  |---|---|---|
  | C1 sem `retry: false` | 3 de 17 | os 3 "sem repetição automática" |
  | C2 sucesso não invalida métricas | 2 de 17 | chaves exatas; sucesso invalida… |
  | C3 qualquer erro invalida `/eu` | 6 de 17 | os 6 "não invalida nada" |
  | C4 só o revogado invalida `/eu` | 1 de 17 | `token_google_ausente` |
  | C5 métricas sempre ligadas | 1 de 17 | id inválido: `expected 'fetching' to be 'idle'` |
  | E1 cota com espera fixa (3600) | 4 de 103 | os 3 novos + "sem Retry-After diz 'mais tarde'" |

  Duas previsões erradas, conferidas com a lista dos reprovados: E1 reprovou também um
  teste antigo (com 3600 fixo o texto nunca diz "mais tarde"); C5, que eu esperava que
  sobrevivesse, foi pego pelo `fetchStatus`. **C5 dependia do tempo**: com a consulta
  ligada, a `queryFn` lança e o TanStack repete; no instante da checagem a consulta ainda
  está em "fetching", mas se as repetições acabassem antes, ela voltaria a "idle" e a
  mutação sobreviveria. Reforço no teste: também `status === "pending"` e
  `failureCount === 0` (a consulta nunca rodou). **Rodada extra**: C5 aplicada e, numa
  cópia de trabalho do teste, sem o `expect` do `fetchStatus` (sha256 dos dois arquivos
  iguais antes e depois; `consultas.test.ts` `56a1e5c9…86ef4477`). Reprovou o mesmo
  teste, com `expected 1 to be +0`: quem pegou foi o `failureCount`. O `status` passou,
  porque durante as repetições a consulta continua "pending"; sozinho, ele não pegaria o
  C5. O `failureCount` pega sem depender do tempo, porque a 1ª tentativa já falhou antes
  da checagem.
- **Fase 2, etapas 1 a 3 — telas Campanhas e Campanha (15/11)**: **`Carregando` em
  `src/componentes/`**: saiu de dentro de `visao-geral/Esqueletos.tsx` (onde era privado)
  sem mudar o código, porque as telas de campanhas usam o mesmo padrão "um status por
  consulta" da etapa 4 (`comStatus={false}` dentro de uma região que já anuncia).
  Alternativa descartada: copiar o componente para `campanhas/` (duas cópias da mesma
  regra de acessibilidade). **`TabelaRolavel`** (`src/componentes/`): o `<Table>` do shadcn
  rola para o lado, mas o contêiner não recebe foco, e quem usa teclado não consegue rolar
  (WCAG 2.1.1). A região tem `tabIndex={0}`, `role="region"` e nome dado pela `<caption>`
  (`aria-labelledby`), e fica sempre na ordem do Tab, mesmo sem rolagem (detectar a
  rolagem mudaria o comportamento conforme a largura). Anel com `--ring` opaco (par já
  testado, ≥ 3:1). Os filhos são `TableHeader`/`TableBody` do shadcn, sem editar
  `components/ui`. **`SeloStatus`**: reaproveita `rotuloStatus` de `lib/formatar.ts` (a
  mesma da Visão geral; texto em minúsculas com `capitalize` só na exibição), com caso
  novo em `formatar.test.ts` (`REMOVED × 1 → removida`). Só as variantes do `Badge` com
  contraste testado (`default` para ENABLED, `outline` para o resto); cada status tem ícone
  e texto próprios (a cor não é o único sinal); status desconhecido → ícone de interrogação,
  com `Object.hasOwn`. **`Sincronizacao`**: `aria-disabled` em vez de `disabled` durante o
  pedido, porque um botão focado que vira `disabled` perde o foco (vai para o `<body>`); o
  clique repetido é ignorado no código, e o teste no navegador confirmou um único POST. O
  `role="status"` existe sempre (vazio fora do pedido): região viva criada junto com o texto
  nem sempre é anunciada. Erro aparece junto do botão (`EstadoErro`, com a ação que o `tipo`
  pede), sem esconder a lista. Sucesso: aviso do sonner ("3 campanhas sincronizadas.").
  **`textoAcessivel`** (`campanhas/dados.ts`, pura): "—" e "N/A" sozinhos não dizem nada ao
  leitor de tela; o símbolo fica visível com `aria-hidden` (e `title`), e o leitor ouve
  "sem dado" ou "N/A, indefinido: 0 cliques". 3 testes novos; sem mutação (texto de
  exibição, fora da lógica crítica). **Página Campanha sem pedido com id inválido**:
  `lerIdCampanha` → `null` mostra "Campanha não encontrada" sem montar o conteúdo, então
  `GET /campanhas/{id}/metricas` nem é chamado (conferido no navegador com
  `/campanhas/abc`: nenhum pedido de métricas). Id válido fora da lista do usuário → a
  mesma mensagem ("pode não existir ou ser de outra conta"). O h1 fica fora do Suspense e é
  sempre o mesmo elemento: começa "Campanha" e passa ao nome quando a lista chega (o foco
  do Layout não se perde). Conteúdo das duas telas por `lazy()`, como a Visão geral; no
  detalhe, resumo e métricas são consultas separadas (se a lista falhar, a tabela segue).
  **Texto corrigido antes do commit**: na descrição da tabela diária faltava o ponto entre
  o período e "CTR e CPC calculados…"; o ponto foi posto no componente (`${periodo}.`), e
  não em `descricaoPeriodo`, porque a mesma função monta a legenda da tabela.
  **Build** (JS baixado ao abrir):

  | | Pedaços iniciais | Baixado ao abrir |
  |---|---|---|
  | etapa 5 da Fase 1 | principal 556,31 kB | 556,31 kB |
  | Fase 2 | `index` 365,48 kB + `card` 198,53 kB | 564,01 kB |

  **Mudança de divisão, não melhoria**: o aviso de 500 kB sumiu só porque o Vite separou
  um pedaço comum (`card`, usado pela Visão geral e pelas telas de campanhas) e nenhum
  pedaço passa de 500 kB; o que o navegador baixa ao abrir cresceu 7,70 kB. Pedaços das
  telas novas: `ConteudoCampanhas` 3,51 kB, `ConteudoCampanha` 3,56 kB, `SeloStatus`
  1,68 kB; `ConteudoVisaoGeral` 383,79 kB. **Teste no navegador (Kauan, 15/11), aprovado**:
  lista com 3 campanhas, selos e orçamentos certos; sincronizar com um único POST, aviso
  "3 campanhas sincronizadas." e lista atualizada; erro de servidor junto do botão com a
  lista visível; campanha A com 30 linhas e CTR/CPC conferidos à mão em 13/10, 17/10 e
  28/10; `/campanhas/abc` com "Campanha não encontrada" e nenhum pedido de métricas; foco
  visível na tabela; no celular só a tabela rola; console sem erros. Totais: Vitest
  **653/653** (19 arquivos), typecheck, lint e build ok; pytest não rodado (backend
  intocado, 213/213). Evidência: `docs/evidencias/2026-11-15_fase2_telas_vitest.txt`.
- **Fase 3, etapa 1 — R1 a R3 bloqueadas no backend (15/11)**: decisão do Kauan, em duas
  camadas. (a) A execução formal (planilha completa e desempenho) usa banco e usuário
  próprios, criados por script; antes de medir, um script compara `GET /regras` com a aba
  "Regras e limiares" (3 regras ativas, limiares iguais, nenhuma outra ativa; se houver
  diferença, para sem medir). É a garantia de verdade: nada que se faça na tela chega
  nela. (b) A API recusa criar, editar (qualquer PUT, mesmo idêntico ou só ativando) e
  desativar (DELETE) regra com código R1, R2 ou R3, e renomear outra regra para esses
  códigos: 409 `regra_referencia`. Comparação sem distinguir maiúsculas ("r1" seria
  confundida com a R1 na tela). `CODIGOS_REFERENCIA` vem de `regras_padrao()` no motor
  (R1 a R3 não ficam repetidos à mão); um teste confere que são os códigos lidos da
  planilha. `obter_regra` vem antes da checagem: a R1 de outro usuário continua 404 (não
  revela que existe). R1 a R3 só nascem em `criar_regras_padrao`. `RegraSaida` ganha o
  campo calculado `referencia: bool`, para a tela travar sem repetir a lista;
  `esquema.d.ts` regenerado (diff de 5 linhas). Mensagem nova em `erros.ts`: o oráculo de
  `erros.test.ts` reconheceu o tipo sozinho (103 → 105). Os endpoints fixos não mudaram
  de nome. Banco `limen` conferido antes, só leitura: R1 a R3 ativas e iguais à tabela,
  então nada ficou travado num estado errado. Descartados: bloquear só no frontend (um
  `curl` contornaria) e coluna `referencia` com migração 0004 (o código já é único e,
  com o bloqueio, não pode mais ser trocado). **Testes antigos alterados (2)**:
  `test_regra_desativada_nao_gera_alerta` (desativava a R1) e
  `test_regra_desativada_conta_como_inativa` (desativava a R2) passaram a usar regras do
  usuário com o mesmo papel (R9 `ctr < 1` e R4). **Teste instável achado na 1ª rodada de
  mutação**: `test_editar_referencia_e_recusado[R1]` reprovava na suíte inteira e passava
  sozinho (230/231 com o código restaurado). Causa provável (não isolada): a sessão de
  teste usa `expire_on_commit=False`, e depois do commit o SQLAlchemy guarda os objetos
  só por referência fraca; o GET devolvia o objeto em memória (limiar `"1.00"`) ou o
  relido do banco (`"1.000000"`), conforme o coletor de lixo. Correção: `expire_all()` na
  fixture. O que está provado é o resultado: com ele, 236/236 três vezes seguidas.
  **A produção também usa `expire_on_commit=False`** (`app/db.py`). Confirmado num teste
  temporário no `limen_teste` (scratchpad, transação desfeita, apagado depois): o POST
  respondia `'7.5'` e o GET seguinte `'7.500000'`; o PUT `'8'` e o GET `'8.000000'`.
  Correção localizada: `_reler_do_banco` (`expire_all()` + `obter_regra`) em
  `criar_regra` e `atualizar_regra`. O `expire_on_commit` do `sessionmaker` não mudou
  (afetaria sincronização, semeador e avaliação). Teste novo `test_regras_formato.py`
  com uma sessão nova por pedido, como em produção (com a sessão única dos outros testes
  a diferença não apareceria); a fixture guarda e devolve as substituições do conftest.
  **Mutações** (`servicos/regras.py`; script único com backup, trap, `cmp` após cada uma,
  sha256 `cf72500f…8aef8a2e` igual antes e depois):

  | Mutação | Reprovaram (de 236) | Quais |
  |---|---|---|
  | B1 PUT sem checar o código atual | 3 | renomear R1, R2 e R3 para R7 |
  | B2 PUT sem checar o código novo | 2 | renomear R9 para R2 e para r2 |
  | B3 DELETE liberado | 3 | desativar R1, R2 e R3 |
  | B4 POST liberado | 3 | criar R1, r1 e R3 |
  | B5 comparação sensível a maiúsculas | 2 | renomear para r2; criar r1 |
  | B6 sem `_reler_do_banco` | 2 | POST e PUT iguais ao GET seguinte |
  | B7 `sessao.refresh(regra)` no lugar do `expire_all()` | 0 (sobreviveu) | — |

  Na 1ª rodada a B1 sobreviveu: os testes de PUT mandavam o próprio código no corpo, e a
  checagem do código novo recusava do mesmo jeito. Faltava o caso "renomear R1 para R7",
  que foi acrescentado. **B7, previsão refutada pela mutação**: a previsão era que
  `sessao.refresh(regra)` não bastaria, porque o limiar está nas condições; a mutação
  mostrou que basta. Mecanismo provável: o `refresh` sobrescreve os objetos já
  carregados (`populate_existing`) e isso alcança as condições; não foi confirmado no
  código do SQLAlchemy. Não é falha de teste: é uma correção alternativa equivalente.
  Mantido o `expire_all()` (decisão do Kauan): é simples de explicar e a sessão é de um
  pedido só; a docstring registra que o `refresh` também funcionaria. pytest
  **236/236** (213 + 18 do bloqueio + 3 de renomear + 2 de formato), três vezes seguidas.
- **Fase 3, etapa 2 — validação das regras e pedido de avaliação (15/11)**: funções puras,
  sem tela: `src/regras/validacao.ts` (esquema zod do formulário, `lerLimiar`,
  `erroCodigo`, `erroNome`, `validarRegra`) e `src/avaliacoes/pedido.ts`
  (`montarPedidoAvaliacao`), mais `ehDataIso` em `visao-geral/dados.ts` (sobre o `lerData`
  existente; `dados.test.ts` intacto, 62/62). **Regra testada: a tela nunca envia o que
  o backend recusa.** Onde ela é mais rígida, a diferença é de propósito, listada no
  teste e conferida contra o oráculo (o Pydantic aceita e a tela recusa): limiar com sinal
  ou separador sem algarismo dos dois lados (`-0`, `+1`, `.5`, `5.`) e com expoente
  (`1e3`); nome só com espaços; data com hora (`2026-11-11T00:00:00`; a tela aceita só
  `AAAA-MM-DD`); `campanha_id` fora da lista de campanhas (o Pydantic aceita 0 e -1).
  Códigos R1 a R3 (sem distinguir maiúsculas) são recusados na tela como no serviço (409);
  o Pydantic aceita, e por isso o oráculo deles é a lista `CODIGOS_REFERENCIA`. Espaços
  nas pontas do nome e do limiar são removidos antes de enviar. O limiar é texto do começo
  ao fim: sem `Number`/`parseFloat`, normalizado por `lib/decimal.ts`, com casas e
  algarismos contados como o Pydantic conta (`1.0000000` tem 0 casas, `0.5` tem 0
  algarismos inteiros). **Vírgula**: o limiar aceita um único separador, vírgula ou ponto
  (`^\d+(?:[.,]\d+)?$`), e a vírgula vira ponto (`1,5` → `1.5`, que o oráculo aceita com o
  mesmo valor); separador de milhar não existe, e `1.234,5`, `1,234.5` e `1,2,3` são
  recusados com `MENSAGENS.limiarFormato`. Consequência: `1.000` digitado como mil vira 1
  (pendência da etapa 4: mostrar o valor que será salvo). **Oráculo** colhido por script
  no scratchpad, no venv do backend, só com os esquemas (`app.api.esquemas` e
  `app.motor`; um `assert` confere que `app.config`, `app.db` e `app.main` não foram
  importados): sem banco, sem `.env`, sem rede. `model_validate` em 30 limiares, 9
  métricas, 9 operadores, 12 códigos, 9 nomes, 4 quantidades de condições, 13 datas e 16
  pedidos de avaliação, e `model_json_schema()` para os limites e enums (o esquema não traz
  os limites de 12 algarismos inteiros e 6 casas do limiar; eles vêm dos casos). As
  tabelas dos testes foram **geradas da saída JSON por outro script** e inseridas no lugar
  de um marcador, sem cópia à mão; antes da mutação, o trecho inserido em cada teste foi
  comparado com o bloco gerado por `diff` (sem diferença; primeira linha com 1 ocorrência;
  trecho entre linhas em branco). **Achados no caminho**: (1) tamanho do nome: o Pydantic
  aceita 120 emojis e recusa 121, mas o `.length` do JavaScript conta um emoji como 2 e a
  tela recusaria um nome válido; contado com `Array.from(texto).length`, igual ao `len()`
  do Python. (2) Ano 0000: o `lerData` aceitava `0000-01-01`, que o oráculo (rodado de
  novo com esse caso) recusa (`date_parsing`); o `ehDataIso` exige ano ≥ 1. (3) A mutação
  planejada "comparar datas com `new Date`" seria equivalente (datas `AAAA-MM-DD` válidas
  viram meia-noite UTC e comparam igual ao texto), então nenhum teste a pegaria; trocada
  por "`>` vira `>=`". Descartado: ligar os erros do servidor aos campos nesta etapa
  (integração com a API; fica para a etapa 3). **Mutações** (script único para os dois
  arquivos, com backup, trap, `cmp` após cada uma; sha256 iguais antes e depois:
  `validacao.ts` `39552a47…ca58d1d8`, `pedido.ts` `52badb44…9e095bc985f`):

  | | Mutação | Previsto | Reprovou (de 130) |
  |---|---|---|---|
  | V1 | sem limite de casas | 4 | 4 |
  | V2 | casas contadas no texto digitado, sem normalizar | 1 | 1 (`1.0000000`) |
  | V3 | vírgula não convertida | 4 | 4 |
  | V4 | máximo de condições 11 | 2 | 2 |
  | V5 | padrão do código aceita espaço | 3 | 3 |
  | V6 | referência sensível a maiúsculas | 3 | 3 (`r1`, `r2`, `r3`) |
  | V7 | tamanho com `.length` | 1 | 1 (120 emojis) |
  | P1 | campo vazio enviado como `""` | 5 | 5 |
  | P2 | período invertido não bloqueia | 2 | 2 |
  | P3 | `>` vira `>=` | 1 | 1 (início = fim) |
  | P4 | `incluir_pausadas` omitido quando falso | 8 | 8 |
  | P5 | campanha fora da lista enviada | 1 | 1 (`"99"`) |

  Todas as previsões se confirmaram, com os mesmos testes. Testes novos: 91 em
  `validacao.test.ts` e 39 em `pedido.test.ts`. Vitest **785/785** (21 arquivos;
  653 + 2 de `erros.test.ts` da etapa 1 + 130), typecheck e lint ok.
- **Fase 3, etapa 3 — consultas de regras e avaliações e erros nos campos (15/11)**: sem
  tela (as telas usam isto na etapa 4). **Consultas** (`api/consultas.ts`): chaves novas
  `regras`, `regra(id)` (fica sob o prefixo `regras`: invalidar a lista atinge as duas),
  `todasAsAvaliacoes` (prefixo de `avaliacoes(limite)`: a tela de avaliações usa 50, a
  Visão geral 5) e `alertas` (a tela é da Fase 4; invalidar desde já não custa nada).
  `useRegras`; `opcoesRegra(id)` desligada com id `null` (a `queryFn` ainda lança, em vez
  de pedir `/regras/null`). Mutações, todas com `retry: false` explícito e o `onSuccess`
  devolvendo a promessa (o botão fica ocupado até os dados novos chegarem):
  `opcoesSalvarRegra` (id `null` → `POST /regras`, endpoint fixo; número → `PUT
  /regras/{id}`; repetir um POST sem resposta poderia criar a regra e depois receber 409),
  `opcoesAtivarRegra` (não há PATCH: PUT com a regra inteira montada por
  `corpoParaAtivar`, em `regras/validacao.ts`, que passa a regra da API pela mesma
  `validarRegra` do formulário com `ativa = true`; o limiar sai normalizado, `"7.500000"` →
  `"7.5"`; R1 a R3 não passam na validação e nenhum pedido sai), `opcoesDesativarRegra`
  (`DELETE /regras/{id}`; a regra não é apagada) e `opcoesExecutarAvaliacao` (`POST
  /avaliacoes`, endpoint fixo; repetir criaria outra linha no histórico, mesmo sem alerta
  repetido, IN-11). Sucesso de regra invalida `CHAVES_APOS_REGRA` (lista, a regra e o
  resumo, que mostra nome e situação em "Alertas por regra"); sucesso de avaliação invalida
  `CHAVES_APOS_AVALIAR` (histórico de todos os limites, resumo e alertas; não toca em
  regras, campanhas e `/eu`). Erro não invalida nada; o 401 continua no `MutationCache`
  global. Testes (`consultas-regras.test.ts`, 19): `QueryClient` de verdade e cliente
  `openapi-fetch` de verdade com um `fetch` falso que grava método, caminho e corpo, para
  conferir o pedido que sairia de fato; cliente de teste que repete tudo (`retry: 3`,
  `retryDelay: 0`), para o `retry: false` ter de vir das opções; invalidação conferida
  pelo `isInvalidated` de 9 chaves em cache. **Erros nos campos** (`api/campos.ts`,
  pendência (b) da etapa 2): `errosNosCamposRegra` e `errosNosCamposAvaliacao` devolvem
  `{ campos, restante }`. 400 `validacao` → campo pelo `local` do Pydantic
  (`camposInvalidos`, de `erros.ts`, já fazia `["body","condicoes",1,"limiar"]` →
  `condicoes.1.limiar`, o mesmo caminho do `validarRegra`); no formulário de avaliação o
  nome é traduzido (`campanha_id` → `campanhaId`). A mensagem do Pydantic vem em inglês e
  não é usada: o campo recebe "O servidor recusou este valor.". 409 `conflito` (UNIQUE do
  código) e `regra_referencia` → campo `codigo`, cada um com a sua frase; escolhidos pelo
  `tipo`, nunca pelo texto. Local que não é campo do formulário (`["body"]` do período
  invertido, `incluir_pausadas`, que é caixa de marcar) e qualquer outro erro ficam em
  `restante`: a tela mostra o `EstadoErro`, com a ação que o `tipo` pede. Os locais
  conhecidos continuam indo para os campos quando há um desconhecido junto. **Oráculo**
  (`campos.test.ts`, 26 testes): o corpo real de 18 respostas 400/409 de `POST`/`PUT
  /regras` e `POST /avaliacoes`, colhido por um script temporário com a aplicação de
  verdade e uma sessão falsa que falha se usada (sem banco); a mensagem em inglês não foi
  guardada. A tabela foi gerada da saída JSON e entrou no lugar de um marcador, sem cópia à
  mão; conferida com `diff` contra o bloco gerado (idêntico, primeira linha com 1
  ocorrência, trecho entre linhas em branco). **Mutações** (script único para os 3
  arquivos, com backup, trap, `cmp` após cada uma; sha256 iguais antes e depois:
  `consultas.ts` `a24b6bd5…3ded832d`, `validacao.ts` `e0650c2c…0a1a4796`, `campos.ts`
  `49308005…ff13a38d`):

  | | Mutação | Previsto | Reprovou (de 830) |
  |---|---|---|---|
  | C1 | salvar sempre com POST | 2 | 2 (com id: PUT /regras/7; ativar) |
  | C2 | `corpoParaAtivar` com `ativa: regra.ativa` | 1 | 1 (ativar) |
  | C3 | avaliação sem `retry: false` | 2 | 2 (um pedido só: sem resposta e 400) |
  | C4 | `CHAVES_APOS_REGRA` sem o resumo | 4 | 4 (o que cada mutação invalida; salvar, ativar e desativar) |
  | C5 | avaliação invalida só `avaliacoes(50)` | 2 | 2 (o que cada mutação invalida; histórico de todos os limites) |
  | E1 | `conflito` fora do `porTipo` | 1 | 1 (409 conflito vai para o código) |
  | E2 | local desconhecido vira campo | 3 | 3 (período invertido e `incluir_pausadas` do oráculo; local que não é campo) |
  | E3 | padrão sem o índice da condição | 4 | 4 (as 4 linhas de condição do oráculo) |

  Todas as previsões se confirmaram, com os mesmos testes. **C2**: a mutação "apagar
  `ativa: true`" seria pega pelo zod (`ativa` é obrigatório; nenhum pedido sairia), e não
  pelo teste; `ativa: regra.ativa` manda um PUT válido que não ativa, e quem pega é a
  comparação do corpo. Vitest **830/830** (23 arquivos; 785 + 26 + 19), typecheck e lint
  ok; pytest não rodado (backend intocado desde a etapa 1, 236/236).
- **Fase 3, etapa 4 — tela de Regras (15/11)**: rotas `/regras`, `/regras/nova` e
  `/regras/:id/editar` (`rotas.ts`; teste: `/regras/nova` não casa com a de edição, e
  "nova" não é id). As três páginas carregam o conteúdo por `lazy()` com o h1 fora do
  Suspense; nova regra e edição dividem o pedaço `FormularioRegra`. **shadcn**: `input`,
  `label`, `select`, `checkbox` e `alert-dialog` pelo CLI 4.23.0, um por vez, com
  `--dry-run`/`--view` antes (imports só de `react`, `radix-ui`, `lucide-react`, `cn` e
  o `button`), entrada fechada (`</dev/null`, sem `--yes`/`--overwrite`) e sha256 de
  `package.json`, `package-lock.json` e `button.tsx` conferidos depois de cada um:
  inalterados (o alert-dialog pulou o `button.tsx`, idêntico). Nenhum pacote novo; o
  `@hookform/resolvers` 7.0.6 já instalado aceita zod 4.
  **`regras/textos.ts`** (funções puras): rótulos de métrica e operador (`Object.hasOwn`),
  `formatarLimiar` sem arredondar (`formatarMoeda` cortaria 0,125 em 0,13),
  `textoCondicao(es)` com o símbolo na tela e o operador por extenso para o leitor de
  tela, condições ordenadas por `ordem`, `valoresIniciais` (limiar da API `"7.500000"` →
  `"7.5"` só com texto, via `normalizarDecimal`; ilegível vai como veio e a validação
  aponta o campo) e `previaLimiar` (sem separador de milhar, senão "1000" voltaria a
  parecer "1.000"). Fixture com os limiares reais do banco `limen` (NUMERIC com 6 casas,
  consulta só de leitura). Oráculo da volta completa: `valoresIniciais` + `validarRegra`
  devolve o corpo da regra original, escrito por extenso no teste, e o mesmo do
  `corpoParaAtivar`. 40 testes. **Escape do espaço inseparável**: gravado com o marcador
  `@@ESC_NBSP@@` trocado por `sed`, conferido com `grep -c` (0 caracteres literais) e
  `od -c` (6 caracteres do escape). Mutações (`trap`, `cmp`; sha256 do `textos.ts`
  `9e37b795…77c05bc5a` igual antes e depois), todas como previsto:

  | | Mutação | Reprovou (de 40) |
  |---|---|---|
  | T1 | limiar sem normalizar | 2 |
  | T2 | sem ordenar as condições | 2 |
  | T3 | `String(Number(limiar))` | 3 |
  | T4 | prévia com separador de milhar | 2 |
  | T5 | prévia sem trocar o ponto pela vírgula | 3 |

  A volta completa não pega a T1 (o `validarRegra` normaliza de novo): quem pega é o teste
  direto do limiar. **Lista** (`ConteudoRegras`): R1 a R3 sem ações (cadeado e texto). Um
  só botão por linha alterna Desativar/Ativar (o mesmo elemento antes e depois, então o
  foco fica nele). Desativar pede confirmação num alert-dialog controlado, um para a
  tabela, com o foco devolvido ao botão da linha no `onCloseAutoFocus`. Descartado: um
  `AlertDialogTrigger` por linha (o gatilho seria trocado depois do sucesso e o foco iria
  para o `<body>`). `aria-disabled` durante o pedido; um pedido por vez; `role="status"`
  sempre presente; sucesso no sonner; erro acima da tabela, com `reset()` da outra
  mutação. Nome acessível "Editar R4"/"Desativar R4" (código em `sr-only`). Erro de tipo
  achado no typecheck: o `error` da mutação é `unknown` e não pode ir para o JSX; a
  condição passou a ser o `isError`. **Formulário** (`FormularioRegra`): `zodResolver`
  com o mesmo `esquemaRegra` do `validarRegra` (descartado: resolver próprio, que teria de
  remontar os erros aninhados); erros do servidor por `errosNosCamposRegra`, com foco no
  primeiro campo recusado; "Será salvo como" abaixo de cada limiar, no `aria-describedby`
  (lido ao focar, sem região viva, para não falar a cada tecla); rótulo em todo campo,
  condição num `fieldset` com legenda "Condição N". A dica do Código foi conferida contra
  o Pydantic e o `PADRAO_CODIGO` (`^[A-Za-z0-9_-]+$`, 1 a 20) e ganhou "(também em
  minúsculas)". Lint achou `setState` dentro de efeito (foco depois de remover): trocado
  por `useRef`. **Edição**: id inválido → "Regra não encontrada" sem pedido; 404 decidido
  pelo `tipo`; R1 a R3 só leitura. As duas decisões com lógica nos componentes saíram para
  `regras/edicao.ts` (`regraNaoEncontrada`, `focoDaNovaCondicao`; 14 testes), porque
  dentro do `.tsx` nenhum teste do Vitest reprovaria uma mutação. Mutações (43 testes:
  `rotas.test.ts` 29 + `edicao.test.ts` 14; `trap`, `cmp` dos dois arquivos após cada uma;
  sha256 iguais antes e depois: `rotas.ts` `238f402e…28df80770`, `edicao.ts`
  `05f5bbf9…d66e0b`), todas como previsto:

  | | Mutação | Previsto | Reprovou |
  |---|---|---|---|
  | R1 | `regraEditar` sem `/editar` | 2 | 2 (nova não casa; 7/editar casa) |
  | R2 | `regraNova` = `/regras` | 1 | 1 (caminho repetido) |
  | E1 | id inválido não decide | 5 | 5 (`abc`, `nova`, `0`, `007`, `undefined`) |
  | E2 | qualquer `ErroApi` vira "não encontrada" | 3 | 3 (500, sem conexão, 401) |
  | F1 | foco com índice − 1 | 2 | 2 (1 e 9 condições) |
  | F2 | foco no Limiar | 2 | 2 (1 e 9 condições) |

  **Teste no navegador (Kauan, 15/11)**: lista; criar com "1.000" → "Será salvo como R$ 1";
  409 de código repetido no campo Código, com foco; desativar e ativar, com o foco voltando
  ao botão no Esc e no Cancelar; R1 só leitura; `/regras/abc/editar` sem pedido e
  `/regras/999/editar` com 404; criação só pelo teclado; tema escuro e celular; console
  limpo. **Dois defeitos de foco relatados**: (1) **real, corrigido**: "Adicionar
  condição" focava o Limiar. Causa (lida no react-hook-form 7.92.0): sem `focusName`, o
  `append` foca o primeiro campo registrado da condição nova com o prefixo `condicoes.N.`,
  e o Limiar se registra primeiro (o `register` roda no render da linha, antes dos
  `Controller` filhos). Correção: `focusName` para a Métrica. (2) **erro de medição**:
  "Remover condição" parecia perder o foco, mas clicar no Console para digitar
  `document.activeElement` movia o foco; com a expressão ao vivo, o foco estava na Métrica
  da condição anterior, com anel visível, removendo a 2 e a 1. Código do remover mantido.
  **Conferido de novo depois da refatoração para `edicao.ts`**: "Adicionar condição" foca
  a Métrica (`button#…-metrica`) e `/regras/abc/editar` mostra "Regra não encontrada" sem
  pedido. **Dois GET /regras/999 na aba Rede**: StrictMode do modo dev (monta, desmonta e
  monta); o TanStack cancela o pedido quando sai o último observador e o `signal` foi usado
  (o primeiro aparece com 0 kB), e o `deveRepetir` nunca repete 4xx. No build de produção
  há um pedido só. Totais: Vitest **893/893** (25 arquivos; 830 da etapa 3 + 40 de
  `textos` + 9 de `rotas` + 14 de `edicao`), typecheck, lint e build ok; pytest não rodado
  (backend intocado, 236/236). Evidência: `docs/evidencias/2026-11-15_fase3_regras_vitest.txt`
  (verbose; sem e-mail nem segredo, conferido com `grep -l`).
- **Fase 3, etapa 5 — tela de Avaliações (15/11)**: rota `/avaliacoes` (saiu do
  `EmConstrucao`); página com o h1 fora do Suspense e o conteúdo por `lazy()`
  (`ConteudoAvaliacoes`), com o fallback `EsqueletoAvaliacoes` anunciando um único status.
  Formulário e histórico são independentes (erro em um não esconde o outro). Nenhum
  componente novo do shadcn e nenhuma consulta nova: o histórico é `useAvaliacoes(50)`
  (`todasAsAvaliacoes` é só o prefixo da chave) e o nome da campanha vem de
  `useCampanhas()`. **Funções puras**: `avaliacoes/historico.ts` (`celulasHistorico`,
  `textoResultado`, `textoStatus`) e `avaliacoes/formulario.ts` (`decidirEnvio`,
  `depoisDoErro`, `primeiroCampoComErro`, `semErroNoCampo`, `opcoesCampanha`,
  `avisoAtual`, `valorDoSelect`/`campanhaDoSelect`); o `.tsx` só liga estado e tela.
  **Histórico**: `incluir_pausadas` NULL é o sinal de avaliação anterior à 0003 (mesma regra
  do `textoParametros`): Período, Campanha e Incluiu pausadas mostram "não registrado", em
  itálico, e nunca "não"/"todas" (ausente ≠ falso). Depois da 0003, `campanha_id` NULL é
  "todas"; id fora da lista → "campanha nº N (fora da lista)"; lista não carregada → só o
  número. Limitação: a FK de `campanha_id` é `ON DELETE SET NULL`, então uma campanha
  apagada depois da 0003 apareceria como "todas" (campanhas não são apagadas; a
  sincronização marca REMOVED). Alertas em duas colunas, "Alertas novos" e "Já existentes"
  (descartado: as duas na mesma célula). `celulasHistorico` recebe um `Pick` com os 7
  campos que usa, para a fixture não precisar de valores inventados. **Resultado**: zero
  alertas novos é "nenhum alerta novo" (não parece falha); zero registros avaliados ganha
  a dica "confira o período e se a campanha está pausada". O link "Ver alertas" vai para
  `/alertas` sem filtro: `GET /alertas` não filtra por avaliação (só campanha, regra e
  período), e a tela é da Fase 4. **Formulário**: `useState` + `montarPedidoAvaliacao`
  (descartado: react-hook-form + zod, que duplicaria a validação do `pedido.ts`). Um estado
  de erros só, trocado inteiro a cada envio: o cliente valida antes e o servidor só
  responde se o cliente deixou passar, então os dois nunca aparecem juntos (o `juntarErros`
  do plano saiu). `decidirEnvio` decide ignorar (pedido em andamento), corrigir (com foco
  no primeiro campo da tela) ou enviar; o botão usa `aria-disabled` e o `role="status"`
  existe sempre. Erros do servidor por `errosNosCamposAvaliacao`; o resto (período
  invertido no servidor, Google, rede) vai para o `EstadoErro`. Sem a lista de campanhas,
  o select só tem "Todas". **Select do Radix com `value="todas"`**: no Radix instalado,
  `value === ""` significa "nada escolhido" e mostra o placeholder (`shouldShowPlaceholder`,
  linha 1207 de `@radix-ui/react-select/dist/index.mjs`); "Todas as campanhas" usa o valor
  `"todas"` no select e vira `""` no formulário (`campanhaDoSelect`). **Oráculo**: consulta
  só de leitura no `limen` (transação READ ONLY, `default_transaction_read_only=on`,
  colunas explícitas, sem `usuario_id`, e-mail, conta nem ID do Google), com
  `count(DISTINCT usuario_id) = 1` conferido antes; a coluna Data foi comparada com o
  `to_char(... AT TIME ZONE 'America/Fortaleza')` do PostgreSQL, e não com o Intl. As 2
  avaliações reais são do IN-02b (parâmetros NULL); os casos depois da 0003 são sintéticos.
  Nas campanhas, o id 2 é a C: procurar pela posição na lista erraria. Testes: 29 em
  `historico.test.ts` e 28 em `formulario.test.ts`. **Mutações** (script único com backup,
  `trap`, `cmp` após cada uma, sem `set -e`; troca de trecho recusada se não aparecer
  exatamente 1 vez; sha256 iguais antes e depois: `historico.ts` `c90753d9…5eadaa18`,
  `formulario.ts` `41739153…f7d0e224`), todas como previsto:

  | | Mutação | Previsto | Reprovou (de 57) |
  |---|---|---|---|
  | H1 | NULL tratado como `false` | 3 | 3 (as 2 linhas reais; sem a lista) |
  | H2 | `campanha_id` NULL depois da 0003 vira "não registrado" | 1 | 1 ("todas") |
  | H3 | coluna de novos soma os já existentes | 3 | 3 (nº 2 real; "nunca 27"; milhar) |
  | F1 | ordem dos campos com fim antes de início | 2 | 2 (`{inicio, fim}` e `{fim, inicio}`) |
  | F2 | `decidirEnvio` sem checar `pendente` | 2 | 2 (os dois "ignora") |
  | F3 | `depoisDoErro` com `restante: false` fixo | 4 | 4 (período invertido; rede; cota; não `ErroApi`) |
  | F4 | `campanhaDoSelect` sem converter `"todas"` | 2 | 2 (ida e volta; pedido sem `campanha_id`) |

  Na H3, a linha real nº 1 não pega a mutação (0 já existentes); quem pega é a nº 2 e o
  teste "9 e 18, nunca 27". Na F1, os testes de `depoisDoErro` passam, porque o `toEqual`
  ignora a ordem das chaves. **Campos escondidos do Radix**: o painel Issues do navegador
  acusava "form field should have an id or name" no `<select>` escondido (1×1,
  `aria-hidden`) do Select e no `<input>` do Checkbox. Correção sem editar
  `src/components/ui`: `name` no `<Select>` e no `<Checkbox>` do `FormularioAvaliacao`
  (`campanhaId`, `incluirPausadas`) e no `<Checkbox>` de "Regra ativa" do `FormularioRegra`
  (`field.name`; o Select dele já passava `name`). Os dois formulários não fazem envio
  nativo, então o `name` não muda o comportamento. **Build** (baixado ao abrir): **657,29
  kB** (`index` 375,75 + `card` 281,54), +1,21 kB sobre os 656,08 kB da etapa 4 (a página
  e o esqueleto entram direto pelo roteador). `ConteudoAvaliacoes` 9,20 kB. Mudou a
  divisão: o `FormularioRegra` foi de 86,18 para 55,63 kB e surgiu o pedaço comum
  `campos` (30,77 kB; select, checkbox, `api/campos.ts`), usado pelos dois formulários e
  baixado só neles. **Teste no navegador (Kauan, 15/11), aprovado**: histórico com as 2
  avaliações reais em "não registrado" e itálico; execução sem filtros com um único POST,
  resultado "nenhum alerta novo, 18 já existiam, 60 registros" e linha nova com "período
  todo/todas/não"; campanha C pausada com o aviso antes de executar e 0 registros com a
  dica; período invertido com erro e foco na Data final (`input#…-fim`) e nenhum POST;
  com rede 3G (pedido de 2 s), vários cliques geraram um único POST (sem lentidão o pedido
  leva 20 ms, e um clique duplo gera duas execuções legítimas, porque a primeira já
  terminou); avaliação só pelo teclado, tema escuro, celular com rolagem só na tabela,
  console limpo. Totais: Vitest **950/950** (27 arquivos; 893 + 29 + 28), typecheck, lint
  e build ok; pytest não rodado (backend intocado, 236/236). Evidência:
  `docs/evidencias/2026-11-15_fase3_avaliacoes_vitest.txt` (verbose; sem e-mail nem
  segredo, conferido com `grep -l`).
- **Fase 4 — tela de Alertas (16/11)**: rota `/alertas` (saiu do `EmConstrucao`, removido
  por não ter mais uso); página com o h1 fora do Suspense e o conteúdo por `lazy()`
  (`ConteudoAlertas`); o fallback `EsqueletoAlertas` anuncia um único status, e depois a
  tela tem um só `role="status"` (`textoStatusAlertas`). Nenhum endpoint novo e nenhum
  componente novo do shadcn. **O que o backend oferece** (lido antes): `GET /alertas` filtra
  por `campanha_id`, `regra_id`, `inicio` e `fim` (pela **data do registro**) e tem `limite`
  de 1 a 5000 (padrão 500); **não há paginação** (nem `offset` nem filtro por avaliação);
  ordem: data mais recente, depois o código da regra (sem desempate entre campanhas no
  mesmo dia). `valores_medidos` traz só as métricas das condições, como `str(Decimal)`;
  `condicoes` é a cópia gravada na avaliação. **Oráculo**: consulta só leitura no `limen`
  (`default_transaction_read_only=on`, `BEGIN READ ONLY`/`ROLLBACK`, colunas explícitas,
  sem `usuario_id`, e-mail nem ID do Google), com `count(DISTINCT usuario_id) = 1` conferido
  antes: 27 alertas de 13/10 a 11/11, 3 por par campanha × regra; ids 1 = A, 2 = C, 3 = B
  (procurar pela posição erraria); CTR com 28 casas; limiares com 6; a R3 com 2 condições.
  4 linhas reais (alertas 45, 9, 18 e 16) viraram a fixture de `tabela.test.ts`; os casos
  de regra editada e de valor perto do limiar são sintéticos e marcados.
  **Filtros** (`src/alertas/filtros.ts`): a URL é a única fonte (`?campanha=&regra=&inicio=
  &fim=`): enviar grava a URL, e a consulta e os erros saem dela; o link das Avaliações, o
  Voltar/Avançar e uma URL editada passam pelo mesmo caminho. Descartado: validar no envio
  e só gravar a URL válida (duas fontes de erro). Mesmas regras do `POST /avaliacoes`:
  campo vazio omitido, ids só da lista (o FastAPI aceitaria 0 e -1), datas pelo
  `validarPeriodo`, **extraído do `pedido.ts`** sem mudar comportamento (`pedido.test.ts`
  com o mesmo sha256 `7c6771e5…eb81404`, 39/39); o teste de datas dos filtros compara com
  `montarPedidoAvaliacao`, cujo oráculo é o Pydantic. O `limite` (500) vai sempre
  explícito. `montarConsultaAlertas` só espera a lista se o filtro dela estiver preenchido
  (o `/alertas` puro pede tudo em paralelo); erro vence a espera; lista que falhou chega
  como `[]` (`listaParaFiltro`) e o campo mostra o erro, em vez de esperar para sempre.
  Na tela: o foco no primeiro erro é calculado no próprio envio (`envioDosFiltros`), com as
  mesmas listas, porque a troca de URL do React Router pode chegar num render posterior; o
  rascunho acompanha a URL pelo padrão do React de ajustar o estado durante o render, sem
  remontar o formulário (remontar mandaria o foco ao `<body>`; um efeito com `setState` o
  lint recusa); o erro some do campo editado até o próximo envio (`errosVisiveis`).
  **Achado no navegador**: com `?inicio=ontem`, o `<input type="date">` recebia "ontem" e o
  navegador avisava no console ("does not conform to the required format"); o campo só
  aceita "" ou data válida. `valorDoCampoData` entrega "" nesse caso, e o rascunho guarda o
  texto da URL, para o erro continuar até a pessoa corrigir (descartado: limpar o rascunho,
  que apagaria o erro sem correção). Só no `FiltrosAlertas`: no `FormularioAvaliacao` a
  data só vem do próprio campo. **Tabela** (`src/alertas/tabela.ts`): o que disparou vem da
  **cópia das condições do alerta**, não da regra atual (que pode ter sido editada); a regra
  atual só decide o aviso "a regra mudou depois deste alerta" (`regraMudou`, com limiar
  normalizado e condições pela `ordem`; regra fora da lista → sem aviso). O banco não tem
  alertas de regra do usuário: o aviso só é coberto por teste. **Valor medido com casas
  adaptativas** (`formatarMedido`): com 2 casas, CTR `0.996` contra `< 1%` apareceria como
  "1,00% < 1%"; arredonda com pelo menos as casas do limiar (o arredondamento é monotônico,
  o valor não passa para o outro lado) e acrescenta casas enquanto parecer igual ao limiar
  sem ser (o laço termina nas casas do próprio valor). Descartado: sempre 2 casas. Uma
  previsão errada no teste: para `0.9951` contra `0.996`, o esperado escrito era "0,9951%",
  mas a função mostra "0,995%" (3 casas do limiar), já do lado certo; corrigido só o valor
  esperado. Ausente → "—" com "sem dado"; o leitor de tela ouve o operador por extenso
  ("CTR 0,57%, menor que 1%"). `textoContagem`: com 500 itens, "Mostrando os 500 alertas
  mais recentes. Use os filtros para ver os anteriores." `estadoVazioAlertas`: sem filtro
  leva às Avaliações; com filtro, "Limpar filtros". `faseAlertas` decide o que a tela
  mostra, com os filtros antes da consulta (a consulta desligada ficaria "pending" para
  sempre). `comUnidade` (`regras/textos.ts`) e `SEM_DADO` (`campanhas/dados.ts`) passaram
  a ser exportados (uma palavra em cada; testes deles intactos). **Consultas**:
  `opcoesAlertas` desligada com consulta `null` (URL inválida ou lista carregando);
  `alertasFiltrados(consulta)` fica sob o prefixo `alertas`. `chaves.alertas` entrou em
  `CHAVES_APOS_SINCRONIZAR` e `CHAVES_APOS_REGRA`, porque nome da campanha e da regra chegam
  por JOIN. **Testes antigos alterados (2 arquivos, só acréscimos)**: `consultas.test.ts` e
  `consultas-regras.test.ts`, 10 linhas trocadas pela mesma com a chave ou o texto "e
  alertas" acrescentado, mais a chave de alertas no `EM_CACHE` do primeiro (sem ela, a
  invalidação não seria vista; os testes de erro passam a provar que os alertas não são
  invalidados). **"Ver alertas"** usa `linkAlertas(estado.saida)`, com os parâmetros que o
  servidor gravou; mostra os alertas do período, inclusive os que já existiam (a API não
  filtra por avaliação). O typecheck pegou que o `EstadoExecucao` (`avaliacoes/historico.ts`)
  guardava só um `Pick` sem `campanha_id`/`inicio`/`fim`; uma linha de tipo, sem mudar
  comportamento nem o `historico.test.ts`. Descartado: guardar o corpo enviado (usaria o
  pedido, não o gravado). **Mutações** (dois scripts no scratchpad com backup, `trap`, troca
  recusada se o trecho não aparecer exatamente 1 vez, `cmp` após cada uma, sem `set -e`;
  suíte inteira em cada uma; `sha256sum -c` com SUCESSO no fim), todas como previsto:

  | | Mutação | Reprovou (de 1046; M7/M8 de 1070) |
  |---|---|---|
  | M1 | campo vazio enviado como `""` | 8 |
  | M2 | id fora da lista enviado | 4 |
  | M3 | espera as listas mesmo sem filtro | 1 |
  | M4 | espera vence o erro | 1 |
  | M5 | `>` vira `>=` no `validarPeriodo` | 2 (`filtros.test` e `pedido.test`) |
  | M6 | `linkAlertas` sem a campanha | 2 |
  | T1 | disparos montados com a regra atual | 2 |
  | T2 | valor medido sem normalizar nem arredondar | 6 |
  | T3 | aviso de limite nunca aparece | 2 |
  | T4 | `enabled: true` no `opcoesAlertas` | 1 (pelo `failureCount`) |
  | M7 | `listaParaFiltro` devolve `undefined` com erro | 1 |
  | M8 | `faseAlertas` olha a consulta antes dos filtros | 2 |

  Na M5, os casos de período dos filtros não pegam (comparam com o `pedido.ts`, que usa a
  mesma função mutada): quem pega são os testes explícitos de início igual ao fim. Na T4,
  "nenhum pedido" sozinho não pegaria (a `queryFn` lança antes do `fetch`). A previsão da
  M8 foi corrigida de 1 para 2 antes de rodar. **Build** (baixado ao abrir): **658,50 kB**
  (`index` 375,76 + `card` 282,74), +1,21 kB sobre os 657,29 kB da Fase 3 (causa não
  isolada; provável: algo agora comum às telas foi para o `card`). `ConteudoAlertas`
  9,84 kB. O pedaço `campos` (30,77 kB) virou `select` 25,79 + `checkbox` 5,10 + `filtros`
  3,46 (este comum a Avaliações e Alertas, pelo `linkAlertas`). **Teste no navegador
  (Kauan, 16/11), 8 itens aprovados**: (1) 27 alertas, com o CTR da C em 11/11 = 0,57% e o
  CPC de 13/10 = R$ 10,93, o mesmo conferido à mão na Fase 2; (2) filtro de campanha com a
  URL `?campanha=2`, 9 alertas, e Voltar/Avançar restaurando os filtros; (3) período
  invertido com erro e foco na Data final, sem pedido; (4) `?campanha=99` e `?inicio=ontem`
  com erro no campo e sem pedido de alertas; (5) estado vazio com "Limpar filtros" voltando
  aos 27; (6) "Ver alertas" das Avaliações abrindo `?campanha=2&inicio=2026-11-01&fim=
  2026-11-11` com os filtros preenchidos e os 5 alertas; (7) esqueleto com rede 3G e foco
  no h1; (8) teclado, tema escuro e celular; painel Issues "No issues". O único ajuste foi o
  aviso do `?inicio=ontem`, corrigido depois com `valorDoCampoData` (coberto por teste e
  conferido no navegador pelo Kauan em 16/11: erro no campo e console sem o aviso de formato). **Limitações
  (declarar no artigo)**: sem paginação, a tela mostra no máximo os 500 alertas mais
  recentes por filtro (avisa quando chega ao limite); o link "Ver alertas" filtra por
  campanha e período, não pela avaliação. Totais: Vitest **1079/1079** (30 arquivos; 950 +
  79 de `filtros` + 46 de `tabela` + 4 de `consultas-alertas`), typecheck, lint e build ok;
  pytest não rodado (backend intocado, 236/236). Evidência:
  `docs/evidencias/2026-11-16_fase4_alertas_vitest.txt` (verbose; sem e-mail nem segredo,
  conferido com `grep -l`).
- **Execução formal da tabela congelada (16/11)**: banco próprio `limen_execucao`
  (nunca `limen` nem `limen_teste`), criado por `execucao/preparar.py` com usuário
  próprio, R1 a R3 de `criar_regras_padrao` e uma campanha sintética (IDs fictícios
  declarados). A `DATABASE_URL` vai no comando (variável de ambiente vale mais que o
  `.env`); os scripts recusam outro banco pelo nome, conferem que a aplicação vê a mesma
  URL e perguntam ao PostgreSQL o `current_database()`; a URL nunca é impressa. Toda
  evidência é montada em memória e verificada antes de gravar (e-mail, `postgresql`,
  `usuário:senha@`, Fernet, `1//`, `ya29.`, `*_token`; a palavra "token" sozinha não,
  porque está nos textos do IN-03/IN-04); erro inesperado mostra só tipo e arquivo:linha.
  Códigos de saída: 0 ok, 1 divergência, 2 regras diferentes da planilha, 3 ambiente,
  4 evidência sensível, 5 erro inesperado. Cabeçalho de cada saída: commit, código fora
  do commit (contado; tem de ser 0) separado das evidências não commitadas (só listadas),
  sha256 da planilha, data e hora. **Método**: scripts commitados (`2fd5bcf`) antes de
  executar cenários e integração. **Trava**: `conferir_regras` compara `GET /regras` de
  cada usuário com a aba "Regras e limiares" (nomes, condições, limiares em `Decimal`) no
  início e no fim; com diferença, sai com 2 sem executar.
  **Cenários (23)**: um POST por caso, num dia próprio (o lote é tudo ou nada); rejeitado
  = 400 e dia vazio no GET. Duas camadas: aplicação (alerta gravado = "Sim") e motor
  (`avaliar()` com as regras do banco; única camada que separa "Não" de "N/A", porque o
  alerta só existe quando dispara). Observado das colunas O–R = o que o sistema entregou;
  veredito = fórmula S **e** coerência entre as camadas. Resultado: 23/23, 13 alertas
  (= soma dos "Sim" esperados), 0 indevidos, 0 omitidos nas duas camadas; avaliação com
  20 avaliados, 0 rejeitados, motor 0,205 ms.
  **Integração (12)**: IN-01 e IN-02 refeitos no navegador com o uvicorn no
  `limen_execucao` (o código mudou desde 12/11); antes do login, Sair, porque o cookie
  antigo traria um `usuario_id` que, no banco novo, é o usuário da execução. O `limen`
  ficou intacto (1 usuário, mesmo md5 antes e depois, conferido pelo Kauan). IN-02b com
  dois oráculos (números do gerador 9/9/0 e 9/9/9; conjunto exato calculado pelo motor
  puro com os limiares da planilha). IN-03 a IN-06 pelo endpoint real com a porta trocada
  por dublê, um usuário de apoio por caso (IN-05 esperou 1, 2 e 4 s, 7,0 s no total).
  IN-07 compara view, fórmula da planilha (H e I, em `Decimal`) e motor nos 20 válidos.
  IN-08/IN-09 num usuário de apoio; a R4 foi desativada depois (regras não são apagadas).
  IN-10/IN-11 com o RA-02 na campanha A do usuário Google em 12/11/2026 (fora do período
  do IN-02b). **Planilha preenchida**: cópia em `docs/evidencias/`, só colunas amarelas
  (128 células); as outras 1.002 comparadas célula por célula com o original, e o sha256
  do original inalterado; IN-10 só "Sim" com `--in10-dashboard sim`. Formatação não
  comparada.
  **Limitações (declarar no artigo)**: (1) IN-02: a sincronização não pede métricas à
  API; a prova de que vêm zeradas são os prints do Playground de 12/11 (propriedade da
  conta de teste, não do código); (2) IN-03: a renovação do token é feita pela biblioteca
  `google-ads`; o dublê só simula falha temporária seguida de sucesso; (3) IN-08: a regra
  foi criada pelo mesmo `POST /regras` que a tela usa (o formulário foi conferido no
  navegador na Fase 3). **Detalhes registrados**: as evidências `preparar` e
  `conferir_regras` são anteriores ao commit e usam o cabeçalho antigo ("Arquivos fora
  do commit"); a saída do `preparar` mostra limiares `1.00` (objeto em memória,
  `expire_on_commit=False`), e a conferência leu `1.000000` do banco; o
  `executar_cenarios` não imprime a linha "Evidência gravada" e o `preencher_planilha`
  mostra "Banco: limen_execucao" sem abrir o banco (cosméticos, mantidos para não mudar
  código depois do commit).
- **Desempenho — scripts e testes (16/11, antes de medir)**: pacote
  `backend/execucao/desempenho/` no mesmo padrão do `execucao/`, **sem alterar o `comum.py`**
  do commit `2fd5bcf` (reaproveita `Parada`, `Relatorio`, `gravar_juntos` e `rodar`;
  `_fora_do_commit` e `_git` importados). Banco próprio `limen_desempenho`: recusa `limen`,
  `limen_teste` e `limen_execucao` pelo nome, confere o `current_database()` e que o
  `app.config` vê a mesma URL; a URL nunca é impressa. O cabeçalho **para com 3** se houver
  código fora do commit (no `comum.py` ele só contava). Evidências: os padrões do `comum.py`
  mais hostname, usuário do sistema, pasta pessoal, `/home/`, `?code=` e `Bearer`, lidos na
  hora (`base.gravar` checa antes de gravar e relê depois). A versão do banco vem por
  `SHOW server_version`, porque o texto do `version()` traz "PostgreSQL", que o verificador
  recusa. O plano (B3 = 5, B4 = 30, DM, DE) é lido da planilha, nunca repetido no código.
  **Dados**: `gerar_metricas` do IN-02b (já testado, com `validar_registro`), semente
  20261116, de 01/01/2024 a 26/09/2026 (1.000 dias por campanha), IDs de campanha fictícios
  a partir de 900001; o volume N usa N/1000 campanhas; o sha256 dos 10.000 registros fica
  fixo no teste.
  **Regras R4 a R50 por fórmula, sem sorteio.** A 1ª versão tinha limiares fora das faixas
  do gerador (regras que disparavam em 100% ou em 0% dos registros) e, pela conferência em
  memória, R40 a R50 eram cópias de R4 a R14 (a fórmula se repetia a cada 36). Corrigido
  com os limiares dentro das faixas, limiar `(i // 12 + j) % 3` e operador
  `(i + 2j + i // 36) % 4`: 0 regras repetidas. Disparos em memória: DM-01 9 · DM-02 2.140 ·
  DM-03 14.081 · DM-04 90 · DM-05 21.280 · DM-06 141.269 · DM-07 900 · DM-08 213.020 ·
  DM-09 1.412.536. R15, R35, R39 e R45 nunca disparam (condições contraditórias dentro das
  faixas); ficam de propósito e vão listadas na evidência.
  **Estatística** em `Decimal` sobre ns inteiros (`perf_counter_ns`): média, mediana,
  desvio amostral (n − 1), mínimo, máximo e p95 por nearest-rank (o 29º de 30). Oráculo: o
  módulo `statistics` (float só no teste).
  **Motor (DM)**: em memória, sem banco. Dentro do cronômetro fica só
  `[motor.avaliar(r, regras) for r in registros]`; montar os registros, converter as
  regras, o `gc.collect()` e contar os disparos ficam fora. O coletor fica ligado, como no
  serviço (descartado: `gc.disable()`). Falha = exceção ou disparos diferentes da passada
  de referência. Oráculo de R1 a R3 pelos perfis do gerador.
  **Endpoints (DE)**: uvicorn real como subprocesso em 127.0.0.1:8091 (nunca a 8080; porta
  ocupada → 3), sem `--reload`, `--workers 1` e `--no-access-log` (com o log ligado, cada
  amostra pagaria a escrita de uma linha). A saída vai para `/dev/null`; o servidor roda em
  sessão própria e é encerrado no `finally` (terminate e, se preciso, kill; SIGTERM e
  SIGHUP viram interrupção), e a porta é conferida livre no fim. Cliente httpx com
  `trust_env=False` e um gancho que só aceita 127.0.0.1. Login por `/dev/login` fora do
  cronômetro; cookie e resposta não vão para a evidência, e o valor do cookie é procurado
  no texto antes de gravar. Prova de que o servidor está no banco certo: `GET /campanhas`
  (as 10 fictícias) e `GET /regras` (R1 a R10). Descartado: `TestClient` (não passa pelo
  servidor HTTP). Ordem da planilha, 5 + 30 pedidos por endpoint. Esperado em cada pedido:
  DE-01, 30 linhas (28/08 a 26/09/2026); DE-02, 500 de 21.280 (limite padrão); DE-03, P001
  a P035 inativas, que não mudam as regras ativas; DE-04 `{}` (sem período padrão: avalia
  todas as campanhas ENABLED) → 10.000 avaliados, 0 gerados e 21.280 já existentes, em
  estado estável, porque o `preparar` faz uma avaliação não medida antes.
  **Google Ads**: medido à parte e fora da planilha. Chama `porta.listar_campanhas` (a
  mesma do app, só leitura, sem `sincronizar`), 5 + 30 vezes, com 2 s entre as chamadas, e
  para na `CotaExcedida` ou no `TokenRevogado`. Exige o login OAuth no navegador, com o
  uvicorn na 8080 apontando para o `limen_desempenho`: isso cria um usuário Google com R1 a
  R3 e não muda mais nada. Sem conta conectada, sai com 3. A evidência não leva token,
  e-mail, IDs da conta (procurados como número isolado), `code=` nem `Bearer`. A latência
  inclui a rede e a renovação do access token (um `GoogleAdsClient` por chamada, como no
  app).
  **Planilha**: parte da cópia da execução formal (sha256 `940cc864…` registrado) e
  escreve só as 66 células amarelas (B5 mais D, E, F, G e I × 13 linhas). Recalcula a
  estatística a partir das amostras do `.json` e confere com a que ele registrou. A coluna H
  fica fórmula: recalcular no LibreOffice com Ctrl+Shift+F9, comparar com o "CV esperado"
  da evidência e não salvar por cima. Qualquer falha impede o preenchimento; a coluna I
  recebe as falhas das repetições medidas. O `base.cabecalho` ganhou o parâmetro
  `motivo_sem_banco`.
  **Testes**: 202 novos (base 110, endpoints 41, Google Ads 20, planilha 25, motor 6);
  pytest **438/438**. **Mutações**: script no scratchpad com backup, `trap` em EXIT, INT,
  TERM e HUP, `cmp` e sha256 depois de cada restauração, e "NÃO APLICADA" se o trecho não
  aparecer exatamente 1 vez. Foram 32, todas como previsto:

  | Arquivo | Mutações | Pegas |
  |---|---|---|
  | `base.py` | M1 desvio com n · M2 p95 arredondando para baixo · M3 mediana sem média · M4 sem `i // 36` · M5 `gravar` sem checagem local · M5b sem a checagem antes de gravar · M6 `achados` sem os locais · B1 trava aceitando outro nome · B2 cabeçalho sem parar | 8 de 9: a M5b sobreviveu, como previsto (a releitura depois de gravar basta sozinha) |
  | `medir_endpoints.py` | E1 `trust_env` · E2 porta 8080 · E3 DE-04 sem os avaliados · E4 sem o cookie · E5 um aquecimento a menos · E6 DE-03 só com o prefixo · E7 sem `--no-access-log` | 7 de 7 |
  | `medir_google_ads.py` | G1 sem interrupção · G2 sem o token · G3 sem os IDs · G4 ID como substring · G5 sem a ordem · G6 mensagem no status · G7 espera antes da 1ª | 7 de 7; a previsão da G6 foi corrigida de 2 para 5 antes de rodar |
  | `preencher_planilha.py` | P1 escreve H · P2 sem recalcular · P3 commit · P4 sha256 da cópia · P5 `_igual` direto · P6 código fora do commit · P7 resultado | 7 de 7 |
  | `medir_motor.py` | MM1 disparos diferentes não contam · MM2 oráculo sempre verdadeiro | 2 de 2 |

  A mutação "coluna I com todas as falhas" seria equivalente, porque qualquer falha já
  impede o preenchimento, e foi trocada por um teste direto de `celulas`. **Limitações
  (declarar no artigo)**: cliente, servidor e banco na mesma máquina (banco no Docker);
  DE-04 medido em estado estável, sem inserir alertas novos; o DE-02 lista 500 de 21.280
  alertas; um único perfil sintético; log de acesso desligado; a latência do Google inclui
  a rede e a renovação do token; 4 regras nunca disparam; o DM-09 guarda os 100.000
  resultados, como o serviço (pico de memória registrado na evidência).
- **Desempenho — medição (16/11)**: rodado pelo Kauan no próprio terminal, na ordem
  preparar → medir_motor → medir_endpoints → login OAuth → medir_google_ads →
  preencher_planilha; todos saíram com 0. Commit `970049d` em todas as evidências.
  **Base** (`limen_desempenho`): 10.000 métricas, sha256 dos dados `a18a636c…bd7305d`;
  R1 a R10 relidas do banco e iguais às definições; avaliação não medida com 21.280
  alertas, igual ao motor puro regra a regra. **Motor (DM)**, ms, 5 aquecimentos e 30
  repetições:

  | ID | Registros | Regras | Média | Mediana | Desvio | p95 | CV | µs/registro |
  |---|---|---|---|---|---|---|---|---|
  | DM-01 | 1.000 | 3 | 7,301 | 7,298 | 0,042 | 7,376 | 0,57% | 7,3 |
  | DM-02 | 1.000 | 10 | 24,499 | 24,435 | 0,311 | 25,220 | 1,27% | 24,5 |
  | DM-03 | 1.000 | 50 | 154,313 | 154,123 | 0,969 | 155,542 | 0,63% | 154,3 |
  | DM-04 | 10.000 | 3 | 81,162 | 80,984 | 0,737 | 82,321 | 0,91% | 8,1 |
  | DM-05 | 10.000 | 10 | 324,953 | 324,453 | 1,877 | 328,829 | 0,58% | 32,5 |
  | DM-06 | 10.000 | 50 | 1.932,343 | 1.933,707 | 9,282 | 1.947,817 | 0,48% | 193,2 |
  | DM-07 | 100.000 | 3 | 1.350,585 | 1.350,061 | 3,282 | 1.357,184 | 0,24% | 13,5 |
  | DM-08 | 100.000 | 10 | 4.065,014 | 4.063,890 | 6,352 | 4.075,272 | 0,16% | 40,7 |
  | DM-09 | 100.000 | 50 | 18.857,019 | 18.858,836 | 40,291 | 18.917,606 | 0,21% | 188,6 |

  Oráculo de R1 a R3 ok nas 9; disparos iguais à passada de referência; R15, R35, R39 e
  R45 sem disparo (previsto). **Endpoints (DE)**, uvicorn em 127.0.0.1:8091, ms:

  | ID | Endpoint | Média | Mediana | Desvio | p95 | CV |
  |---|---|---|---|---|---|---|
  | DE-01 | GET /campanhas/{id}/metricas (30 linhas) | 2,510 | 2,490 | 0,109 | 2,778 | 4,3% |
  | DE-02 | GET /alertas (500 de 21.280) | 40,080 | 39,967 | 0,613 | 41,655 | 1,5% |
  | DE-03 | POST /regras (P001 a P035, inativas) | 4,648 | 4,614 | 0,190 | 4,963 | 4,1% |
  | DE-04 | POST /avaliacoes (10.000 registros) | 3.135,410 | 3.134,511 | 58,127 | 3.230,575 | 1,9% |

  Todos os pedidos com o resultado esperado (30 linhas; 500 itens; 10.000 avaliados,
  0 gerados, 21.280 já existentes). **Google Ads (à parte, fora da planilha)**:
  `listar_campanhas`, 30 medidas ok, 3 campanhas em todas; média 1.812,280 ms, mediana
  1.787,649, desvio 271,452 (CV 15,0%), p95 2.423,349, mín 1.481,097, máx 2.811,816.
  Nada gravado no banco. **Achados**: (1) no DE-04 o motor (`duracao_motor_ms`) leva
  419,260 ms na média, **13,4%** do pedido (12,7% na mediana); o resto (cerca de 2,7 s)
  é leitura das métricas, o `INSERT … ON CONFLICT DO NOTHING` dos 21.280 alertas e a
  serialização, sem medição separada de cada parte. O gargalo é a persistência, não o
  motor. (2) Crescimento **aproximadamente linear**: com 10× registros, o tempo foi de
  9,8× a 16,6×, e o custo por par registro × regra ficou entre 2,43 µs (DM-01) e
  4,50 µs (DM-07). O DM-07 é o desvio maior (16,6× sobre o DM-04); causa não isolada
  (hipótese: coletor de lixo com os 100 mil resultados guardados). (3) Medição estável:
  CV do motor entre 0,16% e 1,27%; dos endpoints, entre 1,5% e 4,3%. **CV do DM-01**:
  0,0057 no `motor.txt` (amostras em ns) e 0,0058 na coluna H (E ÷ D com as células
  arredondadas a 3 casas: 0,042 ÷ 7,301 = 0,005753); as outras 12 linhas coincidem.
  **Conferências**: `grep -l` nas 9 evidências (padrões do `comum.py` + `/home/`,
  usuário do sistema, hostname, `code=`, `Bearer`, também no XML do `.xlsx`): o único
  achado é o nome do autor na Leia-me, célula A2, que já está na tabela congelada.
  sha256: preenchida `a1d262ce…7c9cba55`, congelada `fbbea2ec…25d6653` (inalterada),
  origem `940cc864…f0cb8b095f`, todos iguais ao registrado. **Limitações (declarar no
  artigo)**: governor da CPU em `powersave` (frequência não fixada); cliente, servidor e
  banco (Docker) na mesma máquina; pico de memória do processo de 2.455,8 MiB (2,4 GiB,
  `ru_maxrss` do processo inteiro, atribuído ao DM-09, que guarda os 100 mil
  resultados); Google Ads com CV de 15%, porque inclui a rede e a renovação do token;
  e as já listadas na entrada dos scripts.
- **Pendências da Fase 3 (15/11)**: (a) ~~mostrar abaixo do limiar o valor que será
  salvo~~ feito na etapa 4 ("Será salvo como", `previaLimiar`); (b) ~~ligar os erros do
  servidor aos campos~~ feito (etapa 3 em `api/campos.ts`, etapa 4 nas telas);
  (c) ~~build~~ **decidido no fim da etapa 4: manter e registrar, como na Fase 1**. O que
  o navegador baixa ao abrir foi de 564,01 kB (Fase 2) para **656,08 kB** (+92,07 kB;
  `index` 374,69 + `card` 281,39). Duas causas: (1) com a lista de regras, o Vite pôs o
  Radix do alert-dialog no pedaço comum `card`, que o `index.html` carrega no início
  (198,53 → 283,25 kB; depois 281,39 kB); (2) com as páginas de nova regra e edição, o
  `index` foi de 365,18 para 374,69 kB (provável: as páginas entram direto pelo roteador
  e o `RegraEditar` traz `textos.ts`, `edicao.ts`, `SeloRegra` e o cartão de referência;
  o pedaço `SeloRegra`, de 2,17 kB, foi absorvido; causa não isolada). O formulário
  (react-hook-form, resolver, select, checkbox) ficou no pedaço próprio `FormularioRegra`
  (86,18 kB), baixado só em /regras/nova e na edição. Motivo para manter: nenhum pedaço
  passa de 500 kB (o aviso não aparece). A piora é real e fica declarada; separar as
  bibliotecas com `manualChunks` fica como **opcional da limpeza final**.
- **Limpeza opcional — `textoPeriodo` duplicado (15/11, Fase 3 etapa 5)**:
  `src/avaliacoes/historico.ts` tem uma cópia de 5 linhas do trecho de período do
  `textoParametros` (`src/visao-geral/dados.ts`), para não alterar aquele arquivo na etapa.
  As duas cópias têm teste. Limpeza: exportar a função de `dados.ts` e usá-la nos dois.
- **Limpeza opcional — campos de data repetidos (16/11, Fase 4, tela de Alertas)**:
  `CampoData`, `descritor` e `Erro` (cerca de 25 linhas) existem em
  `src/avaliacoes/FormularioAvaliacao.tsx` (privados) e de novo em
  `src/alertas/FiltrosAlertas.tsx`, para não mexer no formulário já aprovado no navegador.
  Limpeza: extrair para `src/componentes/` e usar nos dois. O select de regras reaproveita
  `valorDoSelect`/`campanhaDoSelect` (`avaliacoes/formulario.ts`), que só convertem
  "todas" ↔ "" apesar do nome; renomear entra na mesma limpeza.
- **Pendências visuais da Fase 3 (15/11, plano de corte)**: (a) **primeiro item, por ser
  questão de uso**: no celular, a coluna Ações fica escondida e o selo "Desativada"
  aparece cortado até rolar a tabela para o lado (a tabela rola e é focável, mas as
  ações não ficam à vista); (b) espaço sobrando no topo da coluna Regra (selo + nome) da
  lista; (c) no celular, as colunas da direita do histórico de Avaliações ("Incluiu
  pausadas", "Alertas novos", "Já existentes") ficam cortadas até rolar a tabela para o
  lado (mesmo caso do item (a)).
- **Pendência visual da Fase 4 (16/11, plano de corte)**: no celular, a coluna "O que
  disparou" da tabela de Alertas só aparece rolando a tabela para o lado (a tabela rola e
  é focável, mas a informação principal do alerta não fica à vista). Mesmo caso da coluna
  Ações em Regras e do histórico de Avaliações (Fase 3, itens (a) e (c)); a solução pode
  ser a mesma para as três tabelas.
- **Pendências visuais da Fase 2 (15/11, plano de corte)**: (a) no celular, a coluna Dia
  da tabela diária some ao rolar para o lado; fixá-la (`sticky`) manteria a data visível;
  (b) o aviso de sucesso da sincronização (sonner) cobre o nome do usuário no topo da
  tela; mudar a posição ou o deslocamento do `Toaster`.
- **Pendência visual — rever a Visão geral para ficar mais intuitiva (14/11, baixa
  prioridade)**: entra no **plano de corte**, só depois das Fases 2 a 4, dos testes de
  desempenho, da execução da tabela congelada e da implantação. Itens: (a) ranking
  "Campanhas com mais alertas", com a contagem feita no banco, no `/resumo` (mesma decisão
  da Fase 0: agregar no banco, não no navegador); (b) clicar numa barra do gráfico leva à
  tela de Alertas filtrada por aquele dia (depende da Fase 4); (c) revisar proporção,
  destaques e espaçamentos do gráfico **sem mudar a paleta validada** (`grafico.test.ts`);
  (d) uma frase de propósito sob o título de cada página; (e) alertas descritos de forma
  concreta, por exemplo "CTR de 0,8% ficou abaixo de 1% na campanha X em 17/10", na tela de
  Alertas da Fase 4 (o alerta já guarda os valores medidos e a cópia das condições);
  (f) mais presença da cor principal do Limen e títulos um pouco maiores, **sem perder o
  contraste testado** (`contraste.test.ts`).
- **Pendência — prints de evidência das telas (14/11)**: ficam para o **final do projeto**,
  com as telas já ajustadas: tema claro, tema escuro e celular, sem e-mail e com o menu do
  usuário fechado. Até lá, as evidências de cada etapa são as saídas do pytest e do Vitest
  em `docs/evidencias/`.
- **Pendências a mencionar no artigo**: declarar o uso de IA conforme regra do iCEV
  (confirmar com o orientador); justificar Liang et al. (2009) na seção 2.5; buscar fonte
  recente (IEEE/ACM, "rule engine evaluation"); deixar explícito na metodologia o que usou
  dado real × sintético.
