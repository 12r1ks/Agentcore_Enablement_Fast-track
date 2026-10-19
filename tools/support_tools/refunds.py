import uuid
from datetime import UTC, datetime
from decimal import Decimal

from . import store
from .errors import ToolError, caller_customer_id, invalid_parameter, required_string

# Matches the Refund Policy in lumora-company-info.md. The Gateway's Cedar policy enforces it per
# refund before this code runs; this code also enforces it per order, which Cedar can't (it doesn't see past refunds).
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


def _status_after_refund(status: str, fully_refunded: bool) -> str:
    """Refunding a delayed order in full cancels it; a partial refund (e.g. the shipping fee) keeps it DELAYED."""
    if status == "DELAYED":
        return "CANCELLED" if fully_refunded else "DELAYED"
    return "REFUNDED" if fully_refunded else "PARTIALLY_REFUNDED"


def refund_customer(args: dict) -> dict:
    """Tool: refund part or all of an order. Retrying with the same idempotency_key returns the original refund."""
    customer_id = caller_customer_id(args)
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

    # Ownership is checked before the idempotency replay, so another customer's refund
    # can't be read back by sending their order ID and key.
    order = store.get_order(order_id)
    if order is None or order["customer_id"] != customer_id:
        raise ToolError("ORDER_NOT_FOUND", f"No order with ID '{order_id}' for this customer.", details={"order_id": order_id})

    existing = store.get_refund(customer_id, idempotency_key)
    if existing is not None:
        return _replay(existing, order_id, amount)

    # Checked after the replay, so retrying the refund that cancelled a delayed order still returns it.
    if order["status"] == "CANCELLED":
        raise ToolError(
            "ORDER_CANCELLED",
            "This order was cancelled, and cancelling already refunded its payment automatically.",
            details={"order_id": order_id},
        )

    # The limit counts all refunds on the order, so splitting a large refund into smaller ones can't get around it.
    if order["refunded_total"] + amount > AUTO_APPROVAL_LIMIT:
        raise ToolError(
            "REFUND_REQUIRES_APPROVAL",
            f"Refunds over {AUTO_APPROVAL_LIMIT} EUR in total on one order need review by a human support manager.",
            details={"limit": AUTO_APPROVAL_LIMIT, "already_refunded": order["refunded_total"]},
        )

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
    new_status = _status_after_refund(order["status"], fully_refunded=amount == remaining)
    try:
        store.record_refund(order, refund, new_status)
    except store.RefundAlreadyRecorded:
        # A concurrent retry with the same key won the race; return its result.
        return _replay(store.get_refund(customer_id, idempotency_key), order_id, amount)
    except store.OrderChanged:
        raise ToolError("ORDER_CHANGED", "The order was updated by another request. Retry the refund.", retryable=True) from None
    return {"refund": refund, "duplicate": False, "order_status": new_status}
