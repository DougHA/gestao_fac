import sqlite3
from src.data.db_context import get_db_path

class KVStore:
    """Gerencia persistência de metadados simples (Chave-Valor)"""
    
    def __init__(self):
        self.db_path = get_db_path()
        self._init_table()

    def _init_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

    def get_last_sync(self) -> str:
        """Retorna timestamp ISO8601 ou data muito antiga se nunca sincronizou"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM sys_meta WHERE key = 'last_sync_campers'")
            row = cursor.fetchone()
            # Retorna data epoch se não houver registro (baixa tudo)
            return row[0] if row else "1970-01-01T00:00:00.000000"

    def set_last_sync(self, timestamp: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sys_meta (key, value) VALUES ('last_sync_campers', ?)",
                (timestamp,)
            )