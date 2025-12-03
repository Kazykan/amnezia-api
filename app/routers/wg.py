from fastapi import APIRouter

from app.services.docker import exec_in_container

router = APIRouter()


@router.get("/clients")
def list_clients():
    """
    Получить список клиентов из AmneziaWG
    """
    result = exec_in_container("amnezia-awg", "wg show")
    return {"status": "ok", "output": result}
