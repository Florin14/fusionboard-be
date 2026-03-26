import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import timedelta

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import DataError, DBAPIError, IntegrityError, OperationalError, ProgrammingError, SQLAlchemyError

from extensions.auth_jwt import AuthJWT
from extensions.auth_jwt.exceptions import (
    AuthJWTException,
    MissingTokenError,
    RevokedTokenError,
    InvalidHeaderError,
    JWTDecodeError,
    AccessTokenRequired,
    RefreshTokenRequired,
    FreshTokenRequired,
    CSRFError,
)
from extensions.sqlalchemy import init_db, DBSessionMiddleware, SessionLocal
from modules import authRouter, footballRouter, platformRouter, samplePlatformRouter, jobTrackerRouter, smartTasksRouter, dailyBriefRouter, websocketRouter, webhookRouter
from modules.user.models.user_model import UserModel
from modules.admin.models.admin_model import AdminModel
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from project_helpers.responses import ErrorResponse
from project_helpers.schemas import ErrorSchema


def _safe_exc_message(exc: Exception) -> str:
    if hasattr(exc, "detail") and getattr(exc, "detail"):
        return str(getattr(exc, "detail"))
    return str(exc) if str(exc) else exc.__class__.__name__


def _validation_fields(exc: RequestValidationError) -> list[str]:
    fields: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", []) if p is not None)
        msg = err.get("msg")
        if loc and msg:
            fields.append(f"{loc}: {msg}")
        elif loc:
            fields.append(loc)
        elif msg:
            fields.append(msg)
    return fields


async def error_exception_handler(request: Request, exc: ErrorException):
    return ErrorResponse(
        exc.error,
        statusCode=getattr(exc, "statusCode", 500),
        message=getattr(exc, "message", None),
        fields=getattr(exc, "fields", None),
    )


async def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    status_code = getattr(exc, "status_code", 401) or 401
    if isinstance(exc, MissingTokenError):
        error = Error.TOKEN_NOT_FOUND
    elif isinstance(exc, RevokedTokenError):
        error = Error.REVOKED_TOKEN
    elif isinstance(exc, FreshTokenRequired):
        error = Error.FRESH_TOKEN_REQUIRED
    elif isinstance(exc, (AccessTokenRequired, RefreshTokenRequired, InvalidHeaderError, JWTDecodeError, CSRFError)):
        error = Error.INVALID_TOKEN
    else:
        error = Error.INVALID_TOKEN
    return ErrorResponse(error, statusCode=status_code, message=getattr(exc, "message", None))


async def http_exception_handler(request: Request, exc: HTTPException):
    status_code = exc.status_code or 500
    if status_code == 400:
        error = Error.INVALID_JSON_FORMAT
    elif status_code == 401:
        error = Error.INVALID_TOKEN
    elif status_code == 422:
        error = Error.INVALID_QUERY_FORMAT
    else:
        error = Error.SERVER_ERROR
    return ErrorResponse(error, statusCode=status_code, message=_safe_exc_message(exc))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return ErrorResponse(
        Error.INVALID_QUERY_FORMAT,
        statusCode=422,
        message="Validation error",
        fields=_validation_fields(exc),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    message = _safe_exc_message(exc)
    if isinstance(exc, DBAPIError) and getattr(exc, "orig", None):
        message = _safe_exc_message(exc.orig)
    if isinstance(exc, IntegrityError):
        error = Error.DB_INSERT_ERROR
    elif isinstance(exc, DataError):
        error = Error.DB_INSERT_ERROR
    elif isinstance(exc, (OperationalError, ProgrammingError, DBAPIError)):
        error = Error.DB_ACCESS_ERROR
    else:
        error = Error.DB_ACCESS_ERROR
    logging.exception("SQLAlchemy error during request")
    return ErrorResponse(error, statusCode=500, message=message)


async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled exception during request")
    return ErrorResponse(Error.SERVER_ERROR, statusCode=500, message=_safe_exc_message(exc))


def parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _get_jwt_config() -> list[tuple[str, str | list[str] | None]]:
    def _parse_bool(value: str | None) -> bool | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        return None

    token_location = os.getenv("AUTHJWT_TOKEN_LOCATION")
    if token_location:
        locations = [item.strip().lower() for item in token_location.split(",") if item.strip()]
    else:
        locations = None
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    is_production = app_env in {"production", "prod"}
    cookie_samesite = os.getenv("AUTHJWT_COOKIE_SAMESITE")
    if cookie_samesite:
        cookie_samesite = cookie_samesite.strip().lower()
    cookie_secure = _parse_bool(os.getenv("AUTHJWT_COOKIE_SECURE"))
    cookie_domain = os.getenv("AUTHJWT_COOKIE_DOMAIN")
    cookie_csrf_protect = _parse_bool(os.getenv("AUTHJWT_COOKIE_CSRF_PROTECT"))
    allow_header_fallback = _parse_bool(os.getenv("AUTHJWT_ALLOW_HEADER_FALLBACK"))
    if allow_header_fallback is None:
        allow_header_fallback = True
    if locations and "cookies" in locations:
        if allow_header_fallback and "headers" not in locations:
            locations.append("headers")
        if cookie_samesite is None:
            cookie_samesite = "none" if is_production else "lax"
        if cookie_secure is None:
            cookie_secure = is_production
    config: list[tuple[str, str | list[str] | bool | None]] = [
        ("AUTHJWT_SECRET_KEY", os.getenv("AUTHJWT_SECRET_KEY")),
        ("AUTHJWT_TOKEN_LOCATION", locations),
    ]
    if cookie_samesite is not None:
        config.append(("AUTHJWT_COOKIE_SAMESITE", cookie_samesite))
    if cookie_secure is not None:
        config.append(("AUTHJWT_COOKIE_SECURE", cookie_secure))
    if cookie_domain:
        config.append(("AUTHJWT_COOKIE_DOMAIN", cookie_domain))
    if cookie_csrf_protect is not None:
        config.append(("AUTHJWT_COOKIE_CSRF_PROTECT", cookie_csrf_protect))
    config.append(("AUTHJWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=8)))
    config.append(("AUTHJWT_REFRESH_TOKEN_EXPIRES", timedelta(hours=8)))
    return config


def _ensure_default_admin_user(db: SessionLocal) -> None:
    default_email = "admin@fusionboard.io"
    exists = db.query(UserModel).filter(UserModel.email == default_email).first()
    if exists:
        return
    admin = AdminModel(
        name="FusionBoard Admin",
        email=default_email,
        password="FusionAdmin2026!",
    )
    db.add(admin)
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        format="%(asctime)s - [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    init_db()

    db = SessionLocal()
    try:
        _ensure_default_admin_user(db)
    finally:
        db.close()

    # Register platform services
    from modules.football_tracking.register import register_football_service
    from modules.sample_platform.register import register_sample_service
    register_football_service()
    register_sample_service()

    from modules.job_tracker.register import register_job_tracker_service
    from modules.smart_tasks.register import register_smart_tasks_service
    register_job_tracker_service()
    register_smart_tasks_service()

    from modules.platform_registry.service_registry import registry
    logging.info("FusionBoard API started - %d platform(s) registered.", len(registry.services))

    # Start football change detector
    from modules.football_tracking.change_detector import start_change_detector, stop_change_detector
    change_detector_task = asyncio.create_task(start_change_detector(interval_seconds=300))

    yield

    stop_change_detector()
    change_detector_task.cancel()
    logging.info("FusionBoard API shutting down.")


# ─── Create the app ──────────────────────────────────────────────────────
api = FastAPI(
    exception_handlers={
        ErrorException: error_exception_handler,
        AuthJWTException: authjwt_exception_handler,
        HTTPException: http_exception_handler,
        RequestValidationError: validation_exception_handler,
        SQLAlchemyError: sqlalchemy_exception_handler,
        Exception: unhandled_exception_handler,
    },
    title="FusionBoard API",
    description="Unified dashboard API for all your platform services",
    version="1.0.0",
    lifespan=lifespan,
)

AuthJWT.load_config(_get_jwt_config)
_allowed_origins = parse_allowed_origins()


@api.middleware("http")
async def force_cors_headers(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin:
        if "*" in _allowed_origins or origin in _allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


api.add_middleware(DBSessionMiddleware)
api.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/health")
def health():
    return {"status": "ok", "service": "fusionboard"}


# ─── Include routers ─────────────────────────────────────────────────────
common_responses = {
    500: {"model": ErrorSchema},
    401: {"model": ErrorSchema},
    422: {"model": ErrorSchema},
    404: {"model": ErrorSchema},
}
for router in (authRouter, footballRouter, platformRouter, samplePlatformRouter, jobTrackerRouter, smartTasksRouter, dailyBriefRouter):
    api.include_router(router, responses=common_responses)

# WebSocket router (no common_responses since WS doesn't use HTTP responses)
api.include_router(websocketRouter)

# Webhook router (uses shared secret auth, not JWT)
api.include_router(webhookRouter)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
    uvicorn.run("services.run_api:api", host="0.0.0.0", port=port, reload=True, app_dir="src")


if __name__ == "__main__":
    main()
