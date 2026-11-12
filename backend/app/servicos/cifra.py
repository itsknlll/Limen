"""Cifragem e decifragem simétricas com Fernet (AES-128-CBC + HMAC-SHA256).

Decisão: Fernet garante autenticação do ciphertext — adulteração levanta InvalidToken,
nunca produz texto corrompido silencioso. A chave fica em CHAVE_CIFRAGEM no .env.
Alternativa descartada: AES-GCM direto — mais verboso sem vantagem relevante aqui.
"""

from cryptography.fernet import Fernet

from ..config import configuracoes

_CMD_GERAR = 'python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
_MSG_CHAVE_AUSENTE = f"CHAVE_CIFRAGEM não configurada no .env — gere com: {_CMD_GERAR}"
_MSG_CHAVE_INVALIDA = f"CHAVE_CIFRAGEM inválida no .env — gere com: {_CMD_GERAR}"


def _fernet() -> Fernet:
    if not configuracoes.chave_cifragem:
        raise ValueError(_MSG_CHAVE_AUSENTE)
    try:
        return Fernet(configuracoes.chave_cifragem.encode("ascii"))
    except Exception as exc:
        raise ValueError(_MSG_CHAVE_INVALIDA) from exc


def cifrar(texto: str) -> str:
    """Cifra uma string; retorna o ciphertext como string ASCII."""
    return _fernet().encrypt(texto.encode("utf-8")).decode("ascii")


def decifrar(cifrado: str) -> str:
    """Decifra um valor produzido por cifrar(). Levanta InvalidToken se adulterado."""
    return _fernet().decrypt(cifrado.encode("ascii")).decode("utf-8")
