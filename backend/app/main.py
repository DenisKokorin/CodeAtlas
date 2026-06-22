from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes import external, repositories

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CodeAtlas API",
    version="0.1.0",
    description="Backend API for GitHub repository documentation generation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "CodeAtlas backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(repositories.router)
app.include_router(external.router)
