from ast import parse
from fastapi import APIRouter

from services.utils import parse_wg_show
from services.docker import exec_in_container

router = APIRouter()


@router.get("/clients")
def list_clients():
    """
    Получить список клиентов из AmneziaWG
    """
    raw = exec_in_container("amnezia-awg", "wg show")
    result = parse_wg_show(raw)
    return {"status": "ok", "output": result}
