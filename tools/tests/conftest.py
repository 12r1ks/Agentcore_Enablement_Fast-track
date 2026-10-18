import copy
from decimal import Decimal

import pytest

from support_tools import store

ORDER = {
    "order_id": "123",
    "customer_id": "CUST-001",
    "status": "DELAYED",
    "placed_at": "2026-10-05",
    "currency": "EUR",
    "items": [{"sku": "LUM-THM-02", "name": "Lumora Thermo Smart Thermostat", "quantity": 1, "unit_price": Decimal("129.00")}],
    "total": Decimal("163.99"),
    "refunded_total": Decimal("0"),
    "refunds": [],
}
OLDER_ORDER = {**ORDER, "order_id": "124", "status": "DELIVERED", "placed_at": "2026-09-20", "total": Decimal("307.00")}
OTHER_CUSTOMERS_ORDER = {**ORDER, "order_id": "125", "customer_id": "CUST-002"}
CUSTOMER = {"customer_id": "CUST-001", "name": "Emma de Vries", "email": "emma.devries@example.com"}


class FakeStore:
    """In-memory stand-in for the DynamoDB tables, with the same conditional-write rules as store.record_refund."""

    def __init__(self):
        self.orders = {o["order_id"]: copy.deepcopy(o) for o in (ORDER, OLDER_ORDER, OTHER_CUSTOMERS_ORDER)}
        self.customers = {CUSTOMER["customer_id"]: dict(CUSTOMER)}
        self.refunds = {}

    def record_refund(self, order, refund, new_status):
        if refund["idempotency_key"] in self.refunds:
            raise store.RefundAlreadyRecorded
        stored = self.orders[order["order_id"]]
        if stored["refunded_total"] != order["refunded_total"]:
            raise store.OrderChanged
        self.refunds[refund["idempotency_key"]] = refund
        stored["refunded_total"] += refund["amount"]
        stored["status"] = new_status
        stored["refunds"].append(refund)

    def list_orders(self, customer_id):
        mine = [copy.deepcopy(o) for o in self.orders.values() if o["customer_id"] == customer_id]
        return sorted(mine, key=lambda o: o["placed_at"], reverse=True)


@pytest.fixture
def db(monkeypatch) -> FakeStore:
    fake = FakeStore()
    monkeypatch.setattr(store, "get_order", lambda order_id: copy.deepcopy(fake.orders.get(order_id)))
    monkeypatch.setattr(store, "list_orders", fake.list_orders)
    monkeypatch.setattr(store, "get_customer", lambda customer_id: fake.customers.get(customer_id))
    monkeypatch.setattr(store, "get_refund", lambda key: fake.refunds.get(key))
    monkeypatch.setattr(store, "record_refund", fake.record_refund)
    return fake
