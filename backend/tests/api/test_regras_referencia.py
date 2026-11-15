"""Fase 3: R1, R2 e R3 (regras de referência da tabela congelada) bloqueadas na API.

Criar, editar, desativar ou renomear para um código de referência → 409 com
tipo "regra_referencia", e o banco fica como estava. As regras do usuário
continuam livres. A execução formal não depende deste bloqueio: usa banco e
usuário próprios, com checagem das regras antes de medir.
"""

import pytest

from app.modelos import Regra, Usuario
from app.motor import CODIGOS_REFERENCIA
from app.servicos.regras import criar_regras_padrao

from ..tabela_congelada import carregar_regras

REFERENCIA = ["R1", "R2", "R3"]
CORPO_R9 = {"codigo": "R9", "nome": "CPC muito alto", "condicoes": [{"metrica": "cpc", "operador": ">", "limiar": "7.5"}]}


@pytest.fixture
def regras(cliente, sessao_teste, usuario_teste) -> dict[str, dict]:
    criar_regras_padrao(sessao_teste, usuario_teste)
    # A sessão de teste não expira no commit (expire_on_commit=False): sem isto, o GET
    # pode devolver o objeto em memória (limiar "1.00") ou relido do banco ("1.000000"),
    # conforme o coletor de lixo. Expirar faz o "antes" vir sempre do banco.
    sessao_teste.expire_all()
    return {r["codigo"]: r for r in cliente.get("/regras").json()}


def _recusado(resposta) -> None:
    assert resposta.status_code == 409, resposta.text
    assert resposta.json()["tipo"] == "regra_referencia"


def _corpo(regra: dict, **mudancas) -> dict:
    """Corpo de PUT a partir da regra como a API devolve (limiar já é texto)."""
    corpo = {
        "codigo": regra["codigo"],
        "nome": regra["nome"],
        "ativa": regra["ativa"],
        "condicoes": [{k: c[k] for k in ("metrica", "operador", "limiar")} for c in regra["condicoes"]],
    }
    return corpo | mudancas


def test_codigos_de_referencia_sao_os_da_tabela():
    assert CODIGOS_REFERENCIA == {r.id for r in carregar_regras()} == set(REFERENCIA)


@pytest.mark.parametrize("codigo", REFERENCIA)
def test_editar_referencia_e_recusado(cliente, regras, codigo):
    antes = regras[codigo]
    mudada = _corpo(antes, nome="outro nome", condicoes=[{"metrica": "ctr", "operador": "<", "limiar": "50"}])
    _recusado(cliente.put(f"/regras/{antes['id']}", json=mudada))
    assert cliente.get(f"/regras/{antes['id']}").json() == antes


@pytest.mark.parametrize("codigo", REFERENCIA)
def test_put_identico_tambem_e_recusado(cliente, regras, codigo):
    # Nenhum PUT passa: a regra fica exatamente como criar_regras_padrao a deixou.
    antes = regras[codigo]
    _recusado(cliente.put(f"/regras/{antes['id']}", json=_corpo(antes)))
    assert cliente.get(f"/regras/{antes['id']}").json() == antes


@pytest.mark.parametrize("codigo", REFERENCIA)
def test_desativar_referencia_e_recusado(cliente, regras, codigo):
    antes = regras[codigo]
    _recusado(cliente.delete(f"/regras/{antes['id']}"))
    assert cliente.get(f"/regras/{antes['id']}").json() == antes


@pytest.mark.parametrize("codigo", REFERENCIA)
def test_renomear_referencia_e_recusado(cliente, regras, codigo):
    # Só a checagem do código atual pega este caso: o código novo (R7) não é de referência.
    antes = regras[codigo]
    _recusado(cliente.put(f"/regras/{antes['id']}", json=_corpo(antes, codigo="R7")))
    assert cliente.get(f"/regras/{antes['id']}").json() == antes


@pytest.mark.parametrize("novo_codigo", ["R2", "r2"])
def test_renomear_regra_do_usuario_para_referencia_e_recusado(cliente, regras, novo_codigo):
    r9 = cliente.post("/regras", json=CORPO_R9).json()
    _recusado(cliente.put(f"/regras/{r9['id']}", json=_corpo(r9, codigo=novo_codigo)))
    assert cliente.get(f"/regras/{r9['id']}").json() == r9


@pytest.mark.parametrize("codigo", ["R1", "r1", "R3"])
def test_criar_com_codigo_de_referencia_e_recusado(cliente, codigo):
    # Usuário sem as regras padrão: sem o bloqueio, o POST passaria (não há UNIQUE a violar).
    _recusado(cliente.post("/regras", json=CORPO_R9 | {"codigo": codigo}))
    assert cliente.get("/regras").json() == []


def test_referencia_de_outro_usuario_continua_404(cliente, sessao_teste, regras):
    outro = Usuario(email="outro@limen.dev")
    sessao_teste.add(outro)
    sessao_teste.flush()
    criar_regras_padrao(sessao_teste, outro.id)
    r1_outro = sessao_teste.query(Regra).filter_by(usuario_id=outro.id, codigo="R1").one()
    # 404 antes do 409: a resposta não revela que a regra existe em outra conta.
    assert cliente.put(f"/regras/{r1_outro.id}", json=_corpo(regras["R1"])).status_code == 404
    assert cliente.delete(f"/regras/{r1_outro.id}").status_code == 404


def test_saida_marca_as_referencias(cliente, regras):
    criada = cliente.post("/regras", json=CORPO_R9).json()
    assert criada["referencia"] is False
    lista = cliente.get("/regras").json()
    assert {r["codigo"]: r["referencia"] for r in lista} == {"R1": True, "R2": True, "R3": True, "R9": False}


def test_regra_do_usuario_continua_editavel_e_desativavel(cliente, regras):
    r9 = cliente.post("/regras", json=CORPO_R9).json()
    editada = cliente.put(f"/regras/{r9['id']}", json=_corpo(r9, nome="CPC acima de 8", condicoes=[
        {"metrica": "cpc", "operador": ">", "limiar": "8"},
    ]))
    assert editada.status_code == 200, editada.text
    assert cliente.delete(f"/regras/{r9['id']}").status_code == 204
    assert cliente.get(f"/regras/{r9['id']}").json()["ativa"] is False
