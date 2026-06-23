from functools import wraps
from typing import Any, Callable, TypeVar

from kiki.errors import KikiError

F = TypeVar("F", bound=Callable[..., dict[str, Any]])


def tool_safe(fn: F) -> F:
    """Return KikiError payloads instead of raising through MCP."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except KikiError as exc:
            return exc.to_dict()

    return wrapper  # type: ignore[return-value]
