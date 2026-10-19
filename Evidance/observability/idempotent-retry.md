# Idempotent retry: the same refund sent twice is paid once

Produced by the deployed test `test_retried_refund_is_not_paid_twice`
([tests/deployed/test_deployed.py](../../tests/deployed/test_deployed.py), run with
`uv run pytest -m deployed -k retried -s`). It sends the same refund, with the same operation ID, to the
deployed agent in two new sessions, so the agent cannot know from its own history that the refund was issued.
Times are UTC, 2026-10-19.

Prompt (both sessions): "Refund 1 EUR on order 124, reason: retry test. Operation ID smoke-retry-640cb69f.
I confirm the order, amount and reason."

| Time | Session | Trace | Tool result (from the `execute_tool refunds___refund_customer` span) | Refunds Lambda request |
| --- | --- | --- | --- | --- |
| 21:01:37.012 | `smoke-test-4693e0343cb54880b324d6d38e98e982` | `6ad685276fece46a5b0f19a85aa6ced2` | `refund_id` `REF-17B1DA6A`, `"duplicate": false`, `order_status` `PARTIALLY_REFUNDED` | `a8b3eb21-1859-4dd0-9f0a-20385c73e324`, outcome ok |
| 21:01:48.173 | `smoke-test-a071aeb389744e99bb922552a29c36f6` | `6ad68532786a36ea108f424e0307413c` | `refund_id` `REF-17B1DA6A`, **`"duplicate": true`** | `79d6eda9-8fb9-4659-84bd-4bbc59bf7c83`, outcome ok |

Both calls reached the backend (two Lambda requests, both allowed by Cedar). The second returned the stored
refund instead of creating a new one.

State afterwards (DynamoDB, consistent reads):

| Table | Item | Value |
| --- | --- | --- |
| `CustomerSupport-refunds` | `CUST-001#smoke-retry-640cb69f` | one row: `REF-17B1DA6A`, 1 EUR, order 124, created 21:01:37 |
| `CustomerSupport-orders` | order 124 | `refunded_total` grew by 1 EUR, not 2 |

The test asserts all of this: one ledger row for the key, `refunded_total` up by exactly the refund amount,
and the same refund ID in both replies (the retry session can only know it from the backend's stored refund).

**How it works** (`tools/support_tools/refunds.py`, `store.py`): the ledger key is `<customer_id>#<operation ID>`.
Before refunding, the tool looks the key up and, if found, returns that refund with `"duplicate": true`. The
write itself is a DynamoDB transaction whose ledger put has the condition `attribute_not_exists(idempotency_key)`,
so even two retries racing each other produce one refund; the loser returns the winner's result.

The test uses a new key per run so it can be repeated without reseeding.

## The task's key, `operation-123`, in one conversation

[RetryRefund.png](../ScreenShots/RetryRefund.png): the refund with operation ID `operation-123` sent twice in the
same session (`8b2f18b9-a982-4c87-b703-a6439ef34522`).

| Turn | Time | Spans | Result |
| --- | --- | --- | --- |
| 1 | 21:01:03 | `execute_tool orders___get_order`, `execute_tool refunds___refund_customer` | refund issued: `REF-6D78E7D0`, 20 EUR, ledger row `CUST-001#operation-123` |
| 2 | 21:01:27 | no tool call | "I have already processed this refund", with the same refund ID |

Here the agent recognised the repeat from the conversation history and did not call the backend again. That is
the first line of defence; the deployed test above shows the second one, which does not depend on the agent:
when the retry does reach the backend, from a session that knows nothing about the first refund, the backend
returns the stored refund instead of paying again. Order 124's ledger holds exactly one row per operation:
`operation-123` (20 EUR) and `smoke-retry-640cb69f` (1 EUR).
