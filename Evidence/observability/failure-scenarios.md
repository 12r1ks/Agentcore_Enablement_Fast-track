# Failure scenarios

Each failure was triggered through the deployed agent (`agentcore invoke`, one new session per scenario)
and traced back to its root cause from telemetry alone. Times are UTC, 2026-10-19.

Where the evidence comes from:

- **Agent spans:** runtime log group `/aws/bedrock-agentcore/runtimes/CustomerSupport_SupportAgent-0886e04wIQ-DEFAULT`, stream `spans`
- **Agent logs:** the same log group, stream `runtime-logs-<session-id>`
- **Tool logs:** `/aws/lambda/CustomerSupport-orders`, `/aws/lambda/CustomerSupport-refunds`, `/aws/lambda/CustomerSupport-company-info`

## Invalid parameters

Prompt: "Why is my order LUM-2026-10-ORDER-REFERENCE-123-NL-AMSTERDAM-WAREHOUSE-B-PRIORITY-XYZ delayed?"
(a 69-character order ID; the tools accept at most 64). Session `invalid-params-1792448534-long-order-id-session`,
trace `6ad69818737d475b4d71a23c337ee8be`, with the current tools.

| Start | Span | ms | Status |
| --- | --- | --- | --- |
| 22:22:24.280 | `invoke_agent Strands Agents` | 2669 | OK |
| 22:22:24.483 | `chat` (model picks `get_order` with the ID as given) | 1272 | OK |
| 22:22:25.845 | `execute_tool orders___get_order` | 159 | OK |
| 22:22:26.174 | `chat` (answer) | 701 | OK |

Tool log (`/aws/lambda/CustomerSupport-orders`, request `c36c0a33-d6df-44c6-857f-f174409a4e63`, X-Ray trace
`1-6ad69818-737d475b4d71a23c337ee8be`, the agent's trace ID):

```
{"event": "tool_call", "tool": "get_order", "outcome": "INVALID_PARAMETER", "argument_names": ["customer_id", "order_id"]}
```

Agent reply: "I couldn't retrieve the details for that specific order ID because it is too long for my system to
process. Could you please double-check the order ID and provide it again? Alternatively, I can list your recent
orders for you to identify it."

**Root cause:** the order ID exceeded the tools' 64-character limit, so `get_order` rejected it with
`INVALID_PARAMETER` (a structured tool error, `retryable: false`) before reading any data. The tool span is `OK`
because the tool answered normally with an error result; the outcome is in the tool log, linked to the span by
the shared trace ID. The agent explained the problem instead of retrying.

Earlier runs with a refund of 12.345 EUR (sessions `ea6ee315…` and `daf67b5a…`, 20:16, with the earlier
`get_orders` tool) got the same outcome from `refund_customer` (amounts allow at most 2 decimal places;
refunds Lambda requests `2df2bbc3…` and `fe9bc478…`). Rerun at 22:20 with the current tools, the model rounded
the amount to 12.35 before calling the tool, so the invalid value never reached the backend; an over-long
order ID is a value the model passes on unchanged.

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

A real wrong pick, caught in production-like conditions. Between the two deploys that split `get_orders` into
`list_orders` and `get_order`, the Cedar permit `PermitOrderReads` briefly allowed only `get_customer_info`
(20:42–20:45). Three order questions were asked in that window.

| Session | Trace | Question | Tools called | Agent's answer |
| --- | --- | --- | --- | --- |
| `743297a7-3d36-4ad4-a025-2612a0055de5` | `6ad680d32cda5efa19eccf3a43724f47` | "Why is my order 901 delayed?" | `get_customer_info` × 10, `get_company_policy` × 1 | Generic delay reasons, without the order |
| `efac8e75-a8b1-497f-abb5-90c7638b3e75` | `6ad680f3029d18667b80f397499eb7a4` | "What is the status of order 902?" | `get_customer_info` × 11 | "I don't have access to the specific details for order 902 at the moment." |
| `c1927420-8d3c-4dd2-bee8-0ee9e60790be` | `6ad6812b417ca4023893e16a60c0e864` | "Why is my order 123 delayed?" | `get_customer_info` × 11 | "I don't have the details for order 123 in my current view. Could you please double-check the order number?" |

How it shows in the telemetry (session `c1927420…`):

- `AgentCore.Policy.PartiallyAuthorizeActions` on `tools/list`: the Gateway lists only the tools the caller is
  permitted to use, so the model never saw `list_orders` or `get_order`.
- 11 × `execute_tool orders___get_customer_info` in one turn, each ALLOW by `PermitOrderReads` in the Gateway log,
  each `"outcome": "ok"` in the orders Lambda log: every call succeeded, but none could answer the question.
- Agent log at 20:43:47 (session `efac8e75…`):
  `WARNING [hooks.loop_guard] [trace_id=6ad680f3029d18667b80f397499eb7a4 …] Tool limit of 10 reached in one turn`.
- The answer asks the customer to double-check an order number that exists.

**Root cause:** a deployment state in which the order tools were not permitted. The Gateway hid them from the
tool list, so the model picked the only related tool it had, a profile lookup that cannot answer order
questions, and kept calling it until the loop guard stopped it. Nothing failed: every span is `OK` and every
decision `ALLOW`, which is what makes a wrong pick harder to spot than a crash. The signal is the mismatch between
the question and the tool names in `execute_tool` spans, plus the loop guard warning. The smoke test
`test_agent_lists_the_customers_orders` catches this state after a deploy (it failed while this deployment state
was live).

### For comparison: a correct pick when no fitting tool exists

Prompt: "i want to cancel order 124" (no cancel tool exists; the closest-looking one is `refund_customer`).
Session `0903f29f-267c-4aff-980d-900961d10b7e`, trace `6ad68c112a81352678773bfb6ea9e832`: `chat` →
`execute_tool orders___get_order` → `chat`. The reply: "I cannot cancel order 124 because it has already been
delivered and partially refunded." The model checked the order and did not use `refund_customer` as a
substitute for cancelling.

## How the failures differ in the telemetry

| Failure | Failing span | Duration | Where the root cause is |
| --- | --- | --- | --- |
| Tool timeout | `InvokeTool.orders___get_order` ERROR | 10,024 ms (the Lambda timeout) | Lambda `REPORT … Status: timeout` |
| HTTP 500 | `InvokeTool.orders___get_order` ERROR | 212 ms | Lambda `[ERROR] RuntimeError` with stack trace |
| Invalid parameters | none; the tool answered normally | 159 ms | Lambda `tool_call` line, `outcome: INVALID_PARAMETER` |
| LLM loop | `execute_tool` ERROR, no Gateway span | 1 ms | Agent log `Tool limit of 10 reached`; span status message |
| Wrong tool selection | none; all `OK` | | Tool names in `execute_tool` spans that don't match the question; `tools/list` filtered by the permit |

In every case the agent answered the customer without crashing.
## Note: first attempt at the timeout and crash

The first runs (sessions `06bdcfa9…` and `8a3eb5db…`, 20:12–20:15) did not trigger either failure. The tool
logs showed why: the model always called the old `get_orders` tool without its optional `order_id`
(`"argument_names": ["customer_id"]`, 29 of 29 calls), listing orders instead of fetching one, so the triggers
never saw 901 or 902. The tool was then split into `list_orders` and `get_order` with a required `order_id`,
which the model fills reliably.
