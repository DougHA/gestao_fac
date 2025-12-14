import sqlite3
from sqlmodel import or_
from typing import List, Optional
from sqlmodel import SQLModel, Session, select, create_engine
from datetime import datetime, timezone
from sqlmodel import text

from ..models.campista import Camper, CamperStatus
# Supondo que seu db_context esteja acessível
from .db_context import get_db_path 

class CamperRepository:
    def __init__(self):
        # Configuração do Engine SQLModel com conexão específica
        self.db_path = get_db_path()
        # check_same_thread=False é necessário para Flet/FastAPI + SQLite
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self._initialize_tables_and_triggers()

    def _initialize_tables_and_triggers(self):
        """
        Cria as tabelas e, CRUCIALMENTE, os triggers de auditoria.
        Isso garante que o Delta Sync nunca perca uma alteração.
        """
        # 1. Cria tabelas (se não existirem)
        SQLModel.metadata.create_all(self.engine)
        
        # 2. Injeta o Trigger de Auditoria 
        trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS trg_update_campista_timestamp
        AFTER UPDATE ON campistas
        FOR EACH ROW
        BEGIN
            -- Atualiza timestamp para AGORA
            -- Marca sync_status = 1 (Pendente de envio para servidor)
            UPDATE campistas
            SET updated_at = STRFTIME('%Y-%m-%dT%H:%M:%f', 'NOW'),
                sync_status = 1
            WHERE id = OLD.id;
        END;
        """
        
        with self.engine.connect() as conn:
            conn.exec_driver_sql(trigger_sql)
            conn.commit()

    def save(self, camper: Camper) -> Camper:
        """
        Cria ou Atualiza um campista.
        """
        with Session(self.engine) as session:
            # Se for novo, sync_status já nasce como 1 (Pending) via default do Model
            session.add(camper)
            session.commit()
            session.refresh(camper)
            return camper

    def get_by_id(self, camper_id: str) -> Optional[Camper]:
        with Session(self.engine) as session:
            # Filtra apenas os NÃO excluídos (Soft Delete check)
            statement = select(Camper).where(Camper.id == camper_id, Camper.is_deleted == False)
            return session.exec(statement).first()

    def list_active(self) -> List[Camper]:
        """Lista todos campistas ativos no sistema (não excluídos)."""
        with Session(self.engine) as session:
            # Ordenação padrão alfabética
            statement = select(Camper).where(Camper.is_deleted == False).order_by(Camper.full_name)
            return session.exec(statement).all()

    def soft_delete(self, camper_id: str) -> bool:
        """
        Realiza a exclusão lógica (Tombstone Pattern).
        Não remove a linha, apenas marca is_deleted=True.
        O Trigger cuidará de atualizar o updated_at e sync_status.
        """
        with Session(self.engine) as session:
            camper = session.get(Camper, camper_id)
            if not camper:
                return False
            
            camper.is_deleted = True
            # Nota: Não precisamos setar sync_status manualmente aqui 
            # porque o UPDATE disparará o Trigger trg_update_campista_timestamp!
            
            session.add(camper)
            session.commit()
            return True
    
    def search_campers(self, query_text: str = "") -> List[Camper]:
        """
        Busca campistas por nome, apelido ou CPF.
        Retorna todos se a query for vazia.
        Ignora registros marcados como excluídos (Soft Delete).
        """
        with Session(self.engine) as session:
            # Base da query: apenas não deletados
            statement = select(Camper).where(Camper.is_deleted == False)
            
            if query_text:
                # Normaliza para busca 'case insensitive' no SQLite
                # O % envolve o texto para buscar em qualquer parte da string
                search_pattern = f"%{query_text}%"
                
                statement = statement.where(
                    or_(
                        Camper.full_name.like(search_pattern),
                        Camper.nickname.like(search_pattern),
                        Camper.document_cpf.like(search_pattern)
                    )
                )
            
            # Ordena por nome para facilitar leitura
            statement = statement.order_by(Camper.full_name)
            
            return session.exec(statement).all()
        
    def upsert_from_remote(self, data: dict):
        """
        Insere ou Atualiza um registro vindo do servidor.
        IMPORTANTE: Força sync_status = 0 (Synced) para evitar loops.
        """
        sql = """
        INSERT INTO campistas (
            id, full_name, nickname, gender, birth_date, team_id, status,
            document_cpf, contact_phone, responsible_name,
            medical_allergies, medical_medications, medical_notes,
            created_at, updated_at, is_deleted, sync_status
        ) VALUES (
            :id, :full_name, :nickname, :gender, :birth_date, :team_id, :status,
            :document_cpf, :contact_phone, :responsible_name,
            :medical_allergies, :medical_medications, :medical_notes,
            :created_at, :updated_at, :is_deleted, 0
        )
        ON CONFLICT(id) DO UPDATE SET
            full_name=excluded.full_name,
            nickname=excluded.nickname,
            gender=excluded.gender,
            birth_date=excluded.birth_date,
            team_id=excluded.team_id,
            status=excluded.status,
            document_cpf=excluded.document_cpf,
            contact_phone=excluded.contact_phone,
            responsible_name=excluded.responsible_name,
            medical_allergies=excluded.medical_allergies,
            medical_medications=excluded.medical_medications,
            medical_notes=excluded.medical_notes,
            created_at=excluded.created_at,
            updated_at=excluded.updated_at,
            is_deleted=excluded.is_deleted,
            sync_status=0; -- Força status 'Sincronizado'
        """
        
        with self.engine.connect() as conn:
            conn.execute(text(sql), data)
            conn.commit()

    def get_dirty_records(self) -> List[Camper]:
        """Retorna registros pendentes de envio (sync_status=1)"""
        with Session(self.engine) as session:
            # Pega inclusive os deletados (is_deleted=True) se estiverem pendentes
            statement = select(Camper).where(Camper.sync_status == 1)
            return session.exec(statement).all()

    def mark_as_synced(self, camper_ids: List[str]):
        """Marca registros como sincronizados após sucesso no envio"""
        if not camper_ids: return
        
        # Precisamos fazer update raw para garantir performance e evitar triggers desnecessários
        # Formata a lista de IDs para SQL IN clause
        placeholders = ', '.join(['?'] * len(camper_ids))
        sql = f"UPDATE campistas SET sync_status = 0 WHERE id IN ({placeholders})"
        
        with self.engine.connect() as conn:
            conn.exec_driver_sql(sql, camper_ids)
            conn.commit()