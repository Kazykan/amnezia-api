import subprocess
import sys
from core.config import settings


def _log(msg: str):
    """Простой логгер."""
    print(f"[docker-utils] {msg}", file=sys.stderr)


def _run(cmd: str, *, capture_output=False) -> str:
    """
    Универсальный запуск shell-команд с логированием.
    """
    _log(f"CMD: {cmd}")

    try:
        if capture_output:
            result = subprocess.check_output(cmd, shell=True, text=True)
            _log(f"OUTPUT: {result.strip()}")
            return result.strip()

        subprocess.run(cmd, shell=True, check=True)
        _log("STATUS: OK")
        return ""

    except subprocess.CalledProcessError as e:
        _log(f"ERROR: exit code {e.returncode}")
        _log(f"STDERR: {e.stderr if hasattr(e, 'stderr') else 'no stderr'}")
        raise


def get_docker_base_cmd(container: str) -> str:
    """
    Формирует базовую часть команды: /usr/bin/docker exec -i имя_контейнера
    """
    return f"{settings.DOCKER_BIN} exec -i {container}"


def docker_exec(container: str, command: str) -> str:
    """
    Выполняет команду внутри Docker-контейнера и возвращает вывод.
    """
    full_cmd = f"{get_docker_base_cmd(container)} {command}"
    return _run(full_cmd, capture_output=True)


def docker_copy_from(container: str, src: str, dst: str):
    """
    Копирует файл ИЗ контейнера на хост.
    """
    cmd = f"{get_docker_base_cmd(container)} cat {src}"
    _log(f"Copy FROM container: {container}:{src} -> {dst}")

    with open(dst, "w") as f:
        try:
            subprocess.run(cmd, shell=True, check=True, text=True, stdout=f)
            _log("STATUS: OK")
        except subprocess.CalledProcessError as e:
            _log(f"ERROR copying from container: exit {e.returncode}")
            raise


def docker_copy_to(container: str, src: str, dst: str):
    """
    Копирует файл С хоста в контейнер.
    """
    cmd = f"{settings.DOCKER_BIN} cp {src} {container}:{dst}"
    _log(f"Copy TO container: {src} -> {container}:{dst}")
    _run(cmd)


def restart_awg(container: str, wg_config_file: str):
    """
    Перезапускает интерфейс AWG/WireGuard внутри контейнера.
    """
    _log(f"Restarting AWG: {wg_config_file}")

    try:
        docker_exec(
            container,
            f"sh -c 'wg-quick down {wg_config_file} || true && wg-quick up {wg_config_file}'",
        )
        _log("AWG restarted successfully")
    except Exception:
        _log("⚠️ Failed to restart wg-quick — interface may not have been running.")
