from typing import Optional
from datetime import date
from sqlmodel import Field, SQLModel
from enum import Enum
from .base import SyncModel  # Importando nossa classe base criada anteriormente

class CamperStatus(str, Enum):
    # Pipeline de Status 
    INSCRITO = "inscrito"
    EM_ANALISE = "em_analise"
    APROVADO = "aprovado"
    LISTA_ESPERA = "lista_espera"
    EQUIPE_DEFINIDA = "equipe_definida"
    CHECK_IN = "check_in"
    ATIVO = "ativo"
    ENCERRADO = "encerrado"

class Camper(SyncModel, table=True):
    """
    Representa um Campista no sistema.
    Herda ID (UUID), created_at, updated_at, is_deleted e sync_status de SyncModel.
    """
    __tablename__ = "campistas"

    # --- Dados Básicos (Visíveis globalmente - Cenário B [cite: 16]) ---
    full_name: str = Field(index=True)
    nickname: Optional[str] = Field(default=None)
    gender: str  # 'M' ou 'F' para alocação de dormitórios
    birth_date: date
    
    # Vinculação de Equipe (Pode ser nulo inicialmente)
    team_id: Optional[str] = Field(default=None, index=True)

    # Status do Pipeline
    status: CamperStatus = Field(default=CamperStatus.INSCRITO)

    # --- Dados Sensíveis (Acesso restrito a Médicos/Admin [cite: 17, 55]) ---
    # Em um sistema maior, estes ficariam em tabela separada (1:1), 
    # mas para SQLite Offline mantemos junto para performance de leitura.
    document_cpf: Optional[str] = Field(default=None)
    contact_phone: Optional[str] = Field(default=None)
    responsible_name: Optional[str] = Field(default=None)
    
    # Saúde [cite: 55]
    medical_allergies: Optional[str] = Field(default=None)
    medical_medications: Optional[str] = Field(default=None)
    medical_notes: Optional[str] = Field(default=None)

    class Config:
        # Permite uso de Enums no SQLite
        use_enum_values = True