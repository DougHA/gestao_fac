from typing import Optional
from datetime import date
# Importação do String do SQLAlchemy para forçar o tipo no banco
from sqlalchemy import String 
from sqlmodel import Field, SQLModel
from enum import Enum
from .base import SyncModel

class CamperStatus(str, Enum):
    INSCRITO = "inscrito"
    EM_ANALISE = "em_analise"
    APROVADO = "aprovado"
    LISTA_ESPERA = "lista_espera"
    EQUIPE_DEFINIDA = "equipe_definida"
    CHECK_IN = "check_in"
    ATIVO = "ativo"
    ENCERRADO = "encerrado"

class Camper(SyncModel, table=True):
    __tablename__ = "campistas"

    full_name: str = Field(index=True)
    nickname: Optional[str] = Field(default=None)
    gender: str
    birth_date: Optional[date] = None # Ajustado para Optional para evitar erros de validação vazia
    
    team_id: Optional[str] = Field(default=None, index=True)

    # CORREÇÃO: sa_type=String
    # Isso diz ao banco: "Salve como texto simples". 
    # O Pydantic no Python ainda garantirá que só entre valores válidos do Enum.
    status: CamperStatus = Field(
        default=CamperStatus.INSCRITO,
        sa_type=String
    )

    document_cpf: Optional[str] = Field(default=None)
    contact_phone: Optional[str] = Field(default=None)
    responsible_name: Optional[str] = Field(default=None)
    
    medical_allergies: Optional[str] = Field(default=None)
    medical_medications: Optional[str] = Field(default=None)
    medical_notes: Optional[str] = Field(default=None)

    class Config:
        use_enum_values = True