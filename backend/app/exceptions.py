from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .services.base_service import ConflictError, NotFoundError


async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ConflictError, conflict_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
