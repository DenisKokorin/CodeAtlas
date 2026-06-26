import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.auth import verify_docs_credentials
from app.database import Base, engine
from app.routes import auth, chat, export, external, repositories

Base.metadata.create_all(bind=engine)

basic_security = HTTPBasic()

app = FastAPI(
    title="CodeAtlas API",
    version="0.1.0",
    description="Backend API for GitHub repository documentation generation.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
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


def check_docs_basic_auth(
    credentials: HTTPBasicCredentials = Depends(basic_security),
):
    if not verify_docs_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid documentation credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@app.get("/", include_in_schema=False)
def root():
    return {"message": "CodeAtlas backend is running"}


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}


@app.get("/openapi.json", include_in_schema=False)
def protected_openapi(username: str = Depends(check_docs_basic_auth)):
    return JSONResponse(
        get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    )


@app.get("/docs", include_in_schema=False)
def protected_docs(username: str = Depends(check_docs_basic_auth)):
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
    )


if os.getenv("ENABLE_REDOC", "false").lower() == "true":
    from fastapi.openapi.docs import get_redoc_html

    @app.get("/redoc", include_in_schema=False)
    def protected_redoc(username: str = Depends(check_docs_basic_auth)):
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - ReDoc",
        )


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(repositories.router)
app.include_router(external.router)
app.include_router(export.router)
