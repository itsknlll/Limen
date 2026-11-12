from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ...servicos import regras as servico
from ..deps import obter_sessao, obter_usuario_atual
from ..esquemas import RegraEntrada, RegraSaida

roteador = APIRouter(prefix="/regras", tags=["regras"])


@roteador.get("", response_model=list[RegraSaida])
def listar(
    apenas_ativas: bool = False,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    return servico.listar_regras(sessao, usuario_id, apenas_ativas)


@roteador.post("", response_model=RegraSaida, status_code=status.HTTP_201_CREATED)
def criar(
    entrada: RegraEntrada,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    return servico.criar_regra(
        sessao, usuario_id, entrada.codigo, entrada.nome, entrada.ativa, entrada.condicoes
    )


@roteador.get("/{regra_id}", response_model=RegraSaida)
def obter(
    regra_id: int,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    return servico.obter_regra(sessao, usuario_id, regra_id)


@roteador.put("/{regra_id}", response_model=RegraSaida)
def atualizar(
    regra_id: int,
    entrada: RegraEntrada,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    return servico.atualizar_regra(
        sessao, usuario_id, regra_id, entrada.codigo, entrada.nome, entrada.ativa, entrada.condicoes
    )


@roteador.delete("/{regra_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar(
    regra_id: int,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    """Desativa a regra (não apaga, para manter o histórico de alertas)."""
    servico.desativar_regra(sessao, usuario_id, regra_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
