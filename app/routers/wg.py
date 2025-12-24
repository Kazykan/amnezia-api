import subprocess
from services.stats.stats import get_peer_stats, get_wireguard_stats
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from services.update_psk import update_clients_psk
from services.add_client import add_client
from deps.auth import get_current_user
from core.config import settings

router = APIRouter()

class ClientRequest(BaseModel):
    client_name: str

class ReplacePsk(BaseModel):
    client_name: str
    new_preshared_key: str

class ReplacePskRequest(BaseModel):
    clients: list[ReplacePsk]


@router.get("/clients")
def list_clients(user=Depends(get_current_user)):
    """
    Получить список клиентов из AmneziaWG
    """
    try:
        result = subprocess.run(
            f"docker exec -i {settings.DOCKER_CONTAINER} wg show",
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return {"status": "ok", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "output": e.stderr}


@router.post("/add_client")
def add_client_route(
    request: ClientRequest,
    user=Depends(get_current_user),
):
    """
    Добавить клиента в AmneziaWG
    """
    try:
        endpoint = settings.ENDPOINT
        wg_config_file = settings.WG_CONFIG_FILE
        docker_container = settings.DOCKER_CONTAINER

        if not endpoint or not wg_config_file or not docker_container:
            raise HTTPException(
                status_code=500, detail="Не заданы переменные окружения"
            )

        client_conf = add_client(
            client_name=request.client_name,
            endpoint=endpoint,
            wg_config_file=wg_config_file,
            docker_container=docker_container,
        )

        return {"status": "ok", "client_conf": client_conf}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_clients_psk")
def update_clients_psk_route(
    request: ReplacePskRequest,
    user=Depends(get_current_user),
):
    """
    Обновить PresharedKey для клиента в AmneziaWG
    """
    try:
        endpoint = settings.ENDPOINT
        wg_config_file = settings.WG_CONFIG_FILE
        docker_container = settings.DOCKER_CONTAINER

        if not endpoint or not wg_config_file or not docker_container:
            raise HTTPException(
                status_code=500, detail="Не заданы переменные окружения"
            )
        if not request.clients or len(request.clients) == 0:
            raise HTTPException(
                status_code=400, detail="Список клиентов пуст"
            )
        
        # Преобразуем список моделей в список словарей
        client_dicts = [client.dict() for client in request.clients]

        update_clients_psk(wg_config_file, docker_container, json_input=client_dicts)
        return {"status": "ok", "message": f"PresharedKey for client '{request.clients}' updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/replace_configs")
def replace_configs(
    request: ClientRequest,
    user=Depends(get_current_user),
):
    """
    Добавить клиента в AmneziaWG
    """
    try:

        endpoint = settings.ENDPOINT
        wg_config_file = settings.WG_CONFIG_FILE
        docker_container = settings.DOCKER_CONTAINER

        if not endpoint or not wg_config_file or not docker_container:
            raise HTTPException(
                status_code=500, detail="Не заданы переменные окружения"
            )

        client_conf = add_client(
            client_name=request.client_name,
            endpoint=endpoint,
            wg_config_file=wg_config_file,
            docker_container=docker_container,
        )

        return {"status": "ok", "client_conf": client_conf}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{peer}")
def stat_one_peer(peer: str):
    return get_peer_stats(peer)


@router.get("/stats")
def stats():
    return get_wireguard_stats()