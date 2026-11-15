"""Aplicação FastAPI do Limen.

Rodar: uvicorn app.main:app --reload   (documentação interativa em /docs)
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .api.rotas import alertas, avaliacoes, campanhas, dev, oauth, regras, resumo, sessao
from .config import configuracoes
from .servicos.erros import (
    ApiIndisponivel,
    CotaExcedida,
    ConflitoDados,
    ErroGoogleAds,
    NaoEncontrado,
    RegraReferencia,
    TokenExpirado,
    TokenGoogleAusente,
    TokenRevogado,
)

# `tipo` legível por máquina para cada HTTPException genérica (401 de login, 400 do
# callback OAuth, 404 de rota inexistente). Códigos fora da tabela viram "erro_http".
_TIPO_POR_STATUS = {
    status.HTTP_400_BAD_REQUEST: "requisicao_invalida",
    status.HTTP_401_UNAUTHORIZED: "nao_autenticado",
    status.HTTP_404_NOT_FOUND: "nao_encontrado",
}


def _erro(codigo_http: int, tipo: str, detail, headers: dict | None = None) -> JSONResponse:
    """Formato único de erro da API: {"detail": ..., "tipo": ...}.

    `detail` é o texto (ou a lista de validação) de sempre; `tipo` permite ao
    frontend decidir a ação (ex.: dois 409 diferentes: regra duplicada x Google
    desconectado) sem depender do texto da mensagem.
    """
    return JSONResponse(
        status_code=codigo_http, content={"detail": detail, "tipo": tipo}, headers=headers
    )


def criar_app() -> FastAPI:
    app = FastAPI(
        title="Limen API",
        version="0.1.0",
        description="Motor de regras para alertas sobre métricas de campanhas digitais (TCC).",
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=configuracoes.segredo_sessao,
        same_site="lax",
        https_only=configuracoes.ambiente != "desenvolvimento",
    )

    @app.exception_handler(RequestValidationError)
    async def erro_de_validacao(_: Request, erro: RequestValidationError):
        # 400 (e não o 422 padrão do FastAPI): é o código registrado na tabela congelada (IN-09).
        # O "tipo" de cada item da lista é o do Pydantic; o "tipo" externo é o da API.
        detalhes = [
            {"local": list(e.get("loc", [])), "mensagem": e.get("msg"), "tipo": e.get("type")}
            for e in erro.errors()
        ]
        return _erro(status.HTTP_400_BAD_REQUEST, "validacao", detalhes)

    @app.exception_handler(StarletteHTTPException)
    async def erro_http(_: Request, erro: StarletteHTTPException):
        # Cobre HTTPException do FastAPI (subclasse) e os 404/405 do roteamento.
        tipo = _TIPO_POR_STATUS.get(erro.status_code, "erro_http")
        return _erro(erro.status_code, tipo, erro.detail, getattr(erro, "headers", None))

    @app.exception_handler(NaoEncontrado)
    async def nao_encontrado(_: Request, erro: NaoEncontrado):
        return _erro(status.HTTP_404_NOT_FOUND, "nao_encontrado", str(erro))

    @app.exception_handler(ConflitoDados)
    async def conflito(_: Request, erro: ConflitoDados):
        return _erro(status.HTTP_409_CONFLICT, "conflito", str(erro))

    @app.exception_handler(RegraReferencia)
    async def regra_referencia(_: Request, erro: RegraReferencia):
        return _erro(status.HTTP_409_CONFLICT, "regra_referencia", str(erro))

    @app.exception_handler(TokenGoogleAusente)
    async def token_google_ausente(_: Request, erro: TokenGoogleAusente):
        return _erro(status.HTTP_409_CONFLICT, "token_google_ausente", str(erro))

    @app.exception_handler(TokenRevogado)
    async def token_revogado(_: Request, erro: TokenRevogado):
        # 409: estado inconsistente — logado no Limen, mas token Google revogado.
        # 401 está reservado para "não logado no Limen".
        return _erro(
            status.HTTP_409_CONFLICT,
            "token_google_revogado",
            "Token Google revogado; faça login com o Google novamente.",
        )

    @app.exception_handler(TokenExpirado)
    async def token_expirado(_: Request, erro: TokenExpirado):
        return _erro(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "google_autenticacao_temporaria",
            "Falha temporária de autenticação com o Google; tente novamente.",
        )

    @app.exception_handler(ApiIndisponivel)
    async def api_indisponivel(_: Request, erro: ApiIndisponivel):
        return _erro(status.HTTP_503_SERVICE_UNAVAILABLE, "google_ads_indisponivel", str(erro))

    @app.exception_handler(CotaExcedida)
    async def cota_excedida(_: Request, erro: CotaExcedida):
        sufixo = f" [{erro.codigo}]" if erro.codigo else ""
        return _erro(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "cota_excedida",
            f"Cota excedida{sufixo}; tente novamente em 1 hora.",
            headers={"Retry-After": "3600"},
        )

    @app.exception_handler(ErroGoogleAds)
    async def erro_google_ads(_: Request, erro: ErroGoogleAds):
        # Captura subclasses não tratadas pelos handlers específicos acima.
        sufixo = f" [{erro.codigo}]" if erro.codigo else ""
        return _erro(
            status.HTTP_502_BAD_GATEWAY,
            "erro_google_ads",
            f"Erro na comunicação com o Google Ads{sufixo}.",
        )

    @app.get("/saude", tags=["sistema"])
    def saude():
        return {"status": "ok"}

    for modulo in (sessao, campanhas, regras, avaliacoes, alertas, resumo):
        app.include_router(modulo.roteador)
    app.include_router(oauth.roteador)
    if configuracoes.ambiente == "desenvolvimento":
        app.include_router(dev.roteador)

    _corrigir_openapi_422_para_400(app)
    return app


def _corrigir_openapi_422_para_400(app: FastAPI) -> None:
    """Substitui 422 → 400 na documentação OpenAPI gerada pelo FastAPI.

    A API devolve 400 para erros de validação (IN-09), mas o FastAPI documenta 422
    por padrão. Sobrescrever app.openapi() é o ponto correto: age sobre o esquema
    final, sem repetir responses= em cada rota.
    """
    original = app.openapi

    def openapi_corrigido() -> dict:
        schema = original()
        for path_item in schema.get("paths", {}).values():
            for operacao in path_item.values():
                if isinstance(operacao, dict):
                    respostas = operacao.get("responses", {})
                    if "422" in respostas:
                        respostas["400"] = respostas.pop("422")
                        respostas["400"]["description"] = "Erro de validação"
        return schema

    app.openapi = openapi_corrigido


app = criar_app()
