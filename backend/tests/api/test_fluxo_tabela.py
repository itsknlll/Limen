"""A tabela congelada atravessando a aplicação inteira.

Os casos válidos entram pela API (ingestão), o motor roda pela API
(avaliação), e os alertas gravados no banco são comparados com o resultado
esperado registrado na tabela. Diferente de test_cenarios_tabela.py, que testa
o motor isolado, aqui passam juntos validação, banco, view, serviço e API.
"""

from collections import defaultdict
from datetime import timedelta

from app.motor import Resultado
from app.servicos.regras import criar_regras_padrao

from .test_api import DIA, VALIDOS, ingerir


def test_alertas_gravados_batem_com_a_tabela(cliente, sessao_teste, usuario_teste, campanhas_teste):
    criar_regras_padrao(sessao_teste, usuario_teste)
    assert ingerir(cliente, campanhas_teste["A"], VALIDOS).status_code == 201
    assert cliente.post("/avaliacoes", json={}).status_code == 201

    observado = defaultdict(set)
    for alerta in cliente.get("/alertas", params={"limite": 5000}).json():
        observado[alerta["data"]].add(alerta["regra_codigo"])

    divergencias = []
    for n, cenario in enumerate(VALIDOS):
        dia = (DIA + timedelta(days=n)).isoformat()
        esperado = {r for r, res in cenario.esperados.items() if res is Resultado.DISPARA}
        if observado.get(dia, set()) != esperado:
            divergencias.append((cenario.id, sorted(esperado), sorted(observado.get(dia, set()))))

    assert divergencias == [], f"(caso, esperado, observado): {divergencias}"
