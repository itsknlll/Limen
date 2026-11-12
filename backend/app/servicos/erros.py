"""Erros de negócio. A camada de API traduz cada um para um código HTTP."""


class NaoEncontrado(Exception):
    """Recurso inexistente ou de outro usuário (HTTP 404)."""


class ConflitoDados(Exception):
    """Operação conflita com dados existentes (HTTP 409)."""
