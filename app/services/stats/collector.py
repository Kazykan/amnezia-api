import subprocess
import time

from services.docker_utils import get_docker_base_cmd
from .parser import parse_wg_dump
from .database import save_stats

from core.config import settings  # чтобы использовать settings.DOCKER_CONTAINER


def collect_once():
    raw = subprocess.check_output(
        f"docker exec -i {settings.DOCKER_CONTAINER} wg show awg0 dump",
            shell=True,
            text=True
            )

    peers = parse_wg_dump(raw)
    timestamp = int(time.time())

    save_stats(timestamp, peers)
