from fastapi import Request
from fastapi.responses import JSONResponse
from http import HTTPStatus


class CustomError(Exception):
    """Application-level custom error for domain failures."""

    def __init__(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status_code = status_code


async def custom_error_handler(request: Request, exc: CustomError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc)},
    )
