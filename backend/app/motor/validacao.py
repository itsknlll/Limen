"""Validação de um registro de métricas antes da avaliação.

Política "Valores inválidos" (tabela congelada): registro com valor negativo
ou com cliques maiores que impressões é rejeitado, e nenhuma regra é avaliada.
"""

from __future__ import annotations

from .metricas import RegistroMetricas


def validar_registro(registro: RegistroMetricas) -> list[str]:
    """Lista os erros do registro. Lista vazia significa registro válido."""
    erros: list[str] = []
    campos = {
        "impressoes": registro.impressoes,
        "cliques": registro.cliques,
        "custo": registro.custo,
        "conversoes": registro.conversoes,
    }
    for nome, valor in campos.items():
        if valor is not None and valor < 0:
            erros.append(f"{nome} não pode ser negativo (recebido: {valor})")

    if (
        registro.impressoes is not None
        and registro.cliques is not None
        and registro.cliques > registro.impressoes
    ):
        erros.append(
            f"cliques ({registro.cliques}) não podem ser maiores que "
            f"impressões ({registro.impressoes})"
        )
    return erros
