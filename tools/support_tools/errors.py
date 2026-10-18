from typing import Any


class ToolError(Exception):
    """An expected, structured failure returned to the agent instead of crashing the Lambda.

    `retryable` tells the caller whether repeating the same call may succeed.
    """

    def __init__(self, code: str, message: str, *, retryable: bool = False, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        error = {"code": self.code, "message": self.message, "retryable": self.retryable}
        if self.details:
            error["details"] = self.details
        return error


def invalid_parameter(name: str, reason: str) -> ToolError:
    return ToolError("INVALID_PARAMETER", f"Parameter '{name}' {reason}.", details={"parameter": name})


def required_string(args: dict, name: str, max_length: int = 64) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise invalid_parameter(name, "is required and must be a non-empty string")
    value = value.strip()
    if len(value) > max_length:
        raise invalid_parameter(name, f"must be at most {max_length} characters")
    return value
