import uuid
from datetime import UTC, datetime
from decimal import Decimal

from . import store
from .errors import ToolError, invalid_parameter, required_string

# Matches the Refund Policy in lumora-company-info.md. The Gateway's Cedar policy enforces the
# same limit before this code runs; checking here too keeps the backend safe on its own.
AUTO_APPROVAL_LIMIT = Decimal("1000")


def _amount(args: dict) -> Decimal:
    value = args.get("amount")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise invalid_parameter("amount", "is required and must be a number")
    amount = Decimal(str(value))
    if not amount.is_finite() or amount <= 0:
        raise invalid_parameter("amount", "must be greater than 0")
    if amount != amount.quantize(Decimal("0.01")):
        raise invalid_parameter("amount", "must have at most 2 decimal places")
    return amount


def _replay(existing: dict, order_id: str, amount: Decimal) -> dict:
    """Return the refund already stored under this key, unless the key is being reused for a different refund."""
    if existing["order_id"] != order_id or existing["amount"] != amount:
        raise ToolError(
            "IDEMPOTENCY_KEY_REUSED",
            "This idempotency key was already used for a different refund. Use a new key for a new refund.",
            details={"idempotency_key": existing["idempotency_key"]},
        )
    return {"refund": existing, "duplicate": True}


def refund_customer(args: dict) -> dict:
    """Tool: refund part or all of an order. Retrying with the same idempotency_key returns the original refund."""
    order_id = required_string(args, "order_id")
    idempotency_key = required_string(args, "idempotency_key", max_length=128)
    reason = required_string(args, "reason", max_length=500)
    amount = _amount(args)

    if amount > AUTO_APPROVAL_LIMIT:
        raise ToolError(
            "REFUND_REQUIRES_APPROVAL",
            f"Refunds over {AUTO_APPROVAL_LIMIT} EUR need review by a human support manager.",
            details={"limit": AUTO_APPROVAL_LIMIT},
        )

    existing = store.get_refund(idempotency_key)
    if existing is not None:
        return _replay(existing, order_id, amount)

    order = store.get_order(order_id)
    if order is None:
        raise ToolError("ORDER_NOT_FOUND", f"No order with ID '{order_id}'.", details={"order_id": order_id})
    remaining = order["total"] - order["refunded_total"]
    if amount > remaining:
        raise ToolError(
            "REFUND_EXCEEDS_REMAINING",
            f"The refund is larger than the {remaining} {order['currency']} still refundable on this order.",
            details={"remaining": remaining},
        )

    refund = {
        "idempotency_key": idempotency_key,
        "refund_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
        "order_id": order_id,
        "amount": amount,
        "currency": order["currency"],
        "reason": reason,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    new_status = "REFUNDED" if amount == remaining else "PARTIALLY_REFUNDED"
    try:
        store.record_refund(order, refund, new_status)
    except store.RefundAlreadyRecorded:
        # A concurrent retry with the same key won the race; return its result.
        return _replay(store.get_refund(idempotency_key), order_id, amount)
    except store.OrderChanged:
        raise ToolError("ORDER_CHANGED", "The order was updated by another request. Retry the refund.", retryable=True) from None
    return {"refund": refund, "duplicate": False, "order_status": new_status}
