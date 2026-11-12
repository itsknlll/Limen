"""Aplicação FastAPI do Limen.

Rodar: uvicorn app.main:app --reload   (documentação interativa em /docs)
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .api.rotas import alertas, avaliacoes, campanhas, dev, oauth, regras
from .config import configuracoes
from .servicos.erros import (
    ApiIndisponivel,
    CotaExcedida,
    ConflitoDados,
    ErroGoogleAds,
    NaoEncontrado,
    TokenExpirado,
    TokenGoogleAusente,
    TokenRevogado,
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
        detalhes = [
            {"local": list(e.get("loc", [])), "mensagem": e.get("msg"), "tipo": e.get("type")}
            for e in erro.errors()
        ]
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": detalhes})

    @app.exception_handler(NaoEncontrado)
    async def nao_encontrado(_: Request, erro: NaoEncontrado):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(erro)})

    @app.exception_handler(ConflitoDados)
    async def conflito(_: Request, erro: ConflitoDados):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(erro)})

    @app.exception_handler(TokenGoogleAusente)
    async def token_google_ausente(_: Request, erro: TokenGoogleAusente):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(erro)})

    @app.exception_handler(TokenRevogado)
    async def token_revogado(_: Request, erro: TokenRevogado):
        # 409: estado inconsistente — logado no Limen, mas token Google revogado.
        # 401 está reservado para "não logado no Limen".
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Token Google revogado; faça login com o Google novamente."},
        )

    @app.exception_handler(TokenExpirado)
    async def token_expirado(_: Request, erro: TokenExpirado):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Falha temporária de autenticação com o Google; tente novamente."},
        )

    @app.exception_handler(ApiIndisponivel)
    async def api_indisponivel(_: Request, erro: ApiIndisponivel):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(erro)},
        )

    @app.exception_handler(CotaExcedida)
    async def cota_excedida(_: Request, erro: CotaExcedida):
        sufixo = f" [{erro.codigo}]" if erro.codigo else ""
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={"Retry-After": "3600"},
            content={"detail": f"Cota excedida{sufixo}; tente novamente em 1 hora."},
        )

    @app.exception_handler(ErroGoogleAds)
    async def erro_google_ads(_: Request, erro: ErroGoogleAds):
        # Captura subclasses não tratadas pelos handlers específicos acima.
        sufixo = f" [{erro.codigo}]" if erro.codigo else ""
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": f"Erro na comunicação com o Google Ads{sufixo}."},
        )

    @app.get("/saude", tags=["sistema"])
    def saude():
        return {"status": "ok"}

    for modulo in (campanhas, regras, avaliacoes, alertas):
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
