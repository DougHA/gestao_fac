from typing import Type, List, TypeVar, Generic
from sqlmodel import Session, select, create_engine, text
from src.models.base import SyncModel
from src.data.db_context import get_db_path

T = TypeVar("T", bound=SyncModel)

class SyncRepository(Generic[T]):
    """
    Classe base para repositórios que precisam de sincronização.
    Implementa a lógica padrão de Dirty Checking, Upsert Seguro e Soft Delete.
    """
    def __init__(self, model_type: Type[T]):
        self.model_type = model_type
        self.table_name = model_type.__tablename__
        
        self.db_path = get_db_path()
        self.engine = create_engine(
            f"sqlite:///{self.db_path}", 
            connect_args={"check_same_thread": False}
        )
        # Garante que a tabela exista
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(self.engine)
        self._ensure_trigger()

    def _ensure_trigger(self):
        """Cria o trigger de updated_at dinamicamente para a tabela do modelo"""
        trigger_name = f"trg_update_{self.table_name}_timestamp"
        sql = f"""
        CREATE TRIGGER IF NOT EXISTS {trigger_name}
        AFTER UPDATE ON {self.table_name}
        FOR EACH ROW
        BEGIN
            UPDATE {self.table_name}
            SET updated_at = STRFTIME('%Y-%m-%dT%H:%M:%f', 'NOW'),
                sync_status = 1
            WHERE id = OLD.id;
        END;
        """
        with self.engine.connect() as conn:
            conn.exec_driver_sql(sql)
            conn.commit()

    def get_dirty_records(self) -> List[T]:
        """Retorna registros pendentes de envio (sync_status=1)"""
        with Session(self.engine) as session:
            statement = select(self.model_type).where(self.model_type.sync_status == 1)
            return session.exec(statement).all()

    def mark_as_synced(self, ids: List[str]):
        """Marca registros como sincronizados (sync_status=0)"""
        if not ids: return
        placeholders = ', '.join(['?'] * len(ids))
        sql = f"UPDATE {self.table_name} SET sync_status = 0 WHERE id IN ({placeholders})"
        with self.engine.connect() as conn:
            conn.exec_driver_sql(sql, tuple(ids))
            conn.commit()

    def upsert_from_remote(self, data_list: List[dict]):
        """
        Insere ou atualiza dados vindos do servidor sem ativar o trigger de sync.
        Genericamente constrói a query baseada nos campos do modelo.
        """
        if not data_list: return

        keys = list(data_list[0].keys())
        if "sync_status" not in keys: keys.append("sync_status")
        
        columns = ", ".join(keys)
        placeholders = ", ".join([f":{k}" for k in keys])
        
        update_set = ", ".join([
            f"{k}=excluded.{k}" 
            for k in keys 
            if k not in ["id"]
        ])
        
        if "sync_status=excluded.sync_status" not in update_set:
            update_set += ", sync_status=0"

        sql = f"""
        INSERT INTO {self.table_name} ({columns})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET
            {update_set};
        """
        
        with self.engine.connect() as conn:
            for item in data_list:
                item["sync_status"] = 0
            
            conn.execute(text(sql), data_list)
            conn.commit()
            
    # --- MÉTODOS CRUD ---

    def save(self, entity: T) -> T:
        with Session(self.engine) as session:
            # CORREÇÃO: Usamos 'merge' em vez de 'add'.
            # O merge verifica se o ID existe:
            # - Se existir: Atualiza (UPDATE)
            # - Se não existir: Cria (INSERT)
            merged_entity = session.merge(entity)
            session.commit()
            session.refresh(merged_entity)
            return merged_entity
            
    def get_by_id(self, entity_id: str) -> T:
        with Session(self.engine) as session:
            return session.get(self.model_type, entity_id)
            
    def list_all(self) -> List[T]:
        with Session(self.engine) as session:
            return session.exec(select(self.model_type).where(self.model_type.is_deleted == False)).all()

    def soft_delete(self, entity_id: str) -> bool:
        """Marca o registro como deletado (is_deleted=True)"""
        with Session(self.engine) as session:
            entity = session.get(self.model_type, entity_id)
            if not entity:
                return False
            
            entity.is_deleted = True
            session.add(entity)
            session.commit()
            return True