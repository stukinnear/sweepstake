import json
from datetime import date, datetime
from typing import Optional, Type, TypeVar, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from fastapi.responses import StreamingResponse


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

T = TypeVar("T", bound=DeclarativeBase)


def all_optional(cls):
    """Class decorator that makes every field on a SQLModel/Pydantic model Optional with default None."""
    # Update annotations at the class level so SQLModel/Pydantic picks them up on rebuild
    annotations = {}
    for name, field_info in cls.model_fields.items():
        annotations[name] = Optional[field_info.annotation]
        field_info.default = None
    cls.__annotations__.update(annotations)
    cls.model_rebuild(force=True)
    return cls


async def stream_model_results(
    db: AsyncSession,
    query,
    batch_size: int = 1,
) -> AsyncGenerator[str, None]:
    """
    Generic async generator for streaming database results as newline-delimited JSON.
    
    Args:
        db: AsyncSession database connection
        query: SQLAlchemy select query
        batch_size: Number of items to batch before yielding (default 1 for streaming)
    
    Yields:
        JSON strings, one per line
    """
    result = await db.execute(query)
    
    for item in result.scalars():
        # Convert ORM object to dict
        item_dict = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        yield json.dumps(item_dict, default=_json_serial) + "\n"


def create_stream_response(
    generator: AsyncGenerator[str, None],
    media_type: str = "application/x-ndjson",
) -> StreamingResponse:
    """
    Create a StreamingResponse from an async generator.
    
    Args:
        generator: Async generator yielding JSON strings
        media_type: Content-type header (default: newline-delimited JSON)
    
    Returns:
        FastAPI StreamingResponse
    """
    return StreamingResponse(generator, media_type=media_type)
