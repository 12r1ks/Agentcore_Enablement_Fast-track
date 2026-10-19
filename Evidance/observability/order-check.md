# Order check: "Why is my order 123 delayed?"

The task's example request. Session `78268051-c88c-43aa-8dc2-8528b587cca6`, trace
`6ad682013f9d01810d8ec81911f14a5d`, 2026-10-19 (times UTC).

| Start | Service | Span | ms | Status |
| --- | --- | --- | --- | --- |
| 20:48:07.838 | agent | `Bedrock AgentCore.ListMemoryRecords` (preferences loaded at session start) | 174 | |
| 20:48:08.374 | agent | `mcp tools/list` | 125 | OK |
| 20:48:08.443 | gateway | `AgentCore.Policy.PartiallyAuthorizeActions` (tools the agent may see) | 52 | OK |
| 20:48:08.793 | agent | `chat` (model picks `get_order`) | 1053 | OK |
| 20:48:09.917 | agent | `execute_tool orders___get_order` | 837 | OK |
| 20:48:09.951 | gateway | `AgentCore.Policy.AuthorizeAction` (Cedar: ALLOW, `PermitOrderReads`) | 43 | OK |
| 20:48:09.996 | gateway | `AgentCore.Gateway.TargetInvocation` (orders Lambda) | 753 | OK |
| 20:48:10.915 | agent | `chat` (answer to the customer) | 595 | OK |

Tool log (`/aws/lambda/CustomerSupport-orders`, request `df40b457-9dbb-4585-bce5-e7542365c248`,
X-Ray trace `1-6ad68201-3f9d01810d8ec81911f14a5d`):

```
{"event": "tool_call", "tool": "get_order", "outcome": "ok", "argument_names": ["customer_id", "order_id"]}
```

The model selected the right tool for the question and passed the order ID. `get_order` returns the full
order, including its `delay` (reason `CARRIER_BACKLOG`: "PostNL has a parcel backlog at the Amsterdam sorting
centre."). The agent's reply, from the same trace's telemetry:

> The delay is due to a carrier backlog; specifically, PostNL is experiencing a parcel backlog at the
> Amsterdam sorting centre.

The customer ID was added by the agent's `CustomerContextHook`, not by the model.
