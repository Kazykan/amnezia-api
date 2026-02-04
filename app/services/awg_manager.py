import os
import re
import json
import subprocess
from datetime import datetime

from core.config import settings
from services.docker_utils import (
    docker_exec,
    docker_copy_from,
    docker_copy_to,
    restart_awg,
)
from services.firewall_utils import unblock_ip


# -----------------------------
# Загрузка AWG параметров из JSON
# -----------------------------
def load_awg_params() -> str:
    params_path = os.path.join(os.getcwd(), "awg_params.json")

    if not os.path.exists(params_path):
        raise RuntimeError("Файл awg_params.json не найден!")

    with open(params_path, "r") as f:
        params = json.load(f)

    # Формируем строки вида "Jc = 4"
    lines = [f"{k} = {v}" for k, v in params.items()]
    return "\n".join(lines)


# -----------------------------
# Генерация ключей
# -----------------------------
def generate_keys(container: str) -> tuple[str, str, str]:
    key = docker_exec(container, "wg genkey")
    psk = docker_exec(container, "wg genpsk")
    pub = docker_exec(container, f"sh -c \"echo '{key}' | wg pubkey\"")
    return key, pub, psk


# -----------------------------
# Чтение server.conf
# -----------------------------
def read_server_config(container: str, wg_config_file: str, temp_path: str) -> str:
    docker_copy_from(container, wg_config_file, temp_path)
    with open(temp_path, "r") as f:
        return f.read()


# -----------------------------
# Выделение IP
# -----------------------------
def allocate_ip(server_conf: str) -> str:
    octet = 2
    while re.search(rf"AllowedIPs\s*=\s*10\.8\.1\.{octet}/32", server_conf):
        octet += 1
        if octet > 254:
            raise RuntimeError("Подсеть 10.8.1.0/24 заполнена.")
    return f"10.8.1.{octet}/32"


# -----------------------------
# Обновление server.conf
# -----------------------------
def update_server_config(temp_path: str, client_name: str, pub: str, psk: str, ip: str):
    peer_block = f"""

[Peer]
# {client_name}
PublicKey = {pub}
PresharedKey = {psk}
AllowedIPs = {ip}

"""
    with open(temp_path, "a") as f:
        f.write(peer_block)


# -----------------------------
# Создание клиентского .conf
# -----------------------------
def write_client_config(
    path: str,
    ip: str,
    key: str,
    psk: str,
    server_pub: str,
    endpoint: str,
    port: str,
    awg_params: str,
):
    config = f"""[Interface]
Address = {ip}
DNS = 1.1.1.1, 1.0.0.1
PrivateKey = {key}
{awg_params}

[Peer]
PublicKey = {server_pub}
PresharedKey = {psk}
AllowedIPs = 0.0.0.0/0
Endpoint = {endpoint}:{port}
PersistentKeepalive = 25
"""
    with open(path, "w") as f:
        f.write(config)


