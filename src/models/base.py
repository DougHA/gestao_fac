import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel

# Função auxiliar para timestamps UTC
def utc_now():
    return datetime.now(timezone.utc)

class SyncModel(SQLModel):
    """
    Classe Base para todas as entidades sincronizáveis.
    Implementa UUID, Soft Delete e Metadados de Auditoria.
    """
    # Identificador UUID v4 (NUNCA usar Autoincrement) [cite: 31]
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Metadados de Auditoria
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    
    # Tombstone para Soft Delete [cite: 39]
    is_deleted: bool = Field(default=False)
    
    # Status de Sincronização [cite: 38]
    # 0: Synced, 1: Pending Push, 2: Sync Failed
    sync_status: int = Field(default=1) 

    class Config:
        # Garante validação estrita de tipos
        validate_assignment = True