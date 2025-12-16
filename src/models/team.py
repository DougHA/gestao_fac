from sqlmodel import Field
from sqlalchemy import String
from .base import SyncModel

class Team(SyncModel, table=True):
    __tablename__ = "equipes"

    name: str = Field(index=True)
    color_hex: str = Field(default="#808080") # Ex: #FF0000 para Vermelho
    
    # Ex: "Lema: Força e Honra"
    description: str = Field(default="", sa_type=String)