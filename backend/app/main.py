from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .config import settings
from .database import Base, SessionLocal, engine
from .exceptions import register_exception_handlers
from .models.user import User
from .schemas.user import UserCreate
from .services.user_service import ConflictError, UserService

def create_initial_admin() -> None:
    if not (
        settings.initial_admin_username
        and settings.initial_admin_email
        and settings.initial_admin_password
    ):
        return

    db = SessionLocal()
    try:
        if db.query(User).filter(User.is_admin.is_(True)).first():
            return

        service = UserService(db)
        admin = UserCreate(
            username=settings.initial_admin_username,
            email=settings.initial_admin_email,
            password=settings.initial_admin_password,
        )
        try:
            service.create_user(admin, is_admin=True)
        except ConflictError:
            return
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    create_initial_admin()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="OIM Backend",
        description="FastAPI backend with MySQL and dynamic captcha",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = perf_counter()
        response = await call_next(request)
        process_time_ms = (perf_counter() - start_time) * 1000
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
        if process_time_ms > 500:
            print(f"Slow request {request.method} {request.url.path}: {process_time_ms:.2f}ms")
        return response

    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
