import json

from services.docker_utils import (
    docker_exec,
    docker_copy_from,
    docker_copy_to,
)
from services.firewall_utils import unblock_ip


# -----------------------------
# Вспомогательная функция: найти IP клиента
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


# -----------------------------
# Удаление клиента
# -----------------------------
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
    docker_table_path = "/opt/amnezia/awg/clientsTable"

    print(f"[awg] 🗑 Удаление клиента: {client_name}")

    # 1. Скачиваем server.conf
    docker_copy_from(container, wg_config_file, temp_conf)

    with open(temp_conf, "r") as f:
        server_conf = f.read()

    # 2. Находим IP клиента
    client_ip = extract_client_ip(server_conf, client_name)
    print(f"[awg] IP клиента: {client_ip}")

    # 3. Удаляем блок клиента из server.conf
    lines = server_conf.splitlines(keepends=True)
    new_lines = []
    skip = False
    removed = False

    for line in lines:
        if line.strip() == f"# {client_name}":
            skip = True
            removed = True
            continue

        if skip and line.strip().startswith("[Peer]"):
            skip = False
            continue

        if not skip:
            new_lines.append(line)

    if not removed:
        print(f"[awg] ⚠ Клиент {client_name} не найден в server.conf")

    with open(temp_conf, "w") as f:
        f.writelines(new_lines)

    # 4. Обновляем clientsTable
    docker_copy_from(container, docker_table_path, temp_table)

    with open(temp_table, "r") as f:
        table = json.load(f)

    new_table = [c for c in table if c["userData"]["clientName"] != client_name]

    if len(new_table) == len(table):
        print(f"[awg] ⚠ Клиент {client_name} отсутствовал в clientsTable")

    with open(temp_table, "w") as f:
        json.dump(new_table, f, indent=4)

    # 5. Снимаем блокировку IP
    if client_ip:
        print(f"[awg] 🔓 Снятие блокировки IP {client_ip}")
        unblock_ip(client_ip)

    # 6. Возвращаем обновлённые файлы в контейнер
    docker_copy_to(container, temp_conf, wg_config_file)
    docker_copy_to(container, temp_table, docker_table_path)

    # 7. Перезапуск AWG
    print("[awg] 🔄 Перезапуск AWG")
    try:
        docker_exec(container, f"sh -c 'wg-quick down {wg_config_file} || true'")
        docker_exec(container, f"sh -c 'wg-quick up {wg_config_file}'")
        print("[awg] ✔ AWG успешно перезапущен")
    except Exception:
        print("[awg] ⚠ Не удалось перезапустить wg-quick")

    print(f"[awg] ❌ Клиент {client_name} полностью удалён.")
