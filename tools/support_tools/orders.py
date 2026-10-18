from . import store
from .errors import ToolError, required_string


def get_order_status(args: dict) -> dict:
    """Tool: return an order with its status, shipping and delay details, and refund history."""
    order_id = required_string(args, "order_id")
    order = store.get_order(order_id)
    if order is None:
        raise ToolError("ORDER_NOT_FOUND", f"No order with ID '{order_id}'.", details={"order_id": order_id})
    return order


def get_customer_info(args: dict) -> dict:
    """Tool: return a customer's contact details and shipping address."""
    customer_id = required_string(args, "customer_id")
    customer = store.get_customer(customer_id)
    if customer is None:
        raise ToolError("CUSTOMER_NOT_FOUND", f"No customer with ID '{customer_id}'.", details={"customer_id": customer_id})
    return customer
