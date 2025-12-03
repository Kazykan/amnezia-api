from fastapi import FastAPI

from routers import wg, auth

app = FastAPI(title="AmneziaWG REST API")
app.include_router(wg.router, prefix="/api/wg")
app.include_router(auth.router, prefix="/api/auth")
