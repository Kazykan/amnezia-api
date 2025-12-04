from ast import parse
import os
from fastapi import APIRouter, Depends, HTTPException

from services.add_client import add_client
from deps.auth import get_current_user
from services.utils import parse_wg_show
from services.docker import exec_in_container

router = APIRouter()


@router.get("/clients")
def list_clients(user=Depends(get_current_user)):
    """
    Получить список клиентов из AmneziaWG
    """
    raw = exec_in_container("amnezia-awg", "wg show")
    result = parse_wg_show(raw)
    return {"status": "ok", "output": result}


@router.post("/add_client")
def add_client_route(
    client_name: str,
    user=Depends(get_current_user),
):
    """
    Добавить клиента в AmneziaWG
    """
    try:
        endpoint = os.getenv("ENDPOINT")
        wg_config_file = os.getenv("WG_CONFIG_FILE")
        docker_container = os.getenv("DOCKER_CONTAINER")

        if not endpoint or not wg_config_file or not docker_container:
            raise HTTPException(
                status_code=500, detail="Не заданы переменные окружения"
            )

        client_conf = add_client(
            client_name=client_name,
            endpoint=endpoint,
            wg_config_file=wg_config_file,
            docker_container=docker_container,
        )

        return {"status": "ok", "client_conf": client_conf}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
