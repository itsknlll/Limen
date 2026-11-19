# Limen

Motor de regras para geração de alertas sobre métricas de campanhas digitais, integrado à
Google Ads API. Trabalho de Conclusão de Curso (artigo científico) em Engenharia de
Software no iCEV.

## O que é e que problema resolve

Quem gerencia campanhas de mídia paga precisa perceber a tempo quando uma métrica sai do
esperado, mas acompanhar
painéis manualmente é lento e sujeito a esquecimento. O Limen avalia as métricas diárias
de cada campanha contra regras com limiares configuráveis e grava um alerta sempre que uma
regra é violada, guardando o valor medido e uma cópia do limiar usado.

O **motor de regras é o objeto central** do trabalho. A integração com a Google Ads API, a
persistência em PostgreSQL e o dashboard existem para alimentá-lo e mostrar o resultado.

## Funcionalidades por tela

| Tela | O que faz |
|---|---|
| Entrar | Login com a conta Google (OAuth 2.0). |
| Visão geral | Indicadores do resumo, gráfico de alertas por dia (cores por regra), alertas por regra e últimas avaliações, com estados de carregando, vazio e erro. |
| Campanhas | Lista das campanhas sincronizadas da Google Ads API e botão de sincronizar. |
| Campanha | Métricas diárias de uma campanha. |
| Regras | Lista com ativar e desativar (as regras de referência R1 a R3 são só leitura), criação e edição, com prévia "Será salvo como" e erros do servidor exibidos nos campos. |
| Avaliações | Executa uma avaliação (campanha, período, opção de incluir campanhas pausadas, com aviso) e mostra o histórico com os parâmetros usados. |
| Alertas | Lista de alertas com filtros por campanha, regra e período (guardados na URL), mostrando o valor medido e o limiar que dispararam cada alerta. |

## Arquitetura e stack

```
docker-compose.yml          PostgreSQL 16 (bancos limen e limen_teste; porta 5433)
infra/postgres/init/        script que cria o banco limen_teste
backend/
  app/motor/                motor puro, sem banco nem rede: métricas, validação, regras, avaliador
  app/modelos.py            modelo relacional e a view vw_metrica_diaria (somente leitura)
  app/servicos/             regras, campanhas, avaliação, alertas, erros
  app/servicos/sincronizacao/  porta para a Google Ads API, cliente real, sincronizador
  app/servicos/sinteticas/  gerador de métricas sintéticas (puro, semente fixa) e semeador
  app/api/                  esquemas Pydantic, dependências (sessão, usuário), rotas
  app/main.py               aplicação FastAPI
  alembic/versions/         migrações 0001 a 0003
  execucao/                 scripts da execução formal e da medição de desempenho
  tests/                    testes do motor, do banco e da API
frontend/                   dashboard React + TypeScript (Vite)
docs/avaliacao/             tabela de avaliação congelada
docs/evidencias/            saídas de testes, execuções e prints
docs/registro-decisoes.md   histórico de decisões, mutações e resultados
```

Decisões principais:

- O motor não conhece banco nem rede: recebe métricas e regras e devolve as violações.
  Isso permite testá-lo diretamente contra a tabela de casos esperados.
- Valores monetários e limiares usam `Decimal` no Python e `NUMERIC` no banco, nunca
  ponto flutuante.
- A Google Ads API (v26) é usada de verdade para a autorização e para a estrutura das
  campanhas. Como contas de teste não veiculam anúncios, as métricas são **sintéticas**,
  geradas com semente fixa, associadas aos IDs reais das campanhas e marcadas com
  `origem='sintetica'`.
- O refresh token do Google é guardado cifrado no banco (Fernet).
- Erros de validação da API respondem 400.

Versões usadas no desenvolvimento:

| Camada | Componentes |
|---|---|
| Banco | PostgreSQL 16 (imagem `postgres:16`), Docker Compose |
| Backend | Python 3.12, FastAPI 0.162.5, Uvicorn 0.54.0, SQLAlchemy 2.1.8, Alembic 1.20.1, psycopg 3.3.9, Pydantic 2.14.3, pydantic-settings 2.16.2, cryptography 50.0.2, google-ads 35.1.0 |
| Testes do backend | pytest 9.1.1, openpyxl 3.1.5 |
| Frontend | Node.js 22.22.0 ou superior, Vite 8.3.8, React 19.3.1, TypeScript 5.9.3, React Router 8.5.1, TanStack Query 5.107.1, Recharts 3.10.1, Tailwind CSS 4.3.5, shadcn/ui |
| Testes do frontend | Vitest 5.1.0 |

