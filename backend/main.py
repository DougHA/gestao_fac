from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Dict, Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from contextlib import asynccontextmanager
from datetime import datetime

# --- IMPORTAÇÃO DOS MODELOS ---
# Importe aqui todas as entidades que serão sincronizadas
from src.models.campista import Camper
from src.models.team import Team
from src.models.usuario import User

# --- IMPORTAÇÕES DO BACKEND ---
from backend.database import init_db, get_session

# --- MAPEAMENTO DE ROTAS ---
# Este dicionário conecta o "nome na URL" à "Classe do Modelo"
MODELS_MAP = {
    "campers": Camper,
    "teams": Team,
    # Futuro: "ocorrencias": Ocorrencia
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante que as tabelas (incluindo a nova 'equipes') sejam criadas
    await init_db()
    yield

app = FastAPI(title="Gestão FAC - Servidor Central", lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "status": "online", 
        "resources": list(MODELS_MAP.keys()),
        "time": datetime.utcnow().isoformat()
    }

# --- ENDPOINT GENÉRICO DE PUSH ---
@app.post("/sync/push/{resource_name}")
async def push_generic(
    resource_name: str,
    payload: List[Dict[str, Any]], 
    session: AsyncSession = Depends(get_session)
):
    """
    Recebe alterações de QUALQUER recurso definido em MODELS_MAP.
    Ex: POST /sync/push/teams -> Salva na tabela 'equipes'
    """
    # 1. Valida se o recurso existe
    if resource_name not in MODELS_MAP:
        raise HTTPException(status_code=404, detail=f"Recurso '{resource_name}' desconhecido.")
    
    ModelClass = MODELS_MAP[resource_name]
    processed_ids = []
    
    try:
        for item in payload:
            item_id = item.get("id")
            if not item_id: continue
            
            # --- Tratamento Genérico de Datas ---
            # Converte strings ISO8601 para datetime Python onde necessário
            for field in ["created_at", "updated_at", "birth_date"]:
                if field in item and item[field]:
                    if field == "birth_date":
                        # birth_date geralmente é 'date', não 'datetime'
                        try:
                            item[field] = datetime.fromisoformat(item[field]).date()
                        except ValueError:
                             item[field] = datetime.fromisoformat(item[field]) # Fallback
                    else:
                        item[field] = datetime.fromisoformat(item[field])

            # --- Lógica de Upsert (Inserir ou Atualizar) ---
            # Busca pelo ID
            existing_record = await session.get(ModelClass, item_id)
            
            if existing_record:
                # Atualiza campos existentes dinamicamente
                for key, value in item.items():
                    # Só atualiza se o campo existir no modelo e não for o ID
                    if hasattr(existing_record, key) and key != "id":
                        setattr(existing_record, key, value)
                session.add(existing_record)
            else:
                # Cria novo registro usando desempacotamento de dicionário
                new_record = ModelClass(**item)
                session.add(new_record)
            
            processed_ids.append(item_id)
        
        await session.commit()
        return {"processed_ids": processed_ids, "status": "success", "resource": resource_name}
        
    except Exception as e:
        await session.rollback()
        print(f"ERRO NO PUSH ({resource_name}): {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT GENÉRICO DE PULL ---
@app.get("/sync/pull/{resource_name}")
async def pull_generic(
    resource_name: str,
    since: str, 
    session: AsyncSession = Depends(get_session)
):
    """
    Retorna deltas de QUALQUER recurso definido em MODELS_MAP.
    Ex: GET /sync/pull/campers?since=...
    """
    if resource_name not in MODELS_MAP:
        raise HTTPException(status_code=404, detail=f"Recurso '{resource_name}' desconhecido.")
    
    ModelClass = MODELS_MAP[resource_name]
    
    try:
        # Parse da Data
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            since_dt = datetime(1970, 1, 1)

        # Query Genérica: Select * From [Tabela] Where updated_at > since
        statement = select(ModelClass).where(ModelClass.updated_at > since_dt)
        result = await session.exec(statement)
        changes = result.all()
        
        return {
            "resource": resource_name,
            "changes": [record.model_dump(mode='json') for record in changes],
            "current_server_time": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"ERRO NO PULL ({resource_name}): {e}")
        raise HTTPException(status_code=500, detail=str(e))