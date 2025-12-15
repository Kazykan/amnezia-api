import subprocess
from urllib.parse import unquote
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from services.update_psk import update_clients_psk
from services.add_client import add_client
from deps.auth import get_current_user
from services.utils import parse_wg_show
from core.config import settings

router = APIRouter()


class ClientRequest(BaseModel):
    client_name: str



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
    request: ClientRequest,
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
        
        update_clients_psk(wg_config_file, docker_container, json_input=[{"client_name": request.client_name}])
        return {"status": "ok", "message": f"PresharedKey for client '{request.client_name}' updated successfully."}
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
