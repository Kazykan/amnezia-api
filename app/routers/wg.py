import subprocess
from services.docker_utils import get_docker_base_cmd
from services.awg_utils import remove_client
from services.firewall_utils import block_ip, unblock_ip
from services.stats.stats import get_peer_stats, get_wireguard_stats
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from services.add_client import add_client
from deps.auth import get_current_user
from core.config import BlockClientRequest, BlockIPRequest, settings

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
            f"{get_docker_base_cmd(settings.DOCKER_CONTAINER)} wg show",
            shell=True,
            capture_output=True,
            text=True,
            check=True,
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
            container=docker_container,
        )

        return {"status": "ok", "client_conf": client_conf}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/block_ip")
def block_ip_route(request: BlockIPRequest, user=Depends(get_current_user)):
    """
    Блокирует клиента по внутреннему IP.
    """
    try:
        block_ip(request.ip)
        return {"status": "ok", "message": f"IP {request.ip} заблокирован"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unblock_ip")
def unblock_ip_route(request: BlockIPRequest, user=Depends(get_current_user)):
    """
    Разблокирует клиента по внутреннему IP.
    """
    try:
        unblock_ip(request.ip)
        return {"status": "ok", "message": f"IP {request.ip} разблокирован"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remove_client")
def remove_client_route(
    request: BlockClientRequest,
    user=Depends(get_current_user),
):
    """
    Полностью удаляет клиента из AWG:
    - удаляет блок [Peer]
    - удаляет запись из clientsTable
    - снимает блокировку IP (если была)
    """
    try:
        wg_config_file = settings.WG_CONFIG_FILE
        docker_container = settings.DOCKER_CONTAINER

        if not wg_config_file or not docker_container:
            raise HTTPException(
                status_code=500, detail="Не заданы переменные окружения"
            )

        remove_client(
            client_name=request.ip,  # или request.client_name — зависит от твоей модели
            wg_config_file=wg_config_file,
            container=docker_container,
        )

        return {
            "status": "ok",
            "message": f"Client '{request.ip}' removed successfully",
        }

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
            container=docker_container,
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
