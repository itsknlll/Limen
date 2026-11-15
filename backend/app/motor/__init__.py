"""Motor de regras do Limen: objeto central do TCC.

Pacote independente de banco, API e integração externa.
"""

from .avaliador import Resultado, ResultadoAvaliacao, ResultadoRegra, avaliar, avaliar_regra
from .metricas import Metrica, RegistroMetricas, calcular_cpc, calcular_ctr, valor_da_metrica
from .regras import CODIGOS_REFERENCIA, Condicao, Operador, Regra, regras_padrao
from .validacao import validar_registro

__all__ = [
    "CODIGOS_REFERENCIA",
    "Condicao",
    "Metrica",
    "Operador",
    "Regra",
    "RegistroMetricas",
    "Resultado",
    "ResultadoAvaliacao",
    "ResultadoRegra",
    "avaliar",
    "avaliar_regra",
    "calcular_cpc",
    "calcular_ctr",
    "regras_padrao",
    "validar_registro",
    "valor_da_metrica",
]
