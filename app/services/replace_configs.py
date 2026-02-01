import subprocess
from core.config import settings
from docker_utils import docker_copy_to, docker_exec


def replace_configs_and_restart(wg_conf: str, clients_table: str) -> bool:
    """
    Заменяет wg0.conf и clientsTable внутри Docker-контейнера,
    перезапускает контейнер и проверяет, что WireGuard/AWG поднялся.

    Аргументы:
        wg_conf (str): путь к локальному wg0.conf
        clients_table (str): путь к локальному clientsTable

    Возвращает:
        bool: True если интерфейс поднялся, иначе False
    """

    wg_conf_path = settings.WG_CONFIG_FILE
    clients_table_path = settings.CLIENTS_TABLE_PATH
    docker_container = settings.DOCKER_CONTAINER

    print("📤 Копируем новые конфиги внутрь контейнера...")

    try:
        docker_copy_to(docker_container, wg_conf, wg_conf_path)
        docker_copy_to(docker_container, clients_table, clients_table_path)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при копировании файлов в контейнер: {e}")

    print("🔄 Перезапускаем контейнер...")

    try:
        subprocess.run(f"docker restart {docker_container}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Не удалось перезапустить контейнер: {e}")

    print("🩺 Проверяем статус WireGuard/AWG внутри контейнера...")

    try:
        output = docker_exec(docker_container, "wg show")
    except subprocess.CalledProcessError:
        print("⚠️ wg show вернул ошибку — возможно, интерфейс не поднялся.")
        return False

    # Проверяем наличие интерфейса (wg0, awg0, wg1 — любой)
    if "interface:" in output:
        print("✅ WireGuard/AWG успешно запущен.")
        return True

    print("⚠️ Интерфейс WireGuard/AWG не найден.")
    return False
