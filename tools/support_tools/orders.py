from . import store
from .errors import ToolError, caller_customer_id, required_string

_SUMMARY_FIELDS = ("order_id", "status", "placed_at", "total", "currency")


def _summary(order: dict) -> dict:
    return {**{k: order[k] for k in _SUMMARY_FIELDS}, "items": [item["name"] for item in order["items"]]}


def list_orders(args: dict) -> dict:
    """Tool: a summary of all the customer's orders, newest first."""
    customer_id = caller_customer_id(args)
    return {"orders": [_summary(order) for order in store.list_orders(customer_id)]}


def get_order(args: dict) -> dict:
    """Tool: one of the customer's orders in full, with shipping, delay reason and refund history."""
    customer_id = caller_customer_id(args)
    order_id = required_string(args, "order_id")
    order = store.get_order(order_id)
    # Another customer's order is reported as not found, so its existence is not revealed.
    if order is None or order["customer_id"] != customer_id:
        raise ToolError("ORDER_NOT_FOUND", f"No order with ID '{order_id}' for this customer.", details={"order_id": order_id})
    return {"order": order}


def get_customer_info(args: dict) -> dict:
    """Tool: the signed-in customer's contact details and shipping address."""
    customer_id = caller_customer_id(args)
    customer = store.get_customer(customer_id)
    if customer is None:
        raise ToolError("CUSTOMER_NOT_FOUND", f"No customer with ID '{customer_id}'.", details={"customer_id": customer_id})
    return customer
