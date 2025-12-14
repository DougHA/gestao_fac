import sqlite3
from typing import List, Optional
from sqlmodel import Session, select, create_engine, text, or_
from datetime import datetime, timezone

from src.models.campista import Camper, CamperStatus
from src.data.db_context import get_db_path 

class CamperRepository:
    def __init__(self):
        self.db_path = get_db_path()
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self._initialize_tables_and_triggers()

    def _initialize_tables_and_triggers(self):
        # ... (Mantém igual ao anterior) ...
        # Se quiser garantir, coloque o código de init aqui, mas focaremos na correção do método abaixo
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(self.engine)
        
        trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS trg_update_campista_timestamp
        AFTER UPDATE ON campistas
        FOR EACH ROW
        BEGIN
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
        with Session(self.engine) as session:
            session.add(camper)
            session.commit()
            session.refresh(camper)
            return camper

    def get_by_id(self, camper_id: str) -> Optional[Camper]:
        with Session(self.engine) as session:
            statement = select(Camper).where(Camper.id == camper_id, Camper.is_deleted == False)
            return session.exec(statement).first()

    def search_campers(self, query_text: str = "") -> List[Camper]:
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
        with Session(self.engine) as session:
            camper = session.get(Camper, camper_id)
            if not camper:
                return False
            camper.is_deleted = True
            session.add(camper)
            session.commit()
            return True

    def upsert_from_remote(self, data: dict):
        # ... (Mantém igual ao anterior) ...
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
            sync_status=0;
        """
        with self.engine.connect() as conn:
            conn.execute(text(sql), data)
            conn.commit()

    def get_dirty_records(self) -> List[Camper]:
        with Session(self.engine) as session:
            statement = select(Camper).where(Camper.sync_status == 1)
            return session.exec(statement).all()

    # --- A CORREÇÃO ESTÁ AQUI ---
    def mark_as_synced(self, camper_ids: List[str]):
        if not camper_ids: return
        
        placeholders = ', '.join(['?'] * len(camper_ids))
        sql = f"UPDATE campistas SET sync_status = 0 WHERE id IN ({placeholders})"
        
        with self.engine.connect() as conn:
            # CORREÇÃO: Converter list para tuple
            conn.exec_driver_sql(sql, tuple(camper_ids))
            conn.commit()