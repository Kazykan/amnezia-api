from fastapi import FastAPI

from routers import wg

app = FastAPI(title="AmneziaWG REST API")
app.include_router(wg.router, prefix="/api/wg")
