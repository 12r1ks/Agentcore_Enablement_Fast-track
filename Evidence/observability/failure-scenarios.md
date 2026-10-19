# Failure scenarios

Each failure was triggered through the deployed agent (`agentcore invoke`, one new session per scenario)
and traced back to its root cause from telemetry alone. Times are UTC, 2026-10-19.

Where the evidence comes from:

- **Agent spans:** runtime log group `/aws/bedrock-agentcore/runtimes/CustomerSupport_SupportAgent-0886e04wIQ-DEFAULT`, stream `spans`
- **Agent logs:** the same log group, stream `runtime-logs-<session-id>`
- **Tool logs:** `/aws/lambda/CustomerSupport-orders`, `/aws/lambda/CustomerSupport-refunds`, `/aws/lambda/CustomerSupport-company-info`

## Invalid parameters

Prompt: "Refund 12.345 EUR on order 124, reason: dent. Operation ID invalid-001. I confirm the order, amount and reason."
Run twice, in sessions `ea6ee315-ae84-462d-95e0-56215e18f996` and `daf67b5a-3bd2-4c69-bc89-73b1d76807fb`.

| Session | Trace | Failing span | Tool log (Lambda request ID) | Outcome |
| --- | --- | --- | --- | --- |
| `ea6ee315…` | `6ad67a9d4b39ed5d3acd33aa44dce2d7` | `execute_tool refunds___refund_customer` at 20:16:39.579 | `2df2bbc3-d2a8-48a2-8738-fcce8308108f` | `INVALID_PARAMETER` |
| `daf67b5a…` | `6ad67aa137b77e03257a559f2c2138b8` | `execute_tool refunds___refund_customer` at 20:16:43.594 | `fe9bc478-ad6f-4cc6-8ec1-c9e2338b11e3` | `INVALID_PARAMETER` |

Tool log line (refunds Lambda, 20:16:40.110):

```
{"event": "tool_call", "tool": "refund_customer", "outcome": "INVALID_PARAMETER",
 "argument_names": ["amount", "customer_id", "idempotency_key", "order_id", "reason"]}
```

Spans of the turn (session `daf67b5a…`):

| Start | Span | ms | Status |
| --- | --- | --- | --- |
| 20:16:41.217 | `invoke_agent Strands Agents` | 3662 | OK |
| 20:16:41.369 | `chat` | 1016 | OK |
| 20:16:42.466 | `execute_tool orders___get_orders` | 131 | OK |
| 20:16:42.759 | `chat` | 758 | OK |
| 20:16:43.594 | `execute_tool refunds___refund_customer` | 165 | OK |
| 20:16:43.926 | `chat` | 862 | OK |

**Root cause:** the model passed the amount as given, `12.345`. The refund tool accepts at most 2 decimal
places, so it rejected the call with `INVALID_PARAMETER` (a structured tool error, `retryable: false`) before
touching any data. The tool span is `OK` because the tool answered normally with an error result; the
outcome is in the tool log. The agent then explained the problem to the customer instead of retrying.

## LLM loop

Prompt: "Give me every company policy section, one by one: about, contact, order_statuses, shipping, delays,
returns, refunds, warranty, payment, privacy, escalation, faq."
Session `f4545d5b-b3e6-49ed-8b6a-d1d706111870`, trace `6ad67ab66f401e44322e860c100e9254`.

Agent log (stream `runtime-logs-f4545d5b…`):

```
2026-10-19 20:17:11,668 WARNING [hooks.loop_guard] [loop_guard.py:45]
[trace_id=6ad67ab66f401e44322e860c100e9254 span_id=43caf97bdd77db21 ...]
- Tool limit of 10 reached in one turn (possible LLM loop)
```

Tool spans of the turn:

| Start | Span | ms | Status | Status message |
| --- | --- | --- | --- | --- |
| 20:17:03.906 – 20:17:10.978 | `execute_tool company-info___get_company_policy` × 10 | 105–611 | OK | |
| 20:17:11.667 | `execute_tool company-info___get_company_policy` (11th) | 1 | ERROR | Tool limit for this request reached. Do not call more tools; answer the customer with the information you already have. |
| 20:17:12.251 | `execute_tool company-info___get_company_policy` (12th) | 1 | ERROR | same |
| 20:17:12.404 | `chat` (final answer) | 4109 | OK | |

**Root cause:** the request needed 12 tool calls in one turn, above the limit of 10 set by `LoopGuardHook`
(`app/SupportAgent/hooks/loop_guard.py`). From the 11th call on, the hook cancelled each tool call before it
reached the Gateway (1 ms spans, no `mcp tools/call` child) and told the model to answer with what it had.
The model stopped and answered, so the second level of the guard (aborting the turn after 3 more model
calls) was not needed. The whole turn took 14 s instead of running on.

## Tool timeout

Prompt: "Why is my order 901 delayed?" Session `7d9e2a5e-c888-499c-bfc1-8688a4bc6acb`,
trace `6ad681d85fbb708646294a6923fac062`. Order ID 901 is a demo trigger: the orders Lambda sleeps 15 s,
past its 10 s timeout (`tools/support_tools/handler.py`).

Spans (agent and Gateway, one trace):

| Start | Service | Span | ms | Status |
| --- | --- | --- | --- | --- |
| 20:47:28.815 | agent | `chat` (model picks `get_order`) | 1161 | OK |
| 20:47:30.060 | agent | `execute_tool orders___get_order` | 10097 | ERROR: "An internal error occurred. Please retry later." |
| 20:47:30.072 | gateway | `AgentCore.Gateway.InvokeTool` | 10081 | ERROR |
| 20:47:30.097 | gateway | `AgentCore.Policy.AuthorizeAction` | 28 | OK |
| 20:47:30.126 | gateway | `AgentCore.Gateway.InvokeTool.orders___get_order` | 10024 | ERROR |
| 20:47:40.330 | agent | `chat` (answer to the customer) | 1409 | OK |

Tool log (`/aws/lambda/CustomerSupport-orders`, request `dc457bea-1f66-434d-9b0c-69f7f195e8ea`):

```
20:47:30.146 [WARNING] {"event": "simulated_failure", "kind": "timeout"}
20:47:40.177 REPORT RequestId: dc457bea-… Duration: 10000.00 ms … Status: timeout
             XRAY TraceId: 1-6ad681d8-5fbb708646294a6923fac062
```

**Root cause:** the orders Lambda did not answer within its 10 s timeout (`Status: timeout` at exactly
10000 ms), so the Gateway's tool call failed after 10.0 s and the agent got a generic error. Cedar allowed the
call (`AuthorizeAction` OK), which rules out authorization. The Lambda's X-Ray trace ID is the agent's trace ID,
so the slow span leads straight to the Lambda log line.

## HTTP 500 (backend crash)

Prompt: "What is the status of order 902?" Session `8423cae4-6861-4bb7-b044-bf9cf8a51fdc`,
trace `6ad681f23decc92b66066c3a01c67343`. Order ID 902 is a demo trigger: the orders Lambda raises an
unhandled exception.

| Start | Service | Span | ms | Status |
| --- | --- | --- | --- | --- |
| 20:47:54.216 | agent | `chat` (model picks `get_order`) | 1040 | OK |
| 20:47:55.336 | agent | `execute_tool orders___get_order` | 285 | ERROR: "An internal error occurred. Please retry later." |
| 20:47:55.345 | gateway | `AgentCore.Gateway.InvokeTool` | 271 | ERROR |
| 20:47:55.369 | gateway | `AgentCore.Policy.AuthorizeAction` | 33 | OK |
| 20:47:55.403 | gateway | `AgentCore.Gateway.InvokeTool.orders___get_order` | 212 | ERROR |
| 20:47:55.824 | agent | `chat` (answer to the customer) | 494 | OK |

Tool log (request `507de2a8-e947-4578-a8d3-7d0fcd445e36`, X-Ray trace `1-6ad681f2-3decc92b66066c3a01c67343`):

```
20:47:55.612 [WARNING] {"event": "simulated_failure", "kind": "crash"}
20:47:55.612 [ERROR] RuntimeError: Simulated backend crash
Traceback (most recent call last):
  File "/var/task/support_tools/handler.py", line 65, in lambda_handler
    _simulate_failure(args)
  File "/var/task/support_tools/handler.py", line 43, in _simulate_failure
    raise RuntimeError("Simulated backend crash")
```

**Root cause:** an unhandled `RuntimeError` in the orders Lambda (`handler.py` line 43), reported to the
Gateway as a function error. Same span pattern as the timeout, but failing after 0.2 s instead of 10 s: a fast
failure points to a crash, a 10 s failure to a timeout. The stack trace in the Lambda log names the line.

## Wrong tool selection

Prompt: "i want to cancel order 124". Session `0903f29f-267c-4aff-980d-900961d10b7e`,
trace `6ad68c112a81352678773bfb6ea9e832`. There is no cancel tool, and the closest-looking one is
`refund_customer`, so this tests whether the model picks a wrong tool for an action it can't perform.

| Start | Span | ms | Status |
| --- | --- | --- | --- |
| 21:31:04.448 | `Bedrock AgentCore.ListMemoryRecords` (preferences loaded) | 176 | |
| 21:31:05.478 | `chat` (model picks `get_order`) | 1005 | OK |
| 21:31:06.568 | `execute_tool orders___get_order` | 1513 | OK |
| 21:31:08.250 | `chat` (answer) | 503 | OK |

Agent reply, from the trace's telemetry:

> I'm sorry, Ms. Emma de Vries, but I cannot cancel order 124 because it has already been delivered and
> partially refunded. If there is something more I can help you with regarding this order, please let me know!

**Result:** correct selection. The model checked the order before answering and did not call `refund_customer`
as a substitute for cancelling. The trace is where a wrong pick would show: an `execute_tool
refunds___refund_customer` span, with the refund's arguments in the span, after a request that never asked for
a refund. A smaller gap is visible too: no `get_company_policy` span, so the agent didn't point the customer to
the returns process that the policy prescribes for delivered orders.

## How the failures differ in the telemetry

| Failure | Failing span | Duration | Where the root cause is |
| --- | --- | --- | --- |
| Tool timeout | `InvokeTool.orders___get_order` ERROR | 10,024 ms (the Lambda timeout) | Lambda `REPORT … Status: timeout` |
| HTTP 500 | `InvokeTool.orders___get_order` ERROR | 212 ms | Lambda `[ERROR] RuntimeError` with stack trace |
| Invalid parameters | none; the tool answered normally | 165 ms | Lambda `tool_call` line, `outcome: INVALID_PARAMETER` |
| LLM loop | `execute_tool` ERROR, no Gateway span | 1 ms | Agent log `Tool limit of 10 reached`; span status message |
| Wrong tool selection | none; check which `execute_tool` spans follow the request | | The tool names and arguments in the agent's spans |

In every case the agent answered the customer without crashing, and Cedar allowed the call, so authorization
was never the cause.

## Note: first attempt at the timeout and crash

The first runs (sessions `06bdcfa9…` and `8a3eb5db…`, 20:12–20:15) did not trigger either failure. The tool
logs showed why: the model always called the old `get_orders` tool without its optional `order_id`
(`"argument_names": ["customer_id"]`, 29 of 29 calls), listing orders instead of fetching one, so the triggers
never saw 901 or 902. The tool was then split into `list_orders` and `get_order` with a required `order_id`,
which the model fills reliably.
