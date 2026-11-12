"""Aplicação FastAPI do Limen.

Rodar: uvicorn app.main:app --reload   (documentação interativa em /docs)
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .api.rotas import alertas, avaliacoes, campanhas, dev, oauth, regras
from .config import configuracoes
from .servicos.erros import ConflitoDados, NaoEncontrado


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

    @app.get("/saude", tags=["sistema"])
    def saude():
        return {"status": "ok"}

    for modulo in (campanhas, regras, avaliacoes, alertas):
        app.include_router(modulo.roteador)
    app.include_router(oauth.roteador)
    if configuracoes.ambiente == "desenvolvimento":
        app.include_router(dev.roteador)

    return app


app = criar_app()
