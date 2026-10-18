"""DynamoDB access for the order and refund tools. Table names match db/infra/data.yaml."""

from functools import lru_cache

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from .errors import ToolError

ORDERS_TABLE = "CustomerSupport-orders"
ORDERS_BY_CUSTOMER_INDEX = "customer_id-index"
CUSTOMERS_TABLE = "CustomerSupport-customers"
REFUNDS_TABLE = "CustomerSupport-refunds"

# "standard" mode retries throttling and 5xx errors with exponential backoff and jitter.
# Timeouts stay well under the 10 s Lambda timeout, so a slow call fails as a tool error.
_CONFIG = Config(connect_timeout=2, read_timeout=3, retries={"mode": "standard", "max_attempts": 3})

_RETRYABLE_CODES = {
    "ProvisionedThroughputExceededException",
    "ThrottlingException",
    "RequestLimitExceeded",
    "InternalServerError",
    "ServiceUnavailable",
    "TransactionConflict",
}


class RefundAlreadyRecorded(Exception):
    """Another request wrote the same idempotency key first."""


class OrderChanged(Exception):
    """The order's refunded total changed after it was read."""


@lru_cache(maxsize=1)
def _dynamodb():
    return boto3.resource("dynamodb", config=_CONFIG)


def _backend_error(error: Exception) -> ToolError:
    code = error.response["Error"]["Code"] if isinstance(error, ClientError) else type(error).__name__
    retryable = isinstance(error, BotoCoreError) or code in _RETRYABLE_CODES
    return ToolError("BACKEND_ERROR", "The order database could not complete the request.", retryable=retryable, details={"cause": code})


def _get(table: str, key: dict) -> dict | None:
    try:
        return _dynamodb().Table(table).get_item(Key=key, ConsistentRead=True).get("Item")
    except (BotoCoreError, ClientError) as error:
        raise _backend_error(error) from error


def get_order(order_id: str) -> dict | None:
    return _get(ORDERS_TABLE, {"order_id": order_id})


def list_orders(customer_id: str) -> list[dict]:
    """A customer's orders, newest first. Index reads are eventually consistent, so a just-written change may lag briefly."""
    query = {
        "IndexName": ORDERS_BY_CUSTOMER_INDEX,
        "KeyConditionExpression": Key("customer_id").eq(customer_id),
        "ScanIndexForward": False,
    }
    orders = []
    try:
        while True:
            page = _dynamodb().Table(ORDERS_TABLE).query(**query)
            orders += page["Items"]
            if "LastEvaluatedKey" not in page:
                return orders
            query["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    except (BotoCoreError, ClientError) as error:
        raise _backend_error(error) from error


def get_customer(customer_id: str) -> dict | None:
    return _get(CUSTOMERS_TABLE, {"customer_id": customer_id})


def get_refund(idempotency_key: str) -> dict | None:
    return _get(REFUNDS_TABLE, {"idempotency_key": idempotency_key})


def record_refund(order: dict, refund: dict, new_status: str) -> None:
    """Write the refund to the ledger and the order in one transaction, so neither can exist without the other.

    The ledger write fails if the idempotency key exists; the order write fails if another refund
    changed refunded_total since `order` was read.
    """
    entry = {k: refund[k] for k in ("refund_id", "idempotency_key", "amount", "reason", "created_at")}
    try:
        _dynamodb().meta.client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": REFUNDS_TABLE,
                        "Item": refund,
                        "ConditionExpression": "attribute_not_exists(idempotency_key)",
                    }
                },
                {
                    "Update": {
                        "TableName": ORDERS_TABLE,
                        "Key": {"order_id": order["order_id"]},
                        "UpdateExpression": "SET refunded_total = :new_total, #status = :status, refunds = list_append(refunds, :entry)",
                        "ConditionExpression": "refunded_total = :expected",
                        "ExpressionAttributeNames": {"#status": "status"},
                        "ExpressionAttributeValues": {
                            ":new_total": order["refunded_total"] + refund["amount"],
                            ":status": new_status,
                            ":entry": [entry],
                            ":expected": order["refunded_total"],
                        },
                    }
                },
            ]
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "TransactionCanceledException":
            raise _backend_error(error) from error
        ledger, order_update = [reason.get("Code") for reason in error.response.get("CancellationReasons", [{}, {}])]
        if ledger == "ConditionalCheckFailed":
            raise RefundAlreadyRecorded from error
        if order_update == "ConditionalCheckFailed":
            raise OrderChanged from error
        raise _backend_error(error) from error
    except BotoCoreError as error:
        raise _backend_error(error) from error
