from datetime import datetime
import json
import os
import re
import subprocess

from services.docker import exec_in_container

from datetime import datetime
import json
import os
import re
import subprocess

from services.docker import exec_in_container


def add_client(client_name, endpoint, wg_config_file, docker_container):
    # Проверка аргументов
    if not client_name or not endpoint or not wg_config_file or not docker_container:
        raise ValueError("Error: Missing required arguments")

    if not re.match(r"^[a-zA-Z0-9_-]+$", client_name):
        raise ValueError(
            "Error: Invalid CLIENT_NAME. Only letters, numbers, underscores, and hyphens are allowed."
        )

    pwd = os.getcwd()
    os.makedirs(f"{pwd}/users/{client_name}", exist_ok=True)
    os.makedirs(f"{pwd}/files", exist_ok=True)

    # Генерация ключей и очистка лишних символов
    key = exec_in_container(docker_container, "wg genkey").strip()
    psk = exec_in_container(docker_container, "wg genpsk").strip()

    server_conf_path = f"{pwd}/files/server.conf"
    with open(server_conf_path, "w") as f:
        f.write(exec_in_container(docker_container, f"cat {wg_config_file}"))

    # Получаем параметры сервера
    with open(server_conf_path) as f:
        server_conf = f.read()

    match = re.search(r"^PrivateKey\s*=\s*(\S+)", server_conf, re.MULTILINE)
    if not match:
        raise ValueError("Не удалось найти PrivateKey в конфиге WireGuard")
    server_private_key = match.group(1).strip()

    server_public_key = exec_in_container(
        docker_container, "wg pubkey", input_data=server_private_key
    ).strip()

    match_listen_port = re.search(r"ListenPort\s*=\s*(\d+)", server_conf)
    if not match_listen_port:
        raise ValueError("Не удалось найти ListenPort в конфиге WireGuard")
    listen_port = match_listen_port.group(1).strip()

    additional_params = "\n".join(
        re.findall(r"^(Jc|Jmin|Jmax|S1|S2|H[1-4])\s*=\s*.*", server_conf, re.MULTILINE)
    )

    # Выбираем свободный IP
    octet = 2
    while re.search(rf"AllowedIPs\s*=\s*10\.8\.1\.{octet}/32", server_conf):
        octet += 1
        if octet > 254:
            raise RuntimeError("Error: WireGuard internal subnet 10.8.1.0/24 is full")

    client_ip = f"10.8.1.{octet}/32"
    allowed_ips = client_ip

    client_public_key = exec_in_container(
        docker_container, "wg pubkey", input_data=key
    ).strip()

    # Добавляем клиента в server.conf
    with open(server_conf_path, "a") as f:
        f.write(
            f"""
[Peer]
# {client_name}
PublicKey = {client_public_key}
PresharedKey = {psk}
AllowedIPs = {allowed_ips}

"""
        )

    subprocess.run(
        ["docker", "cp", server_conf_path, f"{docker_container}:{wg_config_file}"],
        check=True,
    )
    exec_in_container(
        docker_container,
        f"sh -c 'wg-quick down {wg_config_file} && wg-quick up {wg_config_file}'",
    )

    # Создаем клиентский конфиг
    client_conf = f"""[Interface]
Address = {client_ip}
DNS = 1.1.1.1, 1.0.0.1
PrivateKey = {key}
{additional_params}
[Peer]
PublicKey = {server_public_key}
PresharedKey = {psk}
AllowedIPs = 0.0.0.0/0
Endpoint = {endpoint}:{listen_port}
PersistentKeepalive = 25
"""

    client_conf_path = f"{pwd}/users/{client_name}/{client_name}.conf"
    with open(client_conf_path, "w") as f:
        f.write(client_conf)

    # Обновляем clientsTable
    clients_table_path = f"{pwd}/files/clientsTable"
    try:
        clients_table = exec_in_container(
            docker_container, "cat /opt/amnezia/awg/clientsTable"
        )
        clients = json.loads(clients_table)
    except Exception:
        clients = []

    creation_date = datetime.now().isoformat()
    clients.append(
        {
            "clientId": client_public_key,
            "userData": {"clientName": client_name, "creationDate": creation_date},
        }
    )

    with open(clients_table_path, "w") as f:
        json.dump(clients, f, indent=2)

    subprocess.run(
        [
            "docker",
            "cp",
            clients_table_path,
            f"{docker_container}:/opt/amnezia/awg/clientsTable",
        ],
        check=True,
    )

    print(f"Client {client_name} successfully added to WireGuard")
    return client_conf