# -----------------------------
# Обновление clientsTable
# -----------------------------
def update_clients_table(container: str, pub: str, client_name: str, temp_path: str):
    docker_path = "/opt/amnezia/awg/clientsTable"

    try:
        docker_copy_from(container, docker_path, temp_path)
    except subprocess.CalledProcessError:
        with open(temp_path, "w") as f:
            f.write("[]")

    with open(temp_path, "r") as f:
        table = json.load(f)

    table.append(
        {
            "clientId": pub,
            "userData": {
                "clientName": client_name,
                "creationDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
    )

    with open(temp_path, "w") as f:
        json.dump(table, f, indent=4)

    docker_copy_to(container, temp_path, docker_path)


# -----------------------------
# Валидация клиента
# -----------------------------
def validate_client_config(container: str, client_conf_path: str, wg_config_file: str):
    with open(client_conf_path, "r") as f:
        content = f.read()

    required = [
        "[Interface]",
        "PrivateKey",
        "Address",
        "[Peer]",
        "PublicKey",
        "Endpoint",
    ]
    for r in required:
        if r not in content:
            raise RuntimeError(f"Некорректный конфиг клиента: отсутствует {r}")

    priv_match = re.search(r"PrivateKey\s*=\s*(\S+)", content)
    if not priv_match:
        raise RuntimeError("Не удалось извлечь PrivateKey из клиентского конфига")
    priv = priv_match.group(1)

    try:
        docker_exec(container, f"sh -c \"echo '{priv}' | wg pubkey\"")
    except Exception:
        raise RuntimeError("Некорректный приватный ключ клиента")

    try:
        docker_exec(container, f"wg-quick strip {wg_config_file}")
    except Exception:
        raise RuntimeError("Серверный конфиг повреждён после добавления клиента")

    return True


# -----------------------------
# Основная функция add_client
# -----------------------------
def add_client(client_name: str) -> str:
    container = settings.DOCKER_CONTAINER
    endpoint = settings.ENDPOINT
    wg_config_file = settings.WG_CONFIG_FILE

    pwd = os.getcwd()
    client_dir = os.path.join(pwd, "users", client_name)
    files_dir = os.path.join(pwd, "files")
    os.makedirs(client_dir, exist_ok=True)
    os.makedirs(files_dir, exist_ok=True)

    temp_conf = os.path.join(files_dir, "server.conf")
    temp_table = os.path.join(files_dir, "clientsTable")

    key, pub, psk = generate_keys(container)

    server_conf = read_server_config(container, wg_config_file, temp_conf)

    # Загружаем AWG параметры из JSON
    awg_params = load_awg_params()

    server_priv_match = re.search(r"PrivateKey\s*=\s*(\S+)", server_conf)
    server_priv = server_priv_match.group(1)
    server_pub = docker_exec(container, f"sh -c \"echo '{server_priv}' | wg pubkey\"")

    ip = allocate_ip(server_conf)

    update_server_config(temp_conf, client_name, pub, psk, ip)
    docker_copy_to(container, temp_conf, wg_config_file)

    restart_awg(container, wg_config_file)

    client_conf_path = os.path.join(client_dir, f"{client_name}.conf")
    write_client_config(
        client_conf_path,
        ip,
        key,
        psk,
        server_pub,
        endpoint,
        port="33042",
        awg_params=awg_params,
    )

    validate_client_config(container, client_conf_path, wg_config_file)

    update_clients_table(container, pub, client_name, temp_table)

    with open(client_conf_path, "r") as f:
        return f.read()


# -----------------------------
# Удаление клиента
# -----------------------------
def extract_client_ip(server_conf: str, client_name: str) -> str | None:
    lines = server_conf.splitlines()
    found = False

    for line in lines:
        if line.strip() == f"# {client_name}":
            found = True
            continue

        if found and "AllowedIPs" in line:
            return line.split("=")[1].strip().split("/")[0]

        if found and line.strip().startswith("[Peer]"):
            break

    return None


def remove_client(client_name: str):
    container = settings.DOCKER_CONTAINER
    wg_config_file = settings.WG_CONFIG_FILE

    temp_conf = "/tmp/awg_remove.conf"
    temp_table = "/tmp/awg_clients_table.json"
    docker_table_path = "/opt/amnezia/awg/clientsTable"

    docker_copy_from(container, wg_config_file, temp_conf)

    with open(temp_conf, "r") as f:
        server_conf = f.read()

    client_ip = extract_client_ip(server_conf, client_name)

    lines = server_conf.splitlines(keepends=True)
    new_lines = []
    skip = False

    for line in lines:
        if line.strip() == f"# {client_name}":
            skip = True
            continue

        if skip and line.strip().startswith("[Peer]"):
            skip = False
            continue

        if not skip:
            new_lines.append(line)

    with open(temp_conf, "w") as f:
        f.writelines(new_lines)

    docker_copy_from(container, docker_table_path, temp_table)

    with open(temp_table, "r") as f:
        table = json.load(f)

    table = [c for c in table if c["userData"]["clientName"] != client_name]

    with open(temp_table, "w") as f:
        json.dump(table, f, indent=4)

    if client_ip:
        unblock_ip(client_ip)

    docker_copy_to(container, temp_conf, wg_config_file)
    docker_copy_to(container, temp_table, docker_table_path)

    docker_exec(container, f"sh -c 'wg-quick down {wg_config_file} || true'")
    docker_exec(container, f"sh-quick up {wg_config_file}'")
