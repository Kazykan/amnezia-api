import subprocess
import os
import re
import json
from datetime import datetime

def add_client(client_name, endpoint, wg_config_file, docker_container):
    """
    Добавляет нового клиента WireGuard к существующей конфигурации внутри Docker-кон container.

    Аргументы:
    client_name (str): Имя клиента (используется для папок и комментариев).
    endpoint (str): Внешний IP-адрес или доменное имя сервера WireGuard.
    wg_config_file (str): Путь к файлу конфигурации WireGuard внутри Docker-контейнера (например, /etc/wireguard/wg0.conf).
    docker_container (str): Имя или ID Docker-контейнера, где запущен WireGuard.
    """
    # --- 1. Проверка и валидация аргументов ---
    print("🚀 Начинаем добавление клиента WireGuard...")
    
    # Проверка на наличие обязательных аргументов
    if not all([client_name, endpoint, wg_config_file, docker_container]):
        raise ValueError("Один или несколько обязательных аргументов (CLIENT_NAME, ENDPOINT, WG_CONFIG_FILE, DOCKER_CONTAINER) не предоставлены.")

    # Валидация CLIENT_NAME (только буквы, цифры, _, -)
    if not re.fullmatch(r"^[a-zA-Z0-9_-]+$", client_name):
        raise ValueError(f"Недопустимое имя клиента: {client_name}. Разрешены только буквы, цифры, подчеркивания и дефисы.")

    # Получение текущего рабочего каталога
    pwd = os.getcwd()

    # --- 2. Создание необходимых директорий ---
    # Создаем директории для файлов клиента и временных файлов
    client_dir = os.path.join(pwd, "users", client_name)
    files_dir = os.path.join(pwd, "files")
    
    os.makedirs(client_dir, exist_ok=True)
    os.makedirs(files_dir, exist_ok=True)
    print(f"📁 Созданы директории: {client_dir} и {files_dir}")

    # --- 3. Генерация ключей WireGuard ---
    # Генерируем приватный ключ (key) и PresharedKey (psk) для клиента
    # Выполнение команд внутри Docker-контейнера гарантирует, что используются его утилиты
    try:
        key = subprocess.check_output(f"docker exec -i {docker_container} wg genkey", shell=True, text=True).strip()
        psk = subprocess.check_output(f"docker exec -i {docker_container} wg genpsk", shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при генерации ключей WireGuard: {e}")
    
    client_public_key = subprocess.check_output(f"echo '{key}' | docker exec -i {docker_container} wg pubkey", shell=True, text=True).strip()
    print("🔑 Ключи клиента WireGuard сгенерированы.")
    
    # --- 4. Получение и анализ текущей конфигурации сервера ---
    server_conf_path = os.path.join(files_dir, "server.conf")
    
    # Копируем текущий файл конфигурации сервера WireGuard из контейнера
    try:
        subprocess.run(f"docker exec -i {docker_container} cat {wg_config_file}", shell=True, check=True, text=True, stdout=open(server_conf_path, 'w'))
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Не удалось скопировать конфигурацию сервера из Docker: {e}")

    # Извлекаем данные из конфигурации сервера
    with open(server_conf_path, 'r') as f:
        server_conf_content = f.read()

    # Извлечение приватного ключа сервера
    server_private_key_match = re.search(r"^PrivateKey\s*=\s*(\S+)", server_conf_content, re.MULTILINE)
    if not server_private_key_match:
        raise RuntimeError("Не удалось найти PrivateKey сервера в конфигурации.")
    server_private_key = server_private_key_match.group(1)

    # Получение публичного ключа сервера
    server_public_key = subprocess.check_output(f"echo '{server_private_key}' | docker exec -i {docker_container} wg pubkey", shell=True, text=True).strip()
    
    # Извлечение порта прослушивания
    listen_port_match = re.search(r"^ListenPort\s*=\s*(\d+)", server_conf_content, re.MULTILINE)
    listen_port = listen_port_match.group(1) if listen_port_match else "51820" # Default

    # Извлечение дополнительных параметров (Amnezia-specific)
    additional_params = "\n".join(re.findall(r"^(Jc|Jmin|Jmax|S1|S2|H[1-4])\s*=\s*.*", server_conf_content, re.MULTILINE))
    print("📄 Данные сервера (ключи, порт, доп. параметры) извлечены.")

    # --- 5. Выделение IP-адреса для клиента ---
    # Поиск первого свободного октета в диапазоне 10.8.1.X
    octet = 2
    while re.search(rf"AllowedIPs\s*=\s*10\.8\.1\.{octet}/32", server_conf_content):
        octet += 1
        if octet > 254:
            raise RuntimeError("Внутренняя подсеть WireGuard 10.8.1.0/24 заполнена.")

    client_ip = f"10.8.1.{octet}/32"
    allowed_ips = client_ip
    print(f"✅ Клиенту выделен IP-адрес: {client_ip}")

    # --- 6. Обновление конфигурации сервера (Добавление Peer) ---
    # Блок [Peer] для нового клиента, добавляется в конец server.conf
    peer_config = f"""
[Peer]
# {client_name}
PublicKey = {client_public_key}
PresharedKey = {psk}
AllowedIPs = {allowed_ips}

"""
    with open(server_conf_path, 'a') as f:
        f.write(peer_config)

    # Копирование обновленной конфигурации обратно в Docker-контейнер
    try:
        subprocess.run(f"docker cp {server_conf_path} {docker_container}:{wg_config_file}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Не удалось скопировать обновленную конфигурацию обратно в Docker: {e}")
    
    print("💾 Конфигурация сервера обновлена.")

    # --- 7. Перезапуск WireGuard внутри Docker ---
    # Для применения изменений требуется перезапуск wg-quick
    try:
        # Сначала 'down', затем 'up'
        subprocess.run(f"docker exec -i {docker_container} sh -c 'wg-quick down {wg_config_file} && wg-quick up {wg_config_file}'", shell=True, check=True)
        print("🔄 WireGuard сервис в контейнере перезапущен.")
    except subprocess.CalledProcessError as e:
        # Если wg-quick упадет, сообщаем об ошибке, но продолжаем, так как конфиг на месте
        print(f"⚠️ Предупреждение: Ошибка при перезапуске WireGuard. Возможно, сервис не был запущен. Ошибка: {e}")

    # --- 8. Создание файла конфигурации клиента (.conf) ---
    client_config_path = os.path.join(client_dir, f"{client_name}.conf")
    
    # Блок [Interface] и [Peer] для клиента
    client_config = f"""[Interface]
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
    with open(client_config_path, 'w') as f:
        f.write(client_config)
    
    print(f"📝 Файл конфигурации клиента создан: {client_config_path}")
    
    # --- 9. Обновление таблицы клиентов (AmneziaVPN специфично) ---
    clients_table_path = os.path.join(files_dir, "clientsTable")
    docker_clients_table_path = "/opt/amnezia/awg/clientsTable" # Жестко заданный путь в скрипте

    # Копирование текущей таблицы клиентов из Docker
    try:
        subprocess.run(f"docker exec -i {docker_container} cat {docker_clients_table_path}", shell=True, check=True, text=True, stdout=open(clients_table_path, 'w'))
    except subprocess.CalledProcessError:
        # Если файл не существует, создаем пустой JSON-массив
        with open(clients_table_path, 'w') as f:
            f.write("[]")
            
    # Чтение, обновление и запись таблицы клиентов (JSON-операции)
    with open(clients_table_path, 'r') as f:
        clients_table = json.load(f)

    # Добавляем нового клиента
    new_client_entry = {
        "clientId": client_public_key,
        "userData": {
            "clientName": client_name,
            "creationDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    clients_table.append(new_client_entry)
    
    # Сохраняем обновленный JSON
    with open(clients_table_path, 'w') as f:
        json.dump(clients_table, f, indent=4)

    # Копирование обновленной таблицы клиентов обратно в Docker-контейнер
    try:
        subprocess.run(f"docker cp {clients_table_path} {docker_container}:{docker_clients_table_path}", shell=True, check=True)
        print("📋 Таблица клиентов (clientsTable) обновлена.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Предупреждение: Не удалось обновить таблицу клиентов в Docker: {e}")

    return client_config

