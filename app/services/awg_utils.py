from datetime import datetime
import re
import subprocess
import json
from services.firewall_utils import unblock_ip
from services.docker_utils import docker_copy_from, docker_copy_to, docker_exec


def generate_keys(container: str) -> tuple[str, str, str]:
    """
    Генерирует приватный ключ клиента, публичный ключ и PSK.
    """
    key = docker_exec(container, "wg genkey")
    psk = docker_exec(container, "wg genpsk")
    pub = docker_exec(container, f"sh -c \"echo '{key}' | wg pubkey\"")
    return key, pub, psk


def read_server_config(container: str, wg_config_file: str, temp_path: str) -> str:
    """
    Копирует конфиг сервера из контейнера и возвращает его содержимое.
    """
    docker_copy_from(container, wg_config_file, temp_path)
    with open(temp_path, "r") as f:
        return f.read()


def extract_awg_params(server_conf: str) -> tuple[str, str, str]:
    """
    Извлекает:
    - приватный ключ сервера
    - порт
    - параметры AWG 2.0 (J/S/H/I)
    """
    # PrivateKey
    match = re.search(r"^\s*PrivateKey\s*=\s*(\S+)", server_conf, re.MULTILINE)
    if not match:
        raise RuntimeError("Не удалось найти PrivateKey в конфигурации сервера.")
    server_private_key = match.group(1)

    # ListenPort
    listen_port_match = re.search(r"^ListenPort\s*=\s*(\d+)", server_conf, re.MULTILINE)
    listen_port = listen_port_match.group(1) if listen_port_match else "51820"

    # AWG 2.0 параметры
    awg_params = "\n".join(
        m.group(0)
        for m in re.finditer(
            r"^#?\s*(Jc|Jmin|Jmax|S[1-4]|H[1-4]|I[1-5])\s*=\s*.*",
            server_conf,
            re.MULTILINE,
        )
    )

    return server_private_key, listen_port, awg_params


def allocate_ip(server_conf: str) -> str:
    """
    Находит первый свободный IP в диапазоне 10.8.1.X.
    """
    octet = 2
    while re.search(rf"AllowedIPs\s*=\s*10\.8\.1\.{octet}/32", server_conf):
        octet += 1
        if octet > 254:
            raise RuntimeError("Подсеть 10.8.1.0/24 заполнена.")

    return f"10.8.1.{octet}/32"


def update_server_config(temp_path: str, client_name: str, pub: str, psk: str, ip: str):
    """
    Добавляет новый блок [Peer] в конфиг сервера.
    """
    peer_block = f"""

[Peer]
# {client_name}
PublicKey = {pub}
PresharedKey = {psk}
AllowedIPs = {ip}

"""
    with open(temp_path, "a") as f:
        f.write(peer_block)


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
    """
    Создаёт клиентский .conf файл AWG 2.0.
    """
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


def update_clients_table(
    container: str, pub: str, client_name: str, temp_path: str, docker_path: str
):
    """
    Обновляет clientsTable: добавляет нового клиента.
    """
    # Копируем таблицу
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


def extract_client_ip(server_conf: str, client_name: str) -> str | None:
    """
    Находит внутренний IP клиента по его имени в конфиге.
    """
    lines = server_conf.splitlines()
    found = False

    for line in lines:
        if line.strip() == f"# {client_name}":
            found = True
            continue

        if found and "AllowedIPs" in line:
            # AllowedIPs = 10.8.1.5/32
            return line.split("=")[1].strip().split("/")[0]

        if found and line.strip().startswith("[Peer]"):
            break

    return None


def remove_client(client_name: str, wg_config_file: str, container: str):
    """
    Полностью удаляет клиента из AWG:
    - удаляет блок [Peer]
    - удаляет запись из clientsTable
    - снимает блокировку IP
    - перезапускает интерфейс
    """

    temp_conf = "/tmp/awg_remove.conf"
    temp_table = "/tmp/awg_clients_table.json"

    # 1. Скачиваем конфиг
    docker_copy_from(container, wg_config_file, temp_conf)

    with open(temp_conf, "r") as f:
        server_conf = f.read()

    # 2. Находим IP клиента
    client_ip = extract_client_ip(server_conf, client_name)

    # 3. Удаляем блок [Peer]
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

    # 4. Обновляем clientsTable
    docker_copy_from(container, "/opt/amnezia/awg/clientsTable", temp_table)

    with open(temp_table, "r") as f:
        table = json.load(f)

    table = [c for c in table if c["userData"]["clientName"] != client_name]

    with open(temp_table, "w") as f:
        json.dump(table, f, indent=4)

    # 5. Снимаем блокировку IP
    if client_ip:
        unblock_ip(client_ip)

    # 6. Возвращаем файлы в контейнер
    docker_copy_to(container, temp_conf, wg_config_file)
    docker_copy_to(container, temp_table, "/opt/amnezia/awg/clientsTable")

    # 7. Перезапуск AWG
    try:
        docker_exec(container, f"sh -c 'wg-quick down {wg_config_file} || true'")
        docker_exec(container, f"sh -c 'wg-quick up {wg_config_file}'")
    except Exception:
        print(
            "⚠️ Не удалось перезапустить wg-quick — возможно, интерфейс не был запущен."
        )

    print(f"❌ Клиент {client_name} полностью удалён.")
