from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .db import Base, engine

app = FastAPI(title="VisAI Assistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}


# Create tables on startup (simple MVP; swap to migrations later)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


