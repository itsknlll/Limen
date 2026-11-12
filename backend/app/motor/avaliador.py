"""Avaliação de um registro de métricas contra um conjunto de regras.

O motor é uma função pura: não acessa banco, rede nem relógio. Recebe um
registro e as regras, e devolve o resultado de cada regra. Isso permite
testá-lo isoladamente e medir seu desempenho sem interferência da
integração externa (plano de avaliação, seção 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from .metricas import Metrica, RegistroMetricas, valor_da_metrica
from .regras import Regra
from .validacao import validar_registro


class Resultado(str, Enum):
    DISPARA = "dispara"
    NAO_DISPARA = "nao_dispara"
    NAO_AVALIAVEL = "nao_avaliavel"


@dataclass(frozen=True)
class ResultadoRegra:
    regra_id: str
    resultado: Resultado
    # Valores medidos de cada métrica usada pela regra (None = ausente/indefinido).
    # Servem para o alerta informar o valor que motivou o disparo.
    valores: dict[Metrica, Decimal | None] = field(default_factory=dict)


@dataclass(frozen=True)
class ResultadoAvaliacao:
    aceito: bool
    erros: tuple[str, ...]
    regras: dict[str, ResultadoRegra]

    @property
    def disparadas(self) -> list[str]:
        """IDs das regras que dispararam, ou seja, os alertas a gerar."""
        return [r.regra_id for r in self.regras.values() if r.resultado is Resultado.DISPARA]


def avaliar_regra(registro: RegistroMetricas, regra: Regra) -> ResultadoRegra:
    valores = {c.metrica: valor_da_metrica(registro, c.metrica) for c in regra.condicoes}

    # Se qualquer métrica da regra estiver ausente ou indefinida, a regra não é
    # avaliada, mesmo que outra condição já seja falsa. Isso torna o resultado
    # independente da ordem das condições.
    if any(v is None for v in valores.values()):
        return ResultadoRegra(regra.id, Resultado.NAO_AVALIAVEL, valores)

    dispara = all(
        c.operador.aplicar(valores[c.metrica], c.limiar)  # type: ignore[arg-type]
        for c in regra.condicoes
    )
    return ResultadoRegra(
        regra.id, Resultado.DISPARA if dispara else Resultado.NAO_DISPARA, valores
    )


def avaliar(registro: RegistroMetricas, regras: list[Regra]) -> ResultadoAvaliacao:
    """Avalia um registro contra todas as regras.

    Registro inválido é rejeitado: nenhuma regra é avaliada e todas ficam N/A.
    """
    ids = [r.id for r in regras]
    if len(ids) != len(set(ids)):
        raise ValueError("há regras com IDs repetidos")

    erros = validar_registro(registro)
    if erros:
        return ResultadoAvaliacao(
            aceito=False,
            erros=tuple(erros),
            regras={r.id: ResultadoRegra(r.id, Resultado.NAO_AVALIAVEL) for r in regras},
        )

    return ResultadoAvaliacao(
        aceito=True,
        erros=(),
        regras={r.id: avaliar_regra(registro, r) for r in regras},
    )
