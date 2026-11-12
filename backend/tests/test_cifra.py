"""Testes unitários do serviço de cifragem (app/servicos/cifra.py).

Não precisam de banco: testam apenas a lógica de cifrar/decifrar.
A chave é injetada via monkeypatch para isolar de qualquer .env presente.
"""

import pytest
from cryptography.fernet import Fernet, InvalidToken


@pytest.fixture(autouse=True)
def configurar_chave(monkeypatch):
    from app import config
    monkeypatch.setattr(config.configuracoes, "chave_cifragem", Fernet.generate_key().decode())


def test_cifrar_decifrar_ida_e_volta():
    """cifrar seguido de decifrar deve recuperar o texto original."""
    from app.servicos.cifra import cifrar, decifrar

    original = "tok_refresh_supersecret"
    cifrado = cifrar(original)

    assert cifrado != original          # não está em texto puro
    assert decifrar(cifrado) == original


def test_chave_ausente_levanta_erro_claro(monkeypatch):
    """Sem CHAVE_CIFRAGEM configurada → ValueError com instrução de como gerar."""
    from app import config
    monkeypatch.setattr(config.configuracoes, "chave_cifragem", None)

    from app.servicos import cifra
    # Recarregar _fernet: a função lê config em tempo de execução, sem cache
    with pytest.raises(ValueError, match="CHAVE_CIFRAGEM não configurada"):
        cifra.cifrar("qualquer")


def test_chave_invalida_levanta_erro_claro(monkeypatch):
    """Chave presente mas inválida (ex.: placeholder do .env.example) → ValueError com instrução."""
    from app import config
    monkeypatch.setattr(config.configuracoes, "chave_cifragem", "nao-e-uma-chave-fernet-valida")

    from app.servicos import cifra
    with pytest.raises(ValueError, match="CHAVE_CIFRAGEM inválida"):
        cifra.cifrar("qualquer")


def test_cifrar_mesmo_texto_gera_ciphertexts_distintos():
    """Fernet usa IV aleatório: cifrar o mesmo texto duas vezes produz resultados diferentes."""
    from app.servicos.cifra import cifrar, decifrar

    texto = "tok_refresh_supersecret"
    c1 = cifrar(texto)
    c2 = cifrar(texto)

    assert c1 != c2                   # IV diferente → ciphertext diferente
    assert decifrar(c1) == texto      # mas ambos decifram para o original
    assert decifrar(c2) == texto


def test_texto_adulterado_levanta_invalid_token():
    """Ciphertext adulterado deve levantar InvalidToken, nunca retornar lixo silencioso."""
    from app.servicos.cifra import cifrar, decifrar

    cifrado = cifrar("valor original")
    adulterado = cifrado[:-4] + "XXXX"   # corrompe os últimos 4 chars

    with pytest.raises(InvalidToken):
        decifrar(adulterado)
