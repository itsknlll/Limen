"""Regras do usuário: criação, alteração e conversão para o formato do motor."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .. import motor
from ..modelos import Condicao, Regra
from .erros import ConflitoDados, NaoEncontrado


def para_motor(regra: Regra) -> motor.Regra:
    """Converte a regra do banco para o objeto puro que o motor avalia."""
    return motor.Regra(
        id=regra.codigo,
        nome=regra.nome,
        condicoes=tuple(
            motor.Condicao(
                motor.Metrica(c.metrica), motor.Operador(c.operador), Decimal(c.limiar)
            )
            for c in regra.condicoes
        ),
    )


def _condicoes_do_banco(condicoes) -> list[Condicao]:
    return [
        Condicao(ordem=i, metrica=c.metrica.value, operador=c.operador.value, limiar=c.limiar)
        for i, c in enumerate(condicoes, start=1)
    ]


def listar_regras(sessao: Session, usuario_id: int, apenas_ativas: bool = False) -> list[Regra]:
    consulta = (
        select(Regra)
        .where(Regra.usuario_id == usuario_id)
        .options(selectinload(Regra.condicoes))
        .order_by(Regra.codigo)
    )
    if apenas_ativas:
        consulta = consulta.where(Regra.ativa.is_(True))
    return list(sessao.scalars(consulta))


def obter_regra(sessao: Session, usuario_id: int, regra_id: int) -> Regra:
    regra = sessao.scalar(
        select(Regra)
        .where(Regra.id == regra_id, Regra.usuario_id == usuario_id)
        .options(selectinload(Regra.condicoes))
    )
    if regra is None:
        raise NaoEncontrado("Regra não encontrada")
    return regra


def criar_regra(sessao: Session, usuario_id: int, codigo: str, nome: str, ativa: bool, condicoes) -> Regra:
    regra = Regra(
        usuario_id=usuario_id,
        codigo=codigo,
        nome=nome,
        ativa=ativa,
        condicoes=_condicoes_do_banco(condicoes),
    )
    sessao.add(regra)
    try:
        sessao.commit()
    except IntegrityError as erro:
        sessao.rollback()
        raise ConflitoDados(f"Já existe uma regra com o código {codigo}") from erro
    return obter_regra(sessao, usuario_id, regra.id)


def atualizar_regra(
    sessao: Session, usuario_id: int, regra_id: int, codigo: str, nome: str, ativa: bool, condicoes
) -> Regra:
    regra = obter_regra(sessao, usuario_id, regra_id)
    regra.codigo = codigo
    regra.nome = nome
    regra.ativa = ativa
    # Substitui as condições. Alertas antigos não mudam: guardam uma cópia das condições.
    regra.condicoes.clear()
    sessao.flush()
    regra.condicoes.extend(_condicoes_do_banco(condicoes))
    try:
        sessao.commit()
    except IntegrityError as erro:
        sessao.rollback()
        raise ConflitoDados(f"Já existe uma regra com o código {codigo}") from erro
    return obter_regra(sessao, usuario_id, regra.id)


def desativar_regra(sessao: Session, usuario_id: int, regra_id: int) -> None:
    """Regras não são apagadas, para preservar o histórico de alertas."""
    regra = obter_regra(sessao, usuario_id, regra_id)
    regra.ativa = False
    sessao.commit()


def criar_regras_padrao(sessao: Session, usuario_id: int) -> int:
    """Cria R1, R2 e R3 (limiares da tabela congelada) se o usuário ainda não tem regras."""
    if listar_regras(sessao, usuario_id):
        return 0
    for regra in motor.regras_padrao():
        sessao.add(
            Regra(
                usuario_id=usuario_id,
                codigo=regra.id,
                nome=regra.nome,
                ativa=True,
                condicoes=_condicoes_do_banco(regra.condicoes),
            )
        )
    sessao.commit()
    return 3
