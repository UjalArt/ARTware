import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, SessionLocal
import models
from seed import seed_database
from services.broker import start_broker
from services.mqtt_worker import start_worker
from routers import auth, dashboard, gateways, devices, profiles, rules, users, broker, decoders

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

# Create all tables
models.Base.metadata.create_all(bind=engine)

# Seed demo data
with SessionLocal() as db:
    seed_database(db)

app = FastAPI(title="ARTware", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(gateways.router)
app.include_router(devices.router)
app.include_router(profiles.router)
app.include_router(rules.router)
app.include_router(users.router)
app.include_router(broker.router)
app.include_router(decoders.router)

# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", include_in_schema=False)
@app.get("/{path:path}", include_in_schema=False)
def serve_spa(path: str = ""):
    return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.on_event("startup")
def on_startup():
    start_broker()   # embedded MQTT broker on port 1883 / 8083
    start_worker()   # paho subscriber + demo publisher


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
