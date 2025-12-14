from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from routers import wg, auth

app = FastAPI(title="AmneziaWG REST API")
app.include_router(wg.router, prefix="/api/wg")
app.include_router(auth.router, prefix="/api/auth")
