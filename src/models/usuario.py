from typing import Optional
from enum import Enum
from sqlmodel import Field
from .base import SyncModel

class UserRole(str, Enum):
    """
    Definição hierárquica de papéis conforme especificação.
    """
    COORD_GERAL = "CG"       # Acesso total [cite: 11]
    COORD_EQUIPE = "CE"      # Acesso à equipe + dados básicos globais [cite: 12]
    SERVO = "SERVO"          # Acesso restrito à própria alocação [cite: 14]
    SAUDE = "SAUDE"          # Permissão especial para dados sensíveis [cite: 17]

class User(SyncModel, table=True):
    __tablename__ = "usuarios"

    # Credenciais
    email: str = Field(index=True, unique=True)
    password_hash: str  # Nunca armazenar senha em texto plano!
    
    # Identificação
    full_name: str
    
    # RBAC e Escopo
    role: UserRole = Field(default=UserRole.SERVO)
    
    # Vinculação de Escopo: Se for CE ou Servo, define qual equipe ele vê.
    # Se for NULL e role=CG, vê tudo.
    team_id: Optional[str] = Field(default=None)
    
    # Link opcional com a tabela de servos (se o usuário for um servo operando o app)
    servo_profile_id: Optional[str] = Field(default=None)

    class Config:
        use_enum_values = True