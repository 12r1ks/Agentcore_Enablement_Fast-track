# Concurrent refunds: two sessions, one payout

Two sessions asked for the same refund on order 123 within one second
([DoubleRefund.png](../ScreenShots/DoubleRefund.png)). Only one refund was paid. Times are UTC, 2026-10-19.

| Time | Session | Request | Idempotency key (chosen by the model) | Tool outcome |
| --- | --- | --- | --- | --- |
| 20:54:13 / 20:54:25 | both | `get_order 123` | | ok: 163.99 EUR refundable |
| 20:54:30.557 | A `8ba6b5e7-b7b0-469f-aa2c-e75f6449be27` | refund 160 EUR | `refund-order-123-damage-123456789` | ok: `REF-8851E133`, `"duplicate": false` |
| 20:54:31.402 | B `25faf6fa-c79d-4ee1-ba75-787c09fa6854` | refund 160 EUR | `refund-order-123-damage-20261019-01` | `REFUND_EXCEEDS_REMAINING` |
| 20:55:43.869 | B | refund 163.99 EUR ("full refund") | `refund-order-123-full-20261019-02` | `REFUND_EXCEEDS_REMAINING` (3.99 EUR left) |

Sources: tool inputs and results from the `execute_tool refunds___refund_customer` spans (runtime log group,
stream `spans`; session A trace `6ad68385054594286ac63e7051242068`); outcomes from the `tool_call` lines in
`/aws/lambda/CustomerSupport-refunds` (requests `244a2dce-…` ok, `4b649b6d-…` and `949d5e82-…`
`REFUND_EXCEEDS_REMAINING`).

State afterwards (DynamoDB):

| Table | Item | Value |
| --- | --- | --- |
| `CustomerSupport-refunds` | rows for order 123 | one: `CUST-001#refund-order-123-damage-123456789`, `REF-8851E133`, 160 |
| `CustomerSupport-orders` | order 123 | `refunded_total` 160, status `DELAYED` (partial refund keeps it delayed), one entry in `refunds` |

**What stopped the second payout:** not the idempotency key. No operation ID was given, so each session's model
chose its own key, and session B's request was a new refund as far as the backend could tell. It was refused
because the refund tool reads the order with a consistent read and only 3.99 EUR remained after session A's
refund. Had both writes raced at the same instant, the transaction's condition `refunded_total = :expected`
would have rejected the second with the retryable `ORDER_CHANGED` (`tools/support_tools/store.py`).

**Also visible:** session B's model told the customer the refund history was empty. It reused the order it had
fetched before session A's refund instead of fetching it again. The backend enforced the real amounts anyway,
another case where safety does not depend on the model.

The idempotent retry itself (same operation ID sent twice) is a separate scenario.
