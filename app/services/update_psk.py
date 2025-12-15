import sys
import json
import subprocess
import os
from typing import List, Dict

# --- Константы ---
SERVER_CONF_PATH = "/tmp/wg_temp.conf"

def run_docker_exec(docker_container: str, command: str) -> str:
    """Выполняет команду внутри Docker-контейнера и возвращает вывод."""
    # print(f"Executing: docker exec -i {docker_container} {command}")
    result = subprocess.run(
        f"docker exec -i {docker_container} {command}",
        shell=True,
        capture_output=True,
        text=True,
        check=True,  # Вызывает исключение при ошибке
    )
    return result.stdout.strip()

# =========================================================================
# 1. Функция скачивания конфигурации
# =========================================================================

def download_config_from_docker(wg_config_file: str, docker_container: str) -> str:
    """
    Скачивает конфигурационный файл WireGuard из Docker-контейнера
    и сохраняет его во временный локальный файл.
    
    Returns:
        str: Полный путь к локально сохраненному файлу.
        
    Raises:
        subprocess.CalledProcessError: Если команда Docker завершилась ошибкой.
    """
    print(f"Downloading config file from {docker_container}:{wg_config_file} to {SERVER_CONF_PATH}...")
    
    # 1. Получение содержимого файла
    config_content = run_docker_exec(docker_container, f"cat {wg_config_file}")
    
    # 2. Сохранение временного файла
    with open(SERVER_CONF_PATH, 'w', encoding='utf-8') as f:
        f.write(config_content)
        
    print("Config file downloaded successfully.")
    return SERVER_CONF_PATH

# =========================================================================
# 2. Функция обновления содержимого
# =========================================================================

def update_config_content(local_config_path: str, client_configs: List[Dict[str, str]]):
    """
    Читает локальный файл конфигурации, обновляет PresharedKey для указанных
    клиентов и перезаписывает локальный файл.
    """
    print("Starting client configuration update...")
    
    try:
        with open(local_config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Local config file {local_config_path} not found.")
        return

    updated_lines = []
    current_client = None
    update_performed = False

    for line in lines:
        stripped_line = line.strip()
        
        # Шаг 1: Поиск комментария с именем клиента
        if stripped_line.startswith("#"):
            for entry in client_configs:
                target_name = entry.get('client_name')
                # Ищем имя клиента в комментарии, игнорируя пробелы
                if f"#{target_name}" in stripped_line.replace(' ', ''):
                    current_client = entry
                    break
        
        # Шаг 2: Замена PresharedKey
        if current_client and stripped_line.startswith("PresharedKey"):
            new_key = current_client['new_preshared_key']
            # Добавляем новую строку PresharedKey
            updated_lines.append(f"PresharedKey = {new_key}\n")
            print(f"Updated PSK for client {current_client['client_name']}")
            current_client = None # Сбросить флаг, чтобы не менять другие ключи
            update_performed = True
            continue
            
        # Шаг 3: Сброс флага при начале нового блока [Peer]
        if stripped_line == "[Peer]":
            current_client = None

        updated_lines.append(line)

    # 4. Сохранение измененного конфига
    if update_performed:
        with open(local_config_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        print(f"Local config file {local_config_path} updated successfully.")
    else:
        print("Warning: No PresharedKeys were updated. Local file remains unchanged.")

# =========================================================================
# 3. Функция записи файла и перезапуска
# =========================================================================

def upload_and_restart_wireguard(wg_config_file: str, docker_container: str, local_config_path: str):
    """
    Копирует измененный локальный файл обратно в Docker-контейнер и
    перезапускает службу WireGuard.
    
    Raises:
        subprocess.CalledProcessError: Если команда Docker завершилась ошибкой.
    """
    
    # 1. Возврат конфига в контейнер
    print(f"Copying updated config from {local_config_path} back to {docker_container}:{wg_config_file}...")
    subprocess.run(
        f"docker cp {local_config_path} {docker_container}:{wg_config_file}",
        shell=True,
        check=True
    )
        
    # 2. Перезапуск WireGuard
    print("Restarting WireGuard service...")
    # Используем двойной запуск/остановку, как в Bash-скрипте
    run_docker_exec(docker_container, f'sh -c "wg-quick down {wg_config_file} || true && wg-quick up {wg_config_file}"')
    
    print("WireGuard restarted successfully.")
    
    # 3. Удаление временного файла
    if os.path.exists(local_config_path):
        os.remove(local_config_path)
        print("Cleaned up temporary file.")


# =========================================================================
# ГЛАВНАЯ ФУНКЦИЯ (КООРДИНАТОР)
# =========================================================================

def update_clients_psk(wg_config_file: str, docker_container: str, json_input: List[Dict[str, str]] | None = None):
    """
    Координирует процесс обновления PresharedKey: скачивание, обновление,
    запись и перезапуск WireGuard.
    """
    if not wg_config_file or not docker_container:
        raise ValueError("Usage: update_wireguard_psk_modular(<WG_CONFIG_FILE>, <DOCKER_CONTAINER>, [JSON_DATA])")

    # Чтение JSON (если не передан)
    if json_input is None:
        try:
            print("Reading JSON data from stdin...")
            json_data = sys.stdin.read()
            client_configs = json.loads(json_data)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to decode JSON from stdin: {e}")
            return
    else:
        client_configs = json_input
    
    local_path = ""
    try:
        # 1. СКАЧИВАНИЕ
        local_path = download_config_from_docker(wg_config_file, docker_container)

        # 2. ОБНОВЛЕНИЕ СОДЕРЖИМОГО
        update_config_content(local_path, client_configs)

        # 3. ЗАПИСЬ И ПЕРЕЗАПУСК
        upload_and_restart_wireguard(wg_config_file, docker_container, local_path)
        
        print("\nProcess finished successfully.")

    except subprocess.CalledProcessError as e:
        print(f"\nFATAL ERROR during Docker operation or WG restart: {e.cmd}")
        print(f"Stderr: {e.stderr}")
        
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

    finally:
        # Убедимся, что временный файл удален, если произошла ошибка до шага 3
        if local_path and os.path.exists(local_path):
            os.remove(local_path)

