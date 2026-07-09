"""
YahConect — ponto de entrada da API.

Rodar com:
    uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI

from app.database import init_db
from app.webhook import router as webhook_router
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Bot/ETL para coletar eventos de mensagens (WhatsApp e outras origens) "
                 "e alimentar dashboards de BI/People Analytics.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


app.include_router(webhook_router)
