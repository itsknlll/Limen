"""Modelo relacional do Limen (SQLAlchemy 2.0).

Decisões de modelagem:
- CTR e CPC NÃO são colunas: são derivados de outras colunas e ficam na view
  vw_metrica_diaria. Guardar valores derivados quebraria a normalização (3FN)
  e abriria espaço para inconsistência.
- As restrições de validade (valores não negativos, cliques <= impressões)
  existem também no banco, como CHECK. O backend valida antes, mas o banco é a
  última linha de defesa: nenhum caminho de escrita consegue gravar um
  registro inválido.
- Alerta tem UNIQUE (regra, registro de métricas). Reavaliar o mesmo registro
  não duplica alerta, e a garantia é do banco, não só do código (caso IN-11).
- O alerta guarda uma cópia das condições e dos valores medidos no momento da
  avaliação. Se a regra mudar depois, o histórico continua explicável.
- Valores monetários e limiares usam NUMERIC (decimal exato), coerente com o
  uso de Decimal no motor.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .motor import Metrica, Operador

ORIGENS_METRICA = ("sintetica", "google_ads")
STATUS_CAMPANHA = ("ENABLED", "PAUSED", "REMOVED", "UNKNOWN")
METRICAS = tuple(m.value for m in Metrica)
OPERADORES = tuple(o.value for o in Operador)


def _em(coluna: str, valores: tuple[str, ...]) -> str:
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (UniqueConstraint("email", name="uq_usuario_email"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    nome: Mapped[str | None] = mapped_column(String(200))
    # Cifrado com Fernet (CHAVE_CIFRAGEM). Fonte única: ContaGoogleAds lê por FK.
    refresh_token_cifrado: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContaGoogleAds(Base):
    __tablename__ = "conta_google_ads"
    __table_args__ = (
        UniqueConstraint("usuario_id", "customer_id", name="uq_conta_usuario_customer"),
        CheckConstraint("customer_id ~ '^[0-9]{10}$'", name="ck_conta_customer_id_formato"),
        CheckConstraint(
            "login_customer_id IS NULL OR login_customer_id ~ '^[0-9]{10}$'",
            name="ck_conta_login_customer_id_formato",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE", name="fk_conta_usuario")
    )
    customer_id: Mapped[str] = mapped_column(String(10))
    login_customer_id: Mapped[str | None] = mapped_column(String(10))
    nome: Mapped[str | None] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campanhas: Mapped[list[Campanha]] = relationship(back_populates="conta")


class Campanha(Base):
    __tablename__ = "campanha"
    __table_args__ = (
        UniqueConstraint("conta_id", "google_campaign_id", name="uq_campanha_conta_google_id"),
        CheckConstraint(_em("status", STATUS_CAMPANHA), name="ck_campanha_status"),
        CheckConstraint(
            "orcamento_micros IS NULL OR orcamento_micros >= 0", name="ck_campanha_orcamento"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conta_id: Mapped[int] = mapped_column(
        ForeignKey("conta_google_ads.id", ondelete="CASCADE", name="fk_campanha_conta")
    )
    google_campaign_id: Mapped[int] = mapped_column(BigInteger)
    nome: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20))
    orcamento_micros: Mapped[int | None] = mapped_column(BigInteger)
    sincronizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conta: Mapped[ContaGoogleAds] = relationship(back_populates="campanhas")
    metricas: Mapped[list[MetricaDiaria]] = relationship(back_populates="campanha")


class MetricaDiaria(Base):
    """Métricas de uma campanha em um dia: a unidade de avaliação do motor."""

    __tablename__ = "metrica_diaria"
    __table_args__ = (
        UniqueConstraint("campanha_id", "data", name="uq_metrica_campanha_data"),
        CheckConstraint("impressoes IS NULL OR impressoes >= 0", name="ck_metrica_impressoes"),
        CheckConstraint("cliques IS NULL OR cliques >= 0", name="ck_metrica_cliques"),
        CheckConstraint("custo IS NULL OR custo >= 0", name="ck_metrica_custo"),
        CheckConstraint("conversoes IS NULL OR conversoes >= 0", name="ck_metrica_conversoes"),
        CheckConstraint(
            "impressoes IS NULL OR cliques IS NULL OR cliques <= impressoes",
            name="ck_metrica_cliques_ate_impressoes",
        ),
        CheckConstraint(_em("origem", ORIGENS_METRICA), name="ck_metrica_origem"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campanha_id: Mapped[int] = mapped_column(
        ForeignKey("campanha.id", ondelete="CASCADE", name="fk_metrica_campanha")
    )
    data: Mapped[date] = mapped_column(Date)
    impressoes: Mapped[int | None] = mapped_column(BigInteger)
    cliques: Mapped[int | None] = mapped_column(BigInteger)
    custo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    conversoes: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    # Identifica a origem do dado (exigência da metodologia: sintético x real)
    origem: Mapped[str] = mapped_column(String(20))
    # Conjunto de dados sintéticos de onde o registro veio (ex.: "tabela-v1.0")
    lote: Mapped[str | None] = mapped_column(String(100))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campanha: Mapped[Campanha] = relationship(back_populates="metricas")


class Regra(Base):
    __tablename__ = "regra"
    __table_args__ = (UniqueConstraint("usuario_id", "codigo", name="uq_regra_usuario_codigo"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE", name="fk_regra_usuario")
    )
    codigo: Mapped[str] = mapped_column(String(20))
    nome: Mapped[str] = mapped_column(String(120))
    # Regras não são apagadas: são desativadas, para preservar o histórico de alertas.
    ativa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    condicoes: Mapped[list[Condicao]] = relationship(
        back_populates="regra", order_by="Condicao.ordem", cascade="all, delete-orphan"
    )


class Condicao(Base):
    __tablename__ = "condicao"
    __table_args__ = (
        UniqueConstraint("regra_id", "ordem", name="uq_condicao_regra_ordem"),
        CheckConstraint(_em("metrica", METRICAS), name="ck_condicao_metrica"),
        CheckConstraint(_em("operador", OPERADORES), name="ck_condicao_operador"),
        CheckConstraint("limiar >= 0", name="ck_condicao_limiar"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    regra_id: Mapped[int] = mapped_column(
        ForeignKey("regra.id", ondelete="CASCADE", name="fk_condicao_regra")
    )
    ordem: Mapped[int] = mapped_column(SmallInteger)
    metrica: Mapped[str] = mapped_column(String(20))
    operador: Mapped[str] = mapped_column(String(2))
    limiar: Mapped[Decimal] = mapped_column(Numeric(18, 6))

    regra: Mapped[Regra] = relationship(back_populates="condicoes")


class Avaliacao(Base):
    """Uma execução do motor. Guarda contagens e tempo para a avaliação de desempenho."""

    __tablename__ = "avaliacao"
    __table_args__ = (
        CheckConstraint(
            "inicio IS NULL OR fim IS NULL OR inicio <= fim", name="ck_avaliacao_periodo"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE", name="fk_avaliacao_usuario")
    )
    # Parâmetros da execução (migração 0003). NULL = não registrado (avaliações
    # anteriores à 0003), e não "false": ausente ≠ zero.
    incluir_pausadas: Mapped[bool | None] = mapped_column(Boolean)
    campanha_id: Mapped[int | None] = mapped_column(
        ForeignKey("campanha.id", ondelete="SET NULL", name="fk_avaliacao_campanha")
    )
    inicio: Mapped[date | None] = mapped_column(Date)
    fim: Mapped[date | None] = mapped_column(Date)
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registros_avaliados: Mapped[int] = mapped_column(Integer, server_default="0")
    registros_rejeitados: Mapped[int] = mapped_column(Integer, server_default="0")
    alertas_gerados: Mapped[int] = mapped_column(Integer, server_default="0")
    alertas_ja_existentes: Mapped[int] = mapped_column(Integer, server_default="0")
    duracao_motor_ms: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))


class Alerta(Base):
    __tablename__ = "alerta"
    __table_args__ = (
        UniqueConstraint("regra_id", "metrica_diaria_id", name="uq_alerta_regra_metrica"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    avaliacao_id: Mapped[int] = mapped_column(
        ForeignKey("avaliacao.id", ondelete="CASCADE", name="fk_alerta_avaliacao")
    )
    regra_id: Mapped[int] = mapped_column(
        ForeignKey("regra.id", ondelete="RESTRICT", name="fk_alerta_regra")
    )
    metrica_diaria_id: Mapped[int] = mapped_column(
        ForeignKey("metrica_diaria.id", ondelete="CASCADE", name="fk_alerta_metrica")
    )
    # Cópias do momento da avaliação (valores como texto, para não perder precisão no JSON)
    valores_medidos: Mapped[dict] = mapped_column(JSONB)
    condicoes: Mapped[list] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# View só de leitura (criada na migração 0001). Fica num MetaData separado para
# o Alembic não tentar criá-la como tabela.
vw_metrica_diaria = Table(
    "vw_metrica_diaria",
    MetaData(),
    Column("id", BigInteger, primary_key=True),
    Column("campanha_id", BigInteger),
    Column("data", Date),
    Column("impressoes", BigInteger),
    Column("cliques", BigInteger),
    Column("custo", Numeric),
    Column("conversoes", Numeric),
    Column("origem", String),
    Column("lote", String),
    Column("criado_em", DateTime(timezone=True)),
    Column("ctr", Numeric),
    Column("cpc", Numeric),
)
