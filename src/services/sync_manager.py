import httpx
import logging
from typing import Dict, Any, List

from src.data.kv_store import KVStore
# Importe seus repositórios aqui
from src.data.campista_repository import CamperRepository
from src.data.team_repository import TeamRepository 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SyncManager")

API_BASE_URL = "http://localhost:8000"
TIMEOUT_SECONDS = 10

class SyncManager:
    def __init__(self):
        self.kv_store = KVStore()
        self.client = httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT_SECONDS)
        
        # LISTA DE REPOSITÓRIOS PARA SYNC
        # A ordem importa se houver chaves estrangeiras (Pai antes de Filho)
        # Ex: Equipes antes de Campistas (pois campista tem team_id)
        self.repositories = {
            "teams": TeamRepository(),
            "campers": CamperRepository(),
        }

    def perform_sync(self) -> Dict[str, Any]:
        report = {"pushed": 0, "pulled": 0, "errors": [], "status": "success"}

        try:
            # 1. PUSH (Itera sobre todos os repositórios)
            for resource_name, repo in self.repositories.items():
                dirty = repo.get_dirty_records()
                if dirty:
                    count = self._push_resource(resource_name, repo, dirty)
                    report["pushed"] += count

            # 2. PULL GLOBAL
            # O servidor deve ser inteligente para retornar um dict com chaves {"campers": [], "teams": []}
            # Ou fazemos chamadas separadas. Para MVP, vamos fazer chamadas separadas.
            for resource_name, repo in self.repositories.items():
                last_sync = self.kv_store.get_last_sync() # Por enquanto global, ideal seria por recurso
                count = self._pull_resource(resource_name, repo, last_sync)
                report["pulled"] += count
            
            # Atualiza timestamp global se sucesso
            from datetime import datetime
            self.kv_store.set_last_sync(datetime.utcnow().isoformat())

        except httpx.ConnectError:
            report["status"] = "offline"
        except Exception as e:
            logger.error(f"Sync Error: {e}")
            report["status"] = "error"
            report["errors"].append(str(e))

        return report

    def _push_resource(self, resource_name: str, repo, records: List) -> int:
        payload = [r.model_dump(mode='json') for r in records]
        # Endpoint ex: /sync/push/campers
        response = self.client.post(f"/sync/push/{resource_name}", json=payload)
        response.raise_for_status()
        
        result = response.json()
        accepted_ids = result.get("processed_ids", [])
        if accepted_ids:
            repo.mark_as_synced(accepted_ids)
        return len(accepted_ids)

    def _pull_resource(self, resource_name: str, repo, last_sync: str) -> int:
        response = self.client.get(f"/sync/pull/{resource_name}", params={"since": last_sync})
        response.raise_for_status()
        
        data = response.json()
        server_records = data.get("changes", [])
        
        if server_records:
            repo.upsert_from_remote(server_records)
            
        return len(server_records)