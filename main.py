from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import engine, Base
import models  # noqa: F401 — registers all models with Base
from routers import jobs, cv, contacts, messages
import migrations

Base.metadata.create_all(bind=engine)
migrations.run()

app = FastAPI(title="Job Hunter", version="1.0.0")

app.include_router(jobs.router)
app.include_router(cv.router)
app.include_router(contacts.router)
app.include_router(messages.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
