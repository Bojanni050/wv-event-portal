from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import logging  # noqa: E402
import os  # noqa: E402

from fastapi import APIRouter, FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from database import engine  # noqa: E402
from routes import account, admin, auth, events, files, integrations, invitations, messages, music, rsvp, timeline  # noqa: E402
from seed import run_seed  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(title="White Vision Portal API", version="1.0.0")
api = APIRouter(prefix="/api")
for module in (auth, account, events, messages, music, timeline, files, invitations, rsvp, admin, integrations):
    api.include_router(module.router)


@api.get("/")
async def root():
    return {"service": "white-vision-portal", "status": "ok"}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ["CORS_ORIGINS"].split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await run_seed()


@app.on_event("shutdown")
async def shutdown_db_client():
    await engine.dispose()
