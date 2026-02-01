import os
from services.awg_utils import (
    allocate_ip,
    extract_awg_params,
    generate_keys,
    read_server_config,
    update_clients_table,
    update_server_config,
    write_client_config,
)
from services.docker_utils import (
    docker_copy_to,
    docker_exec,
    restart_awg,
)


def add_client(client_name, endpoint, wg_config_file, container):
    """
    Основная функция: добавляет клиента AWG 2.0.
    """

    print("🚀 Добавление клиента...")

    pwd = os.getcwd()
    client_dir = os.path.join(pwd, "users", client_name)
    files_dir = os.path.join(pwd, "files")
    os.makedirs(client_dir, exist_ok=True)
    os.makedirs(files_dir, exist_ok=True)

    temp_conf = os.path.join(files_dir, "server.conf")
    temp_table = os.path.join(files_dir, "clientsTable")

    # 1. Генерация ключей
    key, pub, psk = generate_keys(container)

    # 2. Чтение конфига сервера
    server_conf = read_server_config(container, wg_config_file, temp_conf)

    # 3. Извлечение параметров AWG 2.0
    server_priv, port, awg_params = extract_awg_params(server_conf)

    # 4. Публичный ключ сервера
    server_pub = docker_exec(container, f"sh -c \"echo '{server_priv}' | wg pubkey\"")

    # 5. Выделение IP
    ip = allocate_ip(server_conf)

    # 6. Обновление server.conf
    update_server_config(temp_conf, client_name, pub, psk, ip)
    docker_copy_to(container, temp_conf, wg_config_file)

    # 7. Перезапуск
    restart_awg(container, wg_config_file)

    # 8. Создание клиентского .conf
    client_conf_path = os.path.join(client_dir, f"{client_name}.conf")
    write_client_config(
        client_conf_path, ip, key, psk, server_pub, endpoint, port, awg_params
    )

    # 9. Обновление clientsTable
    update_clients_table(
        container, pub, client_name, temp_table, "/opt/amnezia/awg/clientsTable"
    )

    print("🎉 Клиент успешно добавлен!")
    return client_conf_path