## Como rodar localmente

Pré-requisitos: Docker com Docker Compose, Python 3.12 ou superior (no Ubuntu, com o
pacote `python3-venv`) e Node.js 22.22.0 ou superior. O `frontend/.npmrc` usa
`engine-strict=true`, então o `npm` recusa versões mais antigas do Node.

### 1. Banco de dados

Na raiz do repositório:

```bash
docker compose up -d
```

Sobe o container `limen-db` na porta **5433** (para não conflitar com um PostgreSQL local
na 5432). Na primeira criação do volume, o script de `infra/postgres/init/` cria também o
banco `limen_teste`. Depois de reiniciar o computador, rode o comando de novo.

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Edite o `backend/.env` (ele não vai para o git):

- `DATABASE_URL` e `DATABASE_URL_TESTE`: troque `USUARIO` e `SENHA` pelos valores de
  `POSTGRES_USER` e `POSTGRES_PASSWORD` do `docker-compose.yml`.
- `SEGREDO_SESSAO` e `CHAVE_CIFRAGEM`: gere os valores com os comandos indicados nos
  comentários do próprio `.env.example`.
- As variáveis `GOOGLE_*` só são necessárias para conectar a Google Ads API (próxima seção).

Crie as tabelas e suba a API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8080
```

A documentação interativa da API fica em http://localhost:8080/docs.

### 3. Frontend

Em outro terminal:

```bash
cd frontend
npm ci
npm run dev
```

O dashboard abre em http://localhost:5173. O Vite repassa as chamadas `/api` para o
backend na porta 8080.

### 4. Login de desenvolvimento

Com `AMBIENTE=desenvolvimento` no `.env`, o backend expõe rotas de apoio em `/dev`. Para
entrar sem conta Google:

1. Abra http://localhost:8080/docs e execute `POST /dev/login`. Ele cria (ou reutiliza) um
   usuário de desenvolvimento e abre a sessão.
2. Abra http://localhost:5173. O cookie de sessão é por host, não por porta, então a
   sessão aberta na 8080 vale no dashboard.

Sem a Google Ads API conectada não há campanhas, e as telas aparecem vazias. Fora do seu
computador, use outro valor em `AMBIENTE` para desligar as rotas `/dev`.

## Conectar uma conta Google Ads de teste

O Limen foi desenvolvido com uma conta de administrador (MCC) de teste e uma conta cliente
de teste. Os passos, em alto nível:

1. No Google Cloud, crie um projeto com acesso à Google Ads API.
2. Crie um cliente OAuth do tipo **Aplicativo da Web** e cadastre a URI de redirecionamento
   `http://localhost:8080/api/oauth/google/callback`. O escopo usado é
   `https://www.googleapis.com/auth/adwords`.
3. Baixe o `client_secret.json` para uma pasta **fora do repositório** e aponte
   `GOOGLE_CLIENT_SECRET_FILE` para ele. Não copie o `client_id` nem o `client_secret` para
   o `.env`.
4. Crie as contas de teste e preencha `GOOGLE_LOGIN_CUSTOMER_ID` (a MCC) e
   `GOOGLE_CUSTOMER_ID` (a conta cliente), com 10 dígitos e sem hífens.
5. Reinicie o backend, use **Entrar com Google** na tela Entrar e sincronize na tela
   Campanhas.
6. Como contas de teste têm métricas zeradas, gere as métricas sintéticas em
   http://localhost:8080/docs com `POST /dev/metricas-sinteticas` (semente fixa; rodar de
   novo não duplica).

Documentação oficial:

- Contas de teste: https://developers.google.com/google-ads/api/docs/best-practices/test-accounts
- OAuth 2.0 na Google Ads API: https://developers.google.com/google-ads/api/docs/oauth/overview
- Estrutura das chamadas e cabeçalho `login-customer-id`: https://developers.google.com/google-ads/api/docs/concepts/call-structure

## Testes

Backend (com o banco no ar e o venv ativo):

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Os testes de banco usam `DATABASE_URL_TESTE`. O esquema desse banco é apagado e recriado
pelas próprias migrações a cada execução, por isso ele nunca deve apontar para o `limen`.
Sem `DATABASE_URL_TESTE`, esses testes são pulados.

Frontend:

```bash
cd frontend
npm test            # Vitest (funções puras, sem DOM nem rede)
npm run typecheck
npm run lint
npm run build
```

Contagens em 16/11/2026: **pytest 438 passando** (com 1 aviso de depreciação do Starlette
sobre o `httpx` no cliente de testes) e **Vitest 1079 passando** em 30 arquivos.

Além dos testes, a lógica crítica (motor, cálculos, isolamento entre usuários e erros)
passou por testes de mutação manuais: um trecho é alterado de propósito, confere-se qual
teste reprova e o arquivo é restaurado e conferido. Cada mutação está documentada em
`docs/registro-decisoes.md`. Nos scripts de desempenho foram aplicadas 32 mutações: 31
foram detectadas pelos testes, e a única sobrevivente (M5b) era prevista, porque a releitura
feita depois de gravar já cobre sozinha a checagem removida.

## Artigo do TCC

- Título: *Desenvolvimento e avaliação de um motor de regras para geração de alertas sobre
  métricas de campanhas digitais: integração à Google Ads API*.
- Autor: Kauan Negreiros Lima.
- Orientador: Prof. Esp. Ítalo César Carvalho Lima.
- Curso: Engenharia de Software, iCEV, 2026.
- Status: versão submetida ao orientador em novembro de 2026.
- A versão do código avaliada no artigo corresponde à tag `tcc-2026`.

## Avaliação do TCC

A avaliação parte da tabela `docs/avaliacao/Tabela_limiares_TCC_motor_de_regras.xlsx`,
**congelada no commit `29de91d` (12/11/2026), antes de qualquer código**, com os cenários,
limiares, políticas e resultados esperados.

**Execução formal (16/11/2026)**: em um banco separado (`limen_execucao`, criado por
`backend/execucao/preparar.py`), com o código igual ao do commit `2fd5bcf` em todas as
execuções.

- Cenários: **23 de 23 corretos**, com 13 alertas gerados (os 13 esperados), 0 alertas
  indevidos e 0 omitidos, tanto pela aplicação quanto pelo motor isolado.
- Integração: **12 de 12 conferem**. Os casos IN-01 e IN-02 foram refeitos com a API real
  no navegador, e o IN-10 foi conferido no dashboard.

**Desempenho (16/11/2026)**: scripts em `backend/execucao/desempenho/`, com o código igual
ao do commit `970049d` em todas as medições.

- Motor (DM): **9 de 9** sem falhas.
- Endpoints (DE): **4 de 4** sem falhas (`GET /campanhas/{id}/metricas`, `GET /alertas`,
  `POST /regras`, `POST /avaliacoes`).
- Chamadas à Google Ads API, medidas à parte: **30 de 30**.

Evidências em `docs/evidencias/` (nomes no padrão `AAAA-MM-DD_caso_descricao`):

- `2026-11-16_execucao_*`: saídas, JSON e planilha preenchida da execução formal.
- `2026-11-16_IN-01_*`, `2026-11-16_IN-02_*`, `2026-11-16_IN-10_*`: prints dos casos de
  integração.
- `2026-11-16_desempenho_*`: saídas, JSON e planilha preenchida do desempenho.

O raciocínio de cada etapa, as alternativas descartadas e as mutações estão em
`docs/registro-decisoes.md`.

## Limitações conhecidas

- As métricas são sintéticas: contas de teste da Google Ads API não veiculam anúncios. A
  API real é usada só para autorização e estrutura das campanhas.
- Com o app OAuth em modo "Testando", o refresh token expira em cerca de 7 dias e é preciso
  entrar com Google de novo.
- Roda apenas em ambiente local de desenvolvimento; não há configuração de implantação.
- Os testes do frontend cobrem as funções puras; testes de ponta a ponta no navegador
  (Playwright) ficaram para depois.
- Duas limpezas opcionais de código duplicado no frontend estão registradas e não foram
  feitas.

## Uso de IA no desenvolvimento

O desenvolvimento e a redação contaram com apoio de ferramentas de IA, entre elas o Claude
Code (Anthropic), usado como assistente de programação na escrita de código, testes,
scripts e documentação. Cada comando e cada edição foram aprovados um a um pelo autor, com
uma exceção em 16/11/2026, em que uma sessão abriu em modo automático e rodou só comandos
de leitura antes de ser interrompida, registrada em `docs/registro-decisoes.md`. A tabela
de avaliação foi congelada antes de qualquer código. As decisões de projeto, os critérios
de avaliação e a interpretação dos resultados são de responsabilidade do autor.

## Autor e orientação

- Autor: Kauan Negreiros Lima, Engenharia de Software, iCEV.
- Orientador: Prof. Esp. Ítalo César Carvalho Lima.
