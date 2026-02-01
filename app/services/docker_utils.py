import subprocess
from core.config import settings


def get_docker_base_cmd(container: str) -> str:
    """Формирует базовую часть команды: /usr/bin/docker exec -i имя_контейнера"""
    return f"{settings.DOCKER_BIN} exec -i {container}"


def docker_exec(container: str, command: str) -> str:
    """
    Выполняет команду внутри Docker-контейнера и возвращает вывод.
    """
    return subprocess.check_output(
        f"{get_docker_base_cmd(container)} {command}", shell=True, text=True
    ).strip()


def docker_copy_from(container: str, src: str, dst: str):
    """
    Копирует файл ИЗ контейнера на хост.
    """
    subprocess.run(
        f"{get_docker_base_cmd(container)} cat {src}",
        shell=True,
        check=True,
        text=True,
        stdout=open(dst, "w"),
    )


def docker_copy_to(container: str, src: str, dst: str):
    """
    Копирует файл С хоста в контейнер.
    """
    subprocess.run(f"docker cp {src} {container}:{dst}", shell=True, check=True)


def restart_awg(container: str, wg_config_file: str):
    """
    Перезапускает интерфейс AWG/WireGuard внутри контейнера.
    """
    try:
        docker_exec(
            container,
            f"sh -c 'wg-quick down {wg_config_file} && wg-quick up {wg_config_file}'",
        )
    except subprocess.CalledProcessError:
        print(
            "⚠️ Не удалось перезапустить wg-quick — возможно, интерфейс не был запущен."
        )
