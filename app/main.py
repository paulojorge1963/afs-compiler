from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import entities, financial_years, imports

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="AFS Compiler")

app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

app.include_router(entities.router)
app.include_router(financial_years.router)
app.include_router(imports.router)


@app.on_event("startup")
def on_startup():
    init_db()
