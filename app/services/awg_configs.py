import subprocess
from core.config import settings
from services.docker_utils import docker_copy_to, docker_exec, docker_copy_from


def get_current_configs(local_wg_conf_path: str, local_clients_table_path: str):
    """
    Скачивает текущие конфиги из контейнера на хост.
    """
    container = settings.DOCKER_CONTAINER

    print(f"📥 Загрузка текущих конфигов из контейнера {container}...")

    try:
        # Используем твою функцию docker_copy_from
        docker_copy_from(container, settings.WG_CONFIG_FILE, local_wg_conf_path)
        docker_copy_from(
            container, settings.CLIENTS_TABLE_PATH, local_clients_table_path
        )
        print("✅ Конфиги успешно скачаны.")
    except Exception as e:
        print(f"❌ Ошибка при получении конфигов: {e}")
        raise


def replace_configs_and_restart(wg_conf_src: str, clients_table_src: str) -> bool:
    """
    Заменяет wg0.conf и clientsTable внутри Docker-контейнера и перезапускает его.
    """
    container = settings.DOCKER_CONTAINER

    try:
        print("📤 Копируем новые конфиги в контейнер...")
        docker_copy_to(container, wg_conf_src, settings.WG_CONFIG_FILE)
        docker_copy_to(container, clients_table_src, settings.CLIENTS_TABLE_PATH)

        print(f"🔄 Перезапускаем контейнер {container}...")
        # Перезапуск контейнера — самый надежный способ применить изменения в AmneziaWG
        subprocess.run(f"docker restart {container}", shell=True, check=True)

        # Небольшая пауза, чтобы интерфейс успел инициализироваться
        import time

        time.sleep(2)

        print("🩺 Проверка статуса интерфейса...")
        output = docker_exec(container, "wg show")

        if "interface:" in output:
            print("✅ WireGuard/AWG успешно запущен.")
            return True
        else:
            print("⚠️ Интерфейс не найден в выводе wg show.")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения команды Docker: {e}")
        return False
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")
        return False
