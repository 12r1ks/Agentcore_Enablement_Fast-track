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


def caller_customer_id(args: dict) -> str:
    """The signed-in customer. Added to the arguments by the agent runtime from its session state, never by the model."""
    customer_id = args.get("customer_id")
    if not isinstance(customer_id, str) or not customer_id:
        raise ToolError("CUSTOMER_CONTEXT_MISSING", "The session has no authenticated customer.")
    return customer_id


def required_string(args: dict, name: str, max_length: int = 64) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise invalid_parameter(name, "is required and must be a non-empty string")
    value = value.strip()
    if len(value) > max_length:
        raise invalid_parameter(name, f"must be at most {max_length} characters")
    return value
