"""Leitura da tabela de limiares congelada (docs/avaliacao, commit 29de91d).

Os testes do motor usam a tabela como oráculo: os resultados esperados vêm
dela, e não do código. Assim, o teste confronta o comportamento observado com
o que foi registrado antes da implementação (método dedutivo do plano).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from app.motor import Condicao, Metrica, Operador, Regra, RegistroMetricas, Resultado

CAMINHO_TABELA = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "avaliacao"
    / "Tabela_limiares_TCC_motor_de_regras.xlsx"
)

PRIMEIRA_LINHA_CENARIOS = 5

_ESPERADO = {
    "Sim": Resultado.DISPARA,
    "Não": Resultado.NAO_DISPARA,
    "N/A": Resultado.NAO_AVALIAVEL,
}


@dataclass(frozen=True)
class Cenario:
    id: str
    eixo: str
    descricao: str
    registro: RegistroMetricas
    aceito_esperado: bool
    esperados: dict[str, Resultado]


def _decimal(valor) -> Decimal | None:
    # str() evita levar para o Decimal o erro de representação do float lido do xlsx
    return None if valor is None else Decimal(str(valor))


def _inteiro(valor) -> int | None:
    return None if valor is None else int(valor)


def _abrir():
    if not CAMINHO_TABELA.exists():
        raise FileNotFoundError(f"Tabela congelada não encontrada em {CAMINHO_TABELA}")
    return load_workbook(CAMINHO_TABELA, data_only=False, read_only=True)


def carregar_regras() -> list[Regra]:
    """Monta R1, R2 e R3 com os limiares lidos da aba 'Regras e limiares'."""
    planilha = _abrir()["Regras e limiares"]
    limiares = {
        linha[0]: linha[4]
        for linha in planilha.iter_rows(min_row=4, max_row=6, values_only=True)
    }
    return [
        Regra(
            "R1",
            "CTR baixo",
            # A planilha guarda o CTR como fração (1% = 0,01); o motor usa porcentagem.
            (Condicao(Metrica.CTR, Operador.MENOR, _decimal(limiares["R1"]) * 100),),
        ),
        Regra(
            "R2",
            "CPC alto",
            (Condicao(Metrica.CPC, Operador.MAIOR, _decimal(limiares["R2"])),),
        ),
        Regra(
            "R3",
            "Custo sem conversão",
            (
                Condicao(Metrica.CUSTO, Operador.MAIOR, _decimal(limiares["R3"])),
                Condicao(Metrica.CONVERSOES, Operador.IGUAL, Decimal("0")),
            ),
        ),
    ]


def carregar_cenarios() -> list[Cenario]:
    """Lê os casos da aba 'Cenários de regras' (colunas A–G de entrada, J–M esperadas)."""
    planilha = _abrir()["Cenários de regras"]
    cenarios: list[Cenario] = []
    for linha in planilha.iter_rows(min_row=PRIMEIRA_LINHA_CENARIOS, values_only=True):
        if linha[0] is None:
            break
        id_, eixo, descricao, impressoes, cliques, custo, conversoes = linha[:7]
        registro_esperado, r1, r2, r3 = linha[9:13]
        cenarios.append(
            Cenario(
                id=id_,
                eixo=eixo,
                descricao=descricao,
                registro=RegistroMetricas(
                    impressoes=_inteiro(impressoes),
                    cliques=_inteiro(cliques),
                    custo=_decimal(custo),
                    conversoes=_decimal(conversoes),
                ),
                aceito_esperado=(registro_esperado == "Aceito"),
                esperados={"R1": _ESPERADO[r1], "R2": _ESPERADO[r2], "R3": _ESPERADO[r3]},
            )
        )
    return cenarios
