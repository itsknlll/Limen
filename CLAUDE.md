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
  app/api/                  esquemas Pydantic, deps (sessão/usuário), rotas
  app/main.py               FastAPI (SessionMiddleware, handlers 400/404/409)
  alembic/versions/0001_modelo_inicial.py
  tests/                    motor (tabela + unidade), banco, api
docs/avaliacao/             tabela congelada
docs/evidencias/            prints e saídas do pytest (nome: AAAA-MM-DD_caso_descricao)
```

## Comandos

```bash
cd ~/projetos/limen && docker compose up -d        # banco (após reiniciar o PC)
cd backend && source .venv/bin/activate
pytest -q                                           # 74 testes passando em 12/11
alembic upgrade head
uvicorn app.main:app --reload                       # /docs; POST /dev/login (só em desenvolvimento)
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

## Situação (12/11/2026, 11h30)

Feito: tabela congelada (`29de91d`) · motor + 45 testes (`cfb8ac0`) · banco + migração
(`6aa88ba`) · API REST (`1e22777`) · OAuth + cifragem (`f49faf9`) · sincronização campanhas
(em andamento). Total **109 testes passando** (12/11, após sub-etapa 3).

**Integração Google Ads — estado (12/11/2026):**
- ✅ Sub-etapa 1: Login OAuth (CSRF + PKCE S256, `email_verified`)
- ✅ Sub-etapa 2: Refresh token cifrado em `Usuario.refresh_token_cifrado` (Fernet)
- ✅ Sub-etapa 3: Sincronização de campanhas — 109/109 passando + caso IN-02 aprovado.
  Evidências (12/11): `2026-11-12_IN-02_sincronizacao_real.png` (endpoint retornou
  `{"campanhas_sincronizadas": 3}`) e `2026-11-12_IN-02_campanhas_banco.png` (banco limen:
  campanhas A ENABLED 50 M, B ENABLED 80 M, C PAUSED 40 M com IDs reais e
  sincronizada_em = 2026-11-12 19:29:24 UTC).
- ⬜ Sub-etapa 4: Falhas simuladas (token expirado → renova; refresh revogado → pede
  reautorização; indisponibilidade → 3 tentativas com espera crescente; cota excedida →
  adiar e registrar o código).
- ⬜ IN-02b: Métricas sintéticas associadas às campanhas reais sincronizadas.

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
  `Usuario.refresh_token_cifrado` (ver decisão abaixo). Redireciona para `/docs` enquanto
  o frontend React não existe.
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
- **Pendências a mencionar no artigo**: declarar o uso de IA conforme regra do iCEV
  (confirmar com o orientador); justificar Liang et al. (2009) na seção 2.5; buscar fonte
  recente (IEEE/ACM, "rule engine evaluation"); deixar explícito na metodologia o que usou
  dado real × sintético.
