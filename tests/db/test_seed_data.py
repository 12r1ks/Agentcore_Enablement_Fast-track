from decimal import Decimal

import pytest

from seed_data import load, refunds_from, replace_all


@pytest.fixture(scope="module")
def orders():
    return load("orders.json")


@pytest.fixture(scope="module")
def customers():
    return load("customers.json")


def test_money_is_loaded_as_decimal(orders):
    # DynamoDB rejects floats, so the seed must never contain them.
    assert all(isinstance(order["total"], Decimal) for order in orders)


def test_every_order_belongs_to_a_seeded_customer(orders, customers):
    customer_ids = {customer["customer_id"] for customer in customers}
    assert {order["customer_id"] for order in orders} <= customer_ids


def test_refunded_total_matches_recorded_refunds(orders):
    for order in orders:
        assert order["refunded_total"] == sum((r["amount"] for r in order["refunds"]), Decimal("0")), order["order_id"]


def test_refund_ledger_rows_point_back_to_their_order(orders):
    ledger = refunds_from(orders)
    assert len(ledger) == sum(len(order["refunds"]) for order in orders)
    assert len({row["idempotency_key"] for row in ledger}) == len(ledger)
    for row in ledger:
        order = next(o for o in orders if o["order_id"] == row["order_id"])
        assert row["currency"] == order["currency"]


class FakeTable:
    """Just enough of a boto3 Table for replace_all: paginated scan and a batch writer."""

    def __init__(self, keys, page_size=2):
        self.items = {key: {"order_id": key} for key in keys}
        self.page_size = page_size

    def scan(self, ExclusiveStartKey=None, **_):
        keys = sorted(self.items)
        start = keys.index(ExclusiveStartKey["order_id"]) + 1 if ExclusiveStartKey else 0
        page = keys[start:start + self.page_size]
        result = {"Items": [{"order_id": key} for key in page]}
        if start + self.page_size < len(keys):
            result["LastEvaluatedKey"] = {"order_id": page[-1]}
        return result

    def batch_writer(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def delete_item(self, Key):
        del self.items[Key["order_id"]]

    def put_item(self, Item):
        self.items[Item["order_id"]] = Item


def test_replace_all_removes_items_from_every_scan_page():
    table = FakeTable(["old-1", "old-2", "old-3", "old-4", "old-5"])
    replace_all(table, "order_id", [{"order_id": "123"}, {"order_id": "124"}])
    assert sorted(table.items) == ["123", "124"]
