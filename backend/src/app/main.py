import os
from fastapi import FastAPI
from dotenv import load_dotenv
from .routes import profile as profile_routes
from .routes import exa as exa_routes


load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)

app = FastAPI(title="InnerNets Backend", version="0.1.0")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def root():
    return {
        "service": "innernets-backend",
        "version": "0.1.0",
        "status": "ready",
    }


app.include_router(profile_routes.router)
app.include_router(exa_routes.router)
