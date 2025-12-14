import httpx
import logging
from typing import List, Dict, Any
from datetime import datetime

# Importações internas
from src.data.campista_repository import CamperRepository
from src.data.kv_store import KVStore
from src.models.campista import Camper

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SyncManager")

API_BASE_URL = "http://localhost:8000"  # Em prod: URL do servidor na nuvem
TIMEOUT_SECONDS = 10

class SyncManager:
    def __init__(self):
        self.repository = CamperRepository()
        self.kv_store = KVStore()
        self.client = httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT_SECONDS)

    def perform_sync(self) -> Dict[str, Any]:
        """
        Orquestrador Principal:
        1. Tenta PUSH (enviar locais).
        2. Tenta PULL (receber remotos).
        Retorna relatório de execução.
        """
        report = {"pushed": 0, "pulled": 0, "errors": [], "status": "success"}

        try:
            # --- FASE 1: PUSH (Envio) ---
            dirty_records = self.repository.get_dirty_records()
            if dirty_records:
                logger.info(f"Iniciando PUSH de {len(dirty_records)} registros...")
                pushed_count = self._push_changes(dirty_records)
                report["pushed"] = pushed_count

            # --- FASE 2: PULL (Recebimento) ---
            last_sync = self.kv_store.get_last_sync()
            logger.info(f"Iniciando PULL desde {last_sync}...")
            pulled_count = self._pull_changes(last_sync)
            report["pulled"] = pulled_count

        except httpx.ConnectError:
            msg = "Sem conexão com o servidor (Offline)."
            logger.warning(msg)
            report["status"] = "offline"
            report["errors"].append(msg)
            
        except Exception as e:
            msg = f"Erro crítico na sincronização: {str(e)}"
            logger.error(msg)
            report["status"] = "error"
            report["errors"].append(msg)

        return report

    def _push_changes(self, records: List[Camper]) -> int:
        """
        Envia lote de mudanças locais para o servidor.
        """
        # Serializa os modelos para dicts (JSON compatível)
        payload = [record.model_dump(mode='json') for record in records]
        
        response = self.client.post("/sync/push", json=payload)
        response.raise_for_status() # Lança erro se != 200 OK
        
        # O servidor deve retornar os IDs que foram aceitos
        # Ex: {"processed_ids": ["uuid1", "uuid2"], "conflicts": []}
        result = response.json()
        accepted_ids = result.get("processed_ids", [])
        
        # Marca como 'Synced' localmente para não enviar de novo
        if accepted_ids:
            self.repository.mark_as_synced(accepted_ids)
            
        return len(accepted_ids)

    def _pull_changes(self, last_sync: str) -> int:
        """
        Baixa deltas do servidor e aplica localmente.
        """
        response = self.client.get(f"/sync/pull", params={"since": last_sync})
        response.raise_for_status()
        
        data = response.json()
        server_records = data.get("changes", [])
        server_timestamp = data.get("current_server_time")
        
        count = 0
        for record_dict in server_records:
            # Aplica regra de integridade e tombstone
            self.repository.upsert_from_remote(record_dict)
            count += 1
            
        # Se tudo correu bem, atualiza o 'ponteiro' de tempo
        if server_timestamp:
            self.kv_store.set_last_sync(server_timestamp)
            
        return count