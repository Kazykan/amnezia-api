import subprocess
from app.core.config import Settings

def replace_configs_and_restart(wg_conf: str, clients_table: str) -> bool:
    """
    Заменяет wg0.conf и clientsTable внутри Docker-контейнера,
    перезапускает контейнер и проверяет, что WireGuard поднялся.

    Аргументы:
    wg_conf (str): путь к локальному wg0.conf
    clients_table (str): путь к локальному clientsTable
    """

    wg_conf_path = Settings.WG_CONFIG_FILE
    clients_table_path = Settings.CLIENTS_TABLE_PATH
    docker_container = Settings.DOCKER_CONTAINER

    print("📤 Копируем новые конфиги внутрь контейнера...")
    try:
        subprocess.run(f"docker cp {wg_conf} {docker_container}:{wg_conf_path}", shell=True, check=True)
        subprocess.run(f"docker cp {clients_table} {docker_container}:{clients_table_path}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при копировании файлов: {e}")

    print("🔄 Перезапускаем контейнер...")
    try:
        subprocess.run(f"docker restart {docker_container}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Не удалось перезапустить контейнер: {e}")

    print("🩺 Проверяем статус WireGuard внутри контейнера...")
    try:
        # Проверка через wg show
        output = subprocess.check_output(
            f"docker exec -i {docker_container} wg show",
            shell=True, text=True
        )
        if "interface: wg0" in output:
            print("✅ WireGuard успешно запущен и интерфейс wg0 активен.")
            return True
        else:
            print("⚠️ WireGuard не запустился корректно, интерфейс wg0 не найден.")
            return False
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при проверке WireGuard: {e}")
