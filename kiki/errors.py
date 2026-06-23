from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    QUERY_TOO_BROAD = "QUERY_TOO_BROAD"
    CONFIRM_DOWNLOAD_REQUIRED = "CONFIRM_DOWNLOAD_REQUIRED"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    INVALID_SEQ_LENGTH_RANGE = "INVALID_SEQ_LENGTH_RANGE"
    INVALID_DATE_FORMAT = "INVALID_DATE_FORMAT"
    PRESET_NOT_FOUND = "PRESET_NOT_FOUND"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    NOT_FOUND = "NOT_FOUND"


class KikiError(Exception):
    """Agent-actionable error with a stable machine-readable code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "success": False,
            "status": "error",
            "error": {
                "code": self.code.value,
                "message": self.message,
            },
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload
