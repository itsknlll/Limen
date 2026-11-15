"""Contratos de entrada e saída da API (validados pelo Pydantic).

A validação de um registro de métricas reaproveita `validar_registro` do
motor: a mesma regra de validade vale no motor, na API e no banco (CHECK).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from ..motor import CODIGOS_REFERENCIA, Metrica, Operador, RegistroMetricas, validar_registro


# --- Regras ---------------------------------------------------------------

class CondicaoEntrada(BaseModel):
    metrica: Metrica
    operador: Operador
    limiar: Decimal = Field(ge=0, max_digits=18, decimal_places=6)


class RegraEntrada(BaseModel):
    codigo: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    nome: str = Field(min_length=1, max_length=120)
    ativa: bool = True
    condicoes: list[CondicaoEntrada] = Field(min_length=1, max_length=10)


class CondicaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ordem: int
    metrica: str
    operador: str
    limiar: Decimal


class RegraSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nome: str
    ativa: bool
    condicoes: list[CondicaoSaida]

    @computed_field
    @property
    def referencia(self) -> bool:
        """R1 a R3 (tabela congelada): a API recusa criar, editar ou desativar (409 regra_referencia)."""
        return self.codigo in CODIGOS_REFERENCIA


# --- Sessão ---------------------------------------------------------------

class ContaGoogleAdsSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    login_customer_id: str | None


class EuSaida(BaseModel):
    """Usuário logado. Nunca inclui o refresh token, nem cifrado."""

    id: int
    nome: str | None
    email: str
    google_conectado: bool
    conta_google_ads: ContaGoogleAdsSaida | None


# --- Campanhas e métricas -------------------------------------------------

class CampanhaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    google_campaign_id: int
    nome: str
    status: str
    orcamento_micros: int | None
    sincronizada_em: datetime | None


class MetricaEntrada(BaseModel):
    data: date
    impressoes: int | None = None
    cliques: int | None = None
    custo: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    conversoes: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)

    def para_registro(self) -> RegistroMetricas:
        return RegistroMetricas(self.impressoes, self.cliques, self.custo, self.conversoes)

    @model_validator(mode="after")
    def validar(self) -> MetricaEntrada:
        erros = validar_registro(self.para_registro())
        if erros:
            raise ValueError("; ".join(erros))
        return self


class LoteMetricasEntrada(BaseModel):
    lote: str | None = Field(default=None, max_length=100)
    registros: list[MetricaEntrada] = Field(min_length=1, max_length=10_000)

    @field_validator("registros")
    @classmethod
    def sem_datas_repetidas(cls, registros: list[MetricaEntrada]) -> list[MetricaEntrada]:
        datas = [r.data for r in registros]
        if len(datas) != len(set(datas)):
            raise ValueError("o lote tem datas repetidas")
        return registros


class IngestaoSaida(BaseModel):
    campanha_id: int
    lote: str | None
    inseridos: int


class SincronizacaoSaida(BaseModel):
    campanhas_sincronizadas: int


class MetricaSaida(BaseModel):
    data: date
    impressoes: int | None
    cliques: int | None
    custo: Decimal | None
    conversoes: Decimal | None
    ctr: Decimal | None
    cpc: Decimal | None
    origem: str
    lote: str | None


# --- Avaliações e alertas -------------------------------------------------

class AvaliacaoEntrada(BaseModel):
    campanha_id: int | None = None
    inicio: date | None = None
    fim: date | None = None
    incluir_pausadas: bool = False

    @model_validator(mode="after")
    def periodo_valido(self) -> AvaliacaoEntrada:
        if self.inicio and self.fim and self.inicio > self.fim:
            raise ValueError("inicio deve ser anterior ou igual a fim")
        return self


class AvaliacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    iniciada_em: datetime
    concluida_em: datetime | None
    registros_avaliados: int
    registros_rejeitados: int
    alertas_gerados: int
    alertas_ja_existentes: int
    duracao_motor_ms: Decimal | None
    # Parâmetros da execução; null = não registrado (avaliações anteriores à migração 0003)
    incluir_pausadas: bool | None
    campanha_id: int | None
    inicio: date | None
    fim: date | None


# --- Resumo (visão geral) -------------------------------------------------

class ResumoCampanhas(BaseModel):
    total: int
    por_status: dict[str, int]


class ResumoRegras(BaseModel):
    total: int
    ativas: int


class ResumoMetricas(BaseModel):
    registros: int
    inicio: date | None
    fim: date | None
    por_origem: dict[str, int]


class ResumoAlertasRegra(BaseModel):
    regra_id: int
    codigo: str
    nome: str
    ativa: bool
    total: int


class ResumoAlertasDia(BaseModel):
    data: date
    por_regra: dict[str, int]


class ResumoAlertas(BaseModel):
    total: int
    # Avaliações distintas que geraram os alertas do período (não o total de execuções)
    avaliacoes: int
    por_regra: list[ResumoAlertasRegra]
    por_dia: list[ResumoAlertasDia]


class ResumoSaida(BaseModel):
    campanhas: ResumoCampanhas
    regras: ResumoRegras
    metricas: ResumoMetricas
    alertas: ResumoAlertas
    ultima_avaliacao: AvaliacaoSaida | None


class AlertaSaida(BaseModel):
    id: int
    criado_em: datetime
    avaliacao_id: int
    data: date
    origem: str
    campanha_id: int
    campanha_nome: str
    regra_id: int
    regra_codigo: str
    regra_nome: str
    valores_medidos: dict[str, str | None]
    condicoes: list[dict]
