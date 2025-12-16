from typing import List
from sqlmodel import Session, select
from src.models.team import Team
from src.data.sync_repository import SyncRepository

class TeamRepository(SyncRepository[Team]):
    def __init__(self):
        super().__init__(Team)

    def seed_initial_teams(self):
        """Cria equipes padrão se o banco estiver vazio (Facilitador do MVP)"""
        if not self.list_all():
            teams = [
                Team(name="Equipe Vermelha", color_hex="#D32F2F", description="Fogo"),
                Team(name="Equipe Azul", color_hex="#1976D2", description="Água"),
                Team(name="Equipe Amarela", color_hex="#FBC02D", description="Luz"),
                Team(name="Equipe Verde", color_hex="#388E3C", description="Terra"),
                Team(name="Sem Equipe", color_hex="#9E9E9E", description="Triagem"),
            ]
            for t in teams:
                self.save(t)
            print("--- SEED: Equipes Padrão Criadas ---")