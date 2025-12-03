from ast import parse
from fastapi import APIRouter, Depends

from deps.auth import get_current_user
from services.utils import parse_wg_show
from services.docker import exec_in_container

router = APIRouter()


@router.get("/clients")
def list_clients(user=Depends(get_current_user)):
    """
    Получить список клиентов из AmneziaWG
    """
    raw = exec_in_container("amnezia-awg", "wg show")
    result = parse_wg_show(raw)
    return {"status": "ok", "output": result}
