from decimal import Decimal
from types import SimpleNamespace

import pytest

from support_tools import store

LEDGER_ROW = {"idempotency_key": "CUST-001#operation-123", "refund_id": "REF-1", "order_id": "123"}


class FakeDynamoDB:
    """Records the calls store makes, with one ledger row stored under its scoped key."""

    def __init__(self):
        self.keys_read = []
        self.transactions = []
        self.meta = SimpleNamespace(client=SimpleNamespace(transact_write_items=lambda **kwargs: self.transactions.append(kwargs)))

    def Table(self, name):
        return SimpleNamespace(get_item=self._get_item)

    def _get_item(self, Key, **_):
        self.keys_read.append(Key)
        return {"Item": dict(LEDGER_ROW)} if Key == {"idempotency_key": LEDGER_ROW["idempotency_key"]} else {}


@pytest.fixture
def dynamodb(monkeypatch) -> FakeDynamoDB:
    fake = FakeDynamoDB()
    monkeypatch.setattr(store, "_dynamodb", lambda: fake)
    return fake


def test_refund_is_looked_up_under_the_customers_scoped_key(dynamodb):
    refund = store.get_refund("CUST-001", "operation-123")
    assert dynamodb.keys_read == [{"idempotency_key": "CUST-001#operation-123"}]
    # The caller gets back the key it sent, not the internal ledger format.
    assert refund["idempotency_key"] == "operation-123"


def test_another_customers_key_is_not_found(dynamodb):
    assert store.get_refund("CUST-002", "operation-123") is None


def test_refund_is_written_under_the_customers_scoped_key(dynamodb):
    order = {"order_id": "123", "customer_id": "CUST-001", "refunded_total": Decimal("0")}
    refund = {
        "idempotency_key": "operation-123",
        "refund_id": "REF-1",
        "order_id": "123",
        "amount": Decimal("50"),
        "reason": "Faulty item",
        "created_at": "2026-10-19T10:00:00+00:00",
    }
    store.record_refund(order, refund, "PARTIALLY_REFUNDED")
    [transaction] = dynamodb.transactions
    ledger_put, order_update = transaction["TransactItems"]
    assert ledger_put["Put"]["Item"]["idempotency_key"] == "CUST-001#operation-123"
    # The order's own refund history keeps the key the customer used.
    assert order_update["Update"]["ExpressionAttributeValues"][":entry"][0]["idempotency_key"] == "operation-123"
