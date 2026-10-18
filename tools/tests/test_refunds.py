from decimal import Decimal

import pytest

from support_tools import store
from support_tools.errors import ToolError
from support_tools.refunds import refund_customer


def refund_args(**overrides) -> dict:
    # customer_id is added by the agent's CustomerContextHook, never by the model.
    return {
        "customer_id": "CUST-001",
        "order_id": "123",
        "amount": 50,
        "reason": "Faulty item",
        "idempotency_key": "operation-123",
        **overrides,
    }


def error_code(args) -> str:
    with pytest.raises(ToolError) as raised:
        refund_customer(args)
    return raised.value.code


def test_partial_refund_updates_order(db):
    result = refund_customer(refund_args())
    assert result["duplicate"] is False
    assert result["order_status"] == "PARTIALLY_REFUNDED"
    assert result["refund"]["amount"] == Decimal("50")
    assert db.orders["123"]["refunded_total"] == Decimal("50")
    assert len(db.orders["123"]["refunds"]) == 1


def test_refunding_the_remainder_marks_order_refunded(db):
    assert refund_customer(refund_args(amount=163.99))["order_status"] == "REFUNDED"


def test_retry_with_same_key_returns_original_refund(db):
    first = refund_customer(refund_args())
    retry = refund_customer(refund_args())
    assert retry["duplicate"] is True
    assert retry["refund"]["refund_id"] == first["refund"]["refund_id"]
    assert db.orders["123"]["refunded_total"] == Decimal("50")
    assert len(db.refunds) == 1


def test_same_key_for_a_different_refund_is_rejected(db):
    refund_customer(refund_args())
    assert error_code(refund_args(amount=60)) == "IDEMPOTENCY_KEY_REUSED"


def test_concurrent_retry_that_loses_the_race_returns_the_winner(db, monkeypatch):
    # The key is free when checked, but a concurrent request writes it before our transaction.
    winner = refund_customer(refund_args())
    lookups = iter([None, winner["refund"]])
    monkeypatch.setattr(store, "get_refund", lambda key: next(lookups))
    retry = refund_customer(refund_args())
    assert retry == {"refund": winner["refund"], "duplicate": True}


def test_order_changed_concurrently_is_retryable(db, monkeypatch):
    def changed(*_):
        raise store.OrderChanged

    monkeypatch.setattr(store, "record_refund", changed)
    with pytest.raises(ToolError) as raised:
        refund_customer(refund_args())
    assert raised.value.code == "ORDER_CHANGED"
    assert raised.value.retryable


def test_over_approval_limit_is_denied_before_touching_data(db):
    assert error_code(refund_args(amount=1000.01)) == "REFUND_REQUIRES_APPROVAL"
    assert db.refunds == {}


def test_exactly_the_limit_reaches_the_order_checks(db):
    # 1000 is allowed by policy; it then fails only because order 123 is smaller.
    assert error_code(refund_args(amount=1000)) == "REFUND_EXCEEDS_REMAINING"


def test_refund_cannot_exceed_remaining_amount(db):
    refund_customer(refund_args(amount=150))
    assert error_code(refund_args(amount=20, idempotency_key="operation-124")) == "REFUND_EXCEEDS_REMAINING"


def test_unknown_order(db):
    assert error_code(refund_args(order_id="999")) == "ORDER_NOT_FOUND"


def test_cannot_refund_another_customers_order(db):
    assert error_code(refund_args(order_id="125")) == "ORDER_NOT_FOUND"
    assert db.refunds == {}
    assert db.orders["125"]["refunded_total"] == Decimal("0")


def test_cannot_read_back_another_customers_refund_with_their_key(db):
    refund_customer(refund_args(customer_id="CUST-002", order_id="125", idempotency_key="their-key"))
    assert error_code(refund_args(order_id="125", idempotency_key="their-key")) == "ORDER_NOT_FOUND"


def test_retry_after_full_refund_still_returns_original(db):
    first = refund_customer(refund_args(amount=163.99))
    assert refund_customer(refund_args(amount=163.99))["refund"] == first["refund"]


@pytest.mark.parametrize("customer_id", [None, "", 1])
def test_missing_customer_context_is_rejected(db, customer_id):
    assert error_code(refund_args(customer_id=customer_id)) == "CUSTOMER_CONTEXT_MISSING"
    assert db.refunds == {}


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": 0},
        {"amount": -5},
        {"amount": "50"},
        {"amount": True},
        {"amount": 10.001},
        {"amount": float("inf")},
        {"amount": float("nan")},
        {"idempotency_key": ""},
        {"reason": None},
    ],
)
def test_invalid_parameters(db, overrides):
    assert error_code(refund_args(**overrides)) == "INVALID_PARAMETER"
