import os
import subprocess
import tempfile
from services.docker_utils import docker_copy_from, docker_copy_to, docker_exec, get_docker_base_cmd
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


class ConfigsUpdateRequest(BaseModel):
    wg_conf: str
    clients_table: str


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


@router.get("/configs")
def get_configs(user=Depends(get_current_user)):
    """
    Получает текущее содержимое wg0.conf и clientsTable из контейнера.
    """
    try:
        # Создаем временные файлы для копирования данных на хост
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False
        ) as tmp_wg, tempfile.NamedTemporaryFile(
            mode="w+", delete=False
        ) as tmp_clients:

            # Копируем из контейнера во временные файлы
            docker_copy_from(
                settings.DOCKER_CONTAINER, settings.WG_CONFIG_FILE, tmp_wg.name
            )
            docker_copy_from(
                settings.DOCKER_CONTAINER, settings.CLIENTS_TABLE_PATH, tmp_clients.name
            )

            # Читаем содержимое
            with open(tmp_wg.name, "r") as f1, open(tmp_clients.name, "r") as f2:
                wg_content = f1.read()
                clients_content = f2.read()

            # Удаляем временные файлы
            os.unlink(tmp_wg.name)
            os.unlink(tmp_clients.name)

        return {"status": "ok", "wg_conf": wg_content, "clients_table": clients_content}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении конфигов: {e}"
        )


@router.post("/replace_configs")
def replace_configs(
    request: ConfigsUpdateRequest,
    user=Depends(get_current_user),
):
    """
    Заменяет конфиги внутри контейнера и перезапускает интерфейс.
    """
    try:
        container = settings.DOCKER_CONTAINER

        # 1. Создаем временные файлы из полученных строк, чтобы передать их в docker_copy_to
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False
        ) as tmp_wg, tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_clients:

            tmp_wg.write(request.wg_conf)
            tmp_clients.write(request.clients_table)

            tmp_wg_path = tmp_wg.name
            tmp_clients_path = tmp_clients.name

        # 2. Копируем в контейнер
        docker_copy_to(container, tmp_wg_path, settings.WG_CONFIG_FILE)
        docker_copy_to(container, tmp_clients_path, settings.CLIENTS_TABLE_PATH)

        # 3. Чистим временные файлы на хосте
        os.unlink(tmp_wg_path)
        os.unlink(tmp_clients_path)

        # 4. Перезапускаем контейнер для применения настроек
        # (Или используйте вашу функцию restart_awg, если не хотите рестартить весь контейнер)
        import subprocess

        subprocess.run(f"docker restart {container}", shell=True, check=True)

        # 5. Проверка статуса
        check = docker_exec(container, "wg show")
        status = (
            "ok"
            if "interface:" in check
            else "warning: container restarted but wg not found"
        )

        return {"status": status}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при замене конфигов: {e}")


@router.get("/stats/{peer}")
def stat_one_peer(peer: str):
    return get_peer_stats(peer)


@router.get("/stats")
def stats():
    return get_wireguard_stats()
