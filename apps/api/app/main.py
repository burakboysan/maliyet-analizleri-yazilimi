import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.db import get_connection, get_postgres_pool
from app.core.settings import get_allowed_origin_regex, get_allowed_origins, get_settings
from app.routers import admin, auth, documents, fixed_costs, health, leave, materials, mobile_compat, modules, products, selection_wizard


settings = get_settings()
is_dev = settings.api_env == "dev"
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bomaksan Maliyet API",
    version="0.1.0",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
    openapi_url="/openapi.json" if is_dev else None,
)


class JsonUnhandledExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled API error: %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={"detail": "Sunucu beklenmeyen bir hata döndürdü. Lütfen daha sonra tekrar deneyin."},
            )


app.add_middleware(JsonUnhandledExceptionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_origin_regex=get_allowed_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def warm_up_database() -> None:
    try:
        get_postgres_pool()
        connection_iter = get_connection()
        try:
            connection = next(connection_iter)
            from app.core.account_security import ensure_account_security_schema

            ensure_account_security_schema(connection)
        finally:
            connection_iter.close()
    except Exception:
        logger.exception("Database warmup failed")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(mobile_compat.router)
app.include_router(modules.router)
app.include_router(leave.router)
app.include_router(materials.router)
app.include_router(products.router)
app.include_router(admin.router)
app.include_router(fixed_costs.router)
app.include_router(mobile_compat.tail_router)
app.include_router(selection_wizard.router)
app.include_router(documents.router)
