from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...servicos import avaliacao as servico
from ..deps import obter_sessao, obter_usuario_atual
from ..esquemas import AvaliacaoEntrada, AvaliacaoSaida

roteador = APIRouter(prefix="/avaliacoes", tags=["avaliações"])


@roteador.post("", response_model=AvaliacaoSaida, status_code=status.HTTP_201_CREATED)
def avaliar(
    entrada: AvaliacaoEntrada | None = None,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    """Executa o motor sobre as métricas guardadas e grava os alertas novos."""
    entrada = entrada or AvaliacaoEntrada()
    return servico.executar_avaliacao(
        sessao,
        usuario_id,
        campanha_id=entrada.campanha_id,
        inicio=entrada.inicio,
        fim=entrada.fim,
        incluir_pausadas=entrada.incluir_pausadas,
    )


@roteador.get("/{avaliacao_id}", response_model=AvaliacaoSaida)
def obter(
    avaliacao_id: int,
    sessao: Session = Depends(obter_sessao),
    usuario_id: int = Depends(obter_usuario_atual),
):
    avaliacao = servico.obter_avaliacao(sessao, usuario_id, avaliacao_id)
    if avaliacao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avaliação não encontrada")
    return avaliacao
