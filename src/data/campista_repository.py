from typing import List
from sqlmodel import Session, select, or_
from src.models.campista import Camper
# Importa a nova classe base
from src.data.sync_repository import SyncRepository

class CamperRepository(SyncRepository[Camper]):
    def __init__(self):
        # Inicializa a base passando o Tipo do modelo
        super().__init__(Camper)

    def search_campers(self, query_text: str = "") -> List[Camper]:
        """Busca específica de campistas (Nome, CPF, Apelido)"""
        with Session(self.engine) as session:
            statement = select(Camper).where(Camper.is_deleted == False)
            
            if query_text:
                search_pattern = f"%{query_text}%"
                statement = statement.where(
                    or_(
                        Camper.full_name.like(search_pattern),
                        Camper.nickname.like(search_pattern),
                        Camper.document_cpf.like(search_pattern)
                    )
                )
            
            statement = statement.order_by(Camper.full_name)
            return session.exec(statement).all()

    def soft_delete(self, camper_id: str) -> bool:
        """Override opcional ou uso direto"""
        with Session(self.engine) as session:
            camper = session.get(Camper, camper_id)
            if not camper: return False
            camper.is_deleted = True
            session.add(camper)
            session.commit()
            return True