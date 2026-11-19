# Limen — contexto do projeto para o Claude Code

TCC de Kauan Negreiros Lima (Engenharia de Software, iCEV), orientador Prof. Esp. Ítalo César
Carvalho Lima. Modalidade: artigo científico. Título: "Desenvolvimento e avaliação de um
motor de regras para geração de alertas sobre métricas de campanhas digitais: integração à
Google Ads API". O **motor de regras é o objeto central**; integração, persistência e
dashboard dão suporte a ele.

Histórico detalhado (decisões por fase, mutações, execução formal, desempenho e pendências visuais do plano de corte): `docs/registro-decisoes.md`.

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

## Segurança e processo (complemento de 16/11/2026)

- Nunca usar auto mode, accept edits nem as opções de não perguntar de novo; cada comando e cada edição são aprovados um a um pelo Kauan, e ao abrir cada sessão confira que o rodapé mostra manual mode on.
- Nunca usar git stash; git add só com lista explícita de arquivos, nunca ponto nem -A, com git status revisado antes, commit por git commit -F com Co-Authored-By, git log -1 --stat antes do push, push sem --force e só com aprovação.
- Banco: consulta "só de leitura no `limen` (transação READ ONLY, `default_transaction_read_only=on`, colunas explícitas, sem `usuario_id`, e-mail, conta nem ID do Google)" (`docs/registro-decisoes.md`, linhas 1099–1100).
- URL do banco: "a URL nunca é impressa" (`docs/registro-decisoes.md`, linha 1261).
- Prints de evidência: "sem e-mail e com o menu do usuário fechado" (linhas 182–183 deste arquivo), e também sem token (acréscimo de 16/11/2026).

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

## Padrões de código e de teste

Trechos citados de `docs/registro-decisoes.md` (linha de origem entre parênteses) e das memórias.

- **Espaço inseparável**: "gravado com o marcador `@@ESC_NBSP@@` trocado por `sed`, conferido com `grep -c` (0 caracteres literais)" (996–997); "Após Write/Edit, `grep -c $'\xc2\xa0'`" (memória `feedback_escape_nbsp.md`).
- **Roteiro de mutação**: "script único com backup, `trap`, `cmp` após cada uma, sem `set -e`; troca de trecho recusada se não aparecer exatamente 1 vez; sha256 iguais antes e depois" (1105–1107); "`cmp` e sha256 depois de cada restauração, e "NÃO APLICADA" se o trecho não aparecer exatamente 1 vez" (1367–1368).
- **Oráculo da saída real**: "as respostas do PostgreSQL 16 (`round()` e `trim_scale()` no `limen_teste`), copiadas no teste como vieram" (652–653); "**geradas da saída JSON por outro script** e inseridas no lugar de um marcador, sem cópia à mão" (882–883).
- **Decimais e datas como texto**: "datas sem hora formatadas partindo o texto" (411); "decimais como texto, sem `parseFloat`" (414); ver também a regra 5.
- **Lógica em `.ts`, nunca só no `.tsx`**: "dentro do `.tsx` nenhum teste do Vitest reprovaria uma mutação" (1030); "o `.tsx` só liga estado e tela" (1074).
- **shadcn só pela CLI**: "pelo CLI, um por vez, com `--dry-run` e `--view` antes" (389); "Componentes gerados (`src/components/ui/`) não são editados, para continuarem iguais ao registro" (328–329).
- **Foco**: "clicar no Console para digitar `document.activeElement` movia o foco; com a expressão ao vivo, o foco estava na Métrica" (1053–1054); memória `feedback_conferir_foco.md`.

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

## Situação (16/11/2026, atualizado após a medição de desempenho)

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
**Artigo (19/11)**: enviado ao orientador em 19/11/2026; README atualizado com a seção do
artigo (commit `04554f6`). Falta o retorno do orientador. A versão final, com revisão por
profissional de Letras e comprovante, vai até **27/11/2026**.

Depois: relatório técnico; versão final do artigo até 27/11/2026.

## Pendências

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
- Pendências visuais do plano de corte (Fases 2 a 4 e revisão da Visão geral): ver `docs/registro-decisoes.md`.
- **Pendência — prints de evidência das telas (14/11)**: ficam para o **final do projeto**,
  com as telas já ajustadas: tema claro, tema escuro e celular, sem e-mail e com o menu do
  usuário fechado. Até lá, as evidências de cada etapa são as saídas do pytest e do Vitest
  em `docs/evidencias/`.
- **Pendências a mencionar no artigo**: declarar o uso de IA conforme regra do iCEV
  (confirmar com o orientador); justificar Liang et al. (2009) na seção 2.5; buscar fonte
  recente (IEEE/ACM, "rule engine evaluation"); deixar explícito na metodologia o que usou
  dado real × sintético.
