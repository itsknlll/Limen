"""Regras configuráveis do motor.

Uma regra é um conjunto de condições ligadas por E (todas precisam ser
verdadeiras para a regra disparar). Cada condição compara uma métrica com um
limiar usando um operador. Assim, novas regras são criadas por configuração,
sem alterar o código do motor.

Política de igualdade (tabela congelada): as regras padrão usam comparação
estrita (< e >), então um valor igual ao limiar não dispara alerta.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Callable

from .metricas import Metrica


class Operador(str, Enum):
    MENOR = "<"
    MENOR_OU_IGUAL = "<="
    MAIOR = ">"
    MAIOR_OU_IGUAL = ">="
    IGUAL = "=="

    def aplicar(self, valor: Decimal, limiar: Decimal) -> bool:
        return _FUNCOES[self](valor, limiar)


_FUNCOES: dict[Operador, Callable[[Decimal, Decimal], bool]] = {
    Operador.MENOR: operator.lt,
    Operador.MENOR_OU_IGUAL: operator.le,
    Operador.MAIOR: operator.gt,
    Operador.MAIOR_OU_IGUAL: operator.ge,
    Operador.IGUAL: operator.eq,
}


@dataclass(frozen=True)
class Condicao:
    metrica: Metrica
    operador: Operador
    limiar: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.limiar, Decimal):
            raise TypeError("o limiar deve ser Decimal, para evitar erros de ponto flutuante")
        if self.limiar < 0:
            raise ValueError(f"limiar não pode ser negativo (recebido: {self.limiar})")


@dataclass(frozen=True)
class Regra:
    id: str
    nome: str
    condicoes: tuple[Condicao, ...]

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("a regra precisa de um identificador")
        if not self.condicoes:
            raise ValueError("a regra precisa de pelo menos uma condição")


def regras_padrao() -> list[Regra]:
    """As três regras e limiares registrados na tabela congelada (v1.0)."""
    return [
        Regra(
            id="R1",
            nome="CTR baixo",
            condicoes=(Condicao(Metrica.CTR, Operador.MENOR, Decimal("1.00")),),
        ),
        Regra(
            id="R2",
            nome="CPC alto",
            condicoes=(Condicao(Metrica.CPC, Operador.MAIOR, Decimal("5.00")),),
        ),
        Regra(
            id="R3",
            nome="Custo sem conversão",
            condicoes=(
                Condicao(Metrica.CUSTO, Operador.MAIOR, Decimal("100.00")),
                Condicao(Metrica.CONVERSOES, Operador.IGUAL, Decimal("0")),
            ),
        ),
    ]


# Códigos das regras de referência da tabela congelada (R1, R2, R3). A API recusa
# criar, editar ou desativar regras com esses códigos (HTTP 409, tipo
# "regra_referencia"): só nascem em criar_regras_padrao, com os limiares da tabela.
# A execução formal não depende deste bloqueio: usa banco e usuário próprios.
CODIGOS_REFERENCIA: frozenset[str] = frozenset(r.id for r in regras_padrao())
