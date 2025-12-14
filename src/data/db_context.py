import sqlite3
import os
import shutil
from pathlib import Path

DATABASE_NAME = "fac.db"

def get_db_path() -> str:
    """
    Define o caminho correto do banco de dados dependendo do OS.
    No Android, movemos de 'assets' para o armazenamento interno gravável.
    """
    # Verifica se estamos rodando em ambiente Android (via variável ou lógica de build)
    # Nota: Em produção Flet, isso pode exigir lógica específica do 'serious-python'
    if "ANDROID_ARGUMENT" in os.environ:
        storage_path = "/data/data/com.seuprojeto.fac/files" # Exemplo [cite: 91]
        target = os.path.join(storage_path, DATABASE_NAME)
        
        # Se não existe no local gravável, copia do bundle (assets)
        if not os.path.exists(target):
            # Lógica de cópia inicial (First run)
            pass 
        return target
    
    # Desenvolvimento Desktop
    return DATABASE_NAME

def create_connection() -> sqlite3.Connection:
    """
    Cria conexão com otimizações para alta concorrência e UI fluida.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    
    # --- CRÍTICO: Otimizações de Performance  ---
    conn.execute("PRAGMA journal_mode=WAL;") 
    conn.execute("PRAGMA synchronous=NORMAL;") 
    conn.execute("PRAGMA temp_store=MEMORY;")
    
    # Habilitar chaves estrangeiras
    conn.execute("PRAGMA foreign_keys=ON;")
    
    return conn