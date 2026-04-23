"""Shared API error response helpers."""

import logging
from typing import Optional

from fastapi.responses import JSONResponse


def api_error(
    logger: logging.Logger,
    user_message: str,
    *,
    status_code: int,
    exc: Optional[Exception] = None,
    context: Optional[str] = None,
) -> JSONResponse:
    """Log an exception with context and return a JSON error payload."""
    if exc is not None:
        if context:
            logger.exception("%s: %s", context, exc)
        else:
            logger.exception("Unhandled API exception: %s", exc)
    return JSONResponse(content={"error": user_message}, status_code=status_code)
