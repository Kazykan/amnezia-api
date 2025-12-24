from dotenv import load_dotenv

load_dotenv()

import asyncio
from services.stats.collector import collect_once
from services.stats.database import init_db
from fastapi import FastAPI


from routers import wg, auth

app = FastAPI(title="AmneziaWG REST API")
app.include_router(wg.router, prefix="/api/wg")
app.include_router(auth.router, prefix="/api/auth")


@app.on_event("startup")
async def start_collector():
    init_db()
    asyncio.create_task(collector_loop())


async def collector_loop():
    while True:
        try:
            collect_once()
        except Exception as e:
            print("Collector error:", e)
        await asyncio.sleep(10)  # интервал сбора
