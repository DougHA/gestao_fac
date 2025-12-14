from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Dict, Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from contextlib import asynccontextmanager

# Importações do nosso código compartilhado
from src.models.campista import Camper
from src.models.usuario import User

# Importações do backend
from backend.database import init_db, get_session

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Na inicialização: cria tabelas
    await init_db()
    yield
    # No desligamento: (opcional, fechar conexões)

app = FastAPI(title="Gestão FAC - Servidor Central", lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "online", "message": "Servidor de Sincronização Ativo"}

# --- ENDPOINTS DE SINCRONIZAÇÃO (MVP) ---

@app.post("/sync/push")
async def push_changes(
    payload: List[Dict[str, Any]], 
    session: AsyncSession = Depends(get_session)
):
    """
    Recebe alterações do cliente (Push).
    Aplica estratégia 'Last Write Wins'.
    """
    processed_ids = []
    
    try:
        for item in payload:
            # Converte o dict recebido para o modelo Camper
            # O ID vem do cliente (UUID gerado offline)
            item_id = item.get("id")
            if not item_id:
                continue
                
            # Verifica se já existe no servidor
            statement = select(Camper).where(Camper.id == item_id)
            result = await session.exec(statement)
            existing_record = result.first()
            
            if existing_record:
                # LÓGICA DE CONFLITO:
                # Só atualiza se o updated_at do payload for mais novo que o do banco
                # (Para simplificar MVP, assumimos que server aceita tudo por enquanto,
                #  mas idealmente compararíamos timestamps ISO aqui)
                for key, value in item.items():
                    setattr(existing_record, key, value)
                session.add(existing_record)
            else:
                # Novo registro
                new_record = Camper(**item)
                session.add(new_record)
            
            processed_ids.append(item_id)
        
        await session.commit()
        return {"processed_ids": processed_ids, "status": "success"}
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Erro no Sync: {str(e)}")

@app.get("/sync/pull")
async def pull_changes(
    since: str, 
    session: AsyncSession = Depends(get_session)
):
    """
    Envia para o cliente tudo que mudou desde 'since'.
    """
    from datetime import datetime
    
    # Busca registros onde updated_at > since
    # Nota: Comparação de string ISO8601 funciona no SQLite/Postgres
    statement = select(Camper).where(Camper.updated_at > since)
    result = await session.exec(statement)
    changes = result.all()
    
    return {
        "changes": [record.model_dump(mode='json') for record in changes],
        "current_server_time": datetime.utcnow().isoformat()
    }