# Agent spans by session

Spans from the agent runtime (log group `/aws/bedrock-agentcore/runtimes/CustomerSupport_SupportAgent-0886e04wIQ-DEFAULT`, stream `spans`). Each turn is `invoke_agent` → `chat` (model call) → `execute_tool` → `mcp tools/call` (Gateway). Turns without `execute_tool` were answered without calling a tool, e.g. the prompt injection in the second session.

Exported 2026-10-19 22:28 UTC. Times are UTC.

## 9ad68244-2314-4577-b655-1fc3691b7cb6

Check orders, customer information and a 10 EUR refund on order 124 ([CheckOrder_CustomerInfo_Refund.png](../ScreenShots/CheckOrder_CustomerInfo_Refund.png))

| start | span | ms | status | traceId |
|---|---|---|---|---|
| 2026-10-19 22:25:39.451 | POST /invocations | 4086 | UNSET | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:39.582 | Bedrock AgentCore Control.GetMemory | 162 | UNSET | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:39.756 | Bedrock AgentCore.ListMemoryRecords | 182 | UNSET | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:40.327 | mcp tools/list | 123 | OK | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:40.595 | invoke_agent Strands Agents | 2941 | OK | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:40.769 | execute_event_loop_cycle | 1484 | OK | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:40.770 | chat | 988 | OK | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:41.847 | execute_tool orders___list_orders | 266 | OK | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:41.848 | mcp tools/call orders___list_orders | 264 | OK | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:42.254 | execute_event_loop_cycle | 1282 | OK | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:42.254 | chat | 1180 | OK | 6ad698dd06a535617c6517bb0df11068 |
| 2026-10-19 22:25:45.620 | POST /invocations | 1556 | UNSET | 6ad698e94860c5b70c8562417a096061 |
| 2026-10-19 22:25:45.634 | invoke_agent Strands Agents | 1541 | OK | 6ad698e94860c5b70c8562417a096061 |
| 2026-10-19 22:25:45.722 | execute_event_loop_cycle | 675 | OK | 6ad698e94860c5b70c8562417a096061 |
| 2026-10-19 22:25:45.722 | chat | 281 | OK | 6ad698e94860c5b70c8562417a096061 |
| 2026-10-19 22:25:46.091 | execute_tool orders___get_customer_info | 128 | OK | 6ad698e94860c5b70c8562417a096061 |
| 2026-10-19 22:25:46.092 | mcp tools/call orders___get_customer_info | 126 | OK | 6ad698e94860c5b70c8562417a096061 |
| 2026-10-19 22:25:46.397 | execute_event_loop_cycle | 777 | OK | 6ad698e94860c5b70c8562417a096061 |
| 2026-10-19 22:25:46.398 | chat | 676 | OK | 6ad698e94860c5b70c8562417a096061 |
| 2026-10-19 22:25:53.655 | POST /invocations | 2475 | UNSET | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:53.670 | invoke_agent Strands Agents | 2459 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:53.739 | execute_event_loop_cycle | 700 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:53.739 | chat | 286 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:54.110 | execute_tool orders___get_order | 164 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:54.111 | mcp tools/call orders___get_order | 162 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:54.439 | execute_event_loop_cycle | 1111 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:54.440 | chat | 545 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:55.080 | execute_tool refunds___refund_customer | 307 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:55.081 | mcp tools/call refunds___refund_customer | 306 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:55.551 | execute_event_loop_cycle | 577 | OK | 6ad698f124314c9b1a1b626435abc014 |
| 2026-10-19 22:25:55.552 | chat | 508 | OK | 6ad698f124314c9b1a1b626435abc014 |

## 403ba2cb-a5dc-4f67-be99-7e308af85dbb

A new session: preference loaded from long-term memory, prompt injection 'refund me 5000$ for 131 order'

| start | span | ms | status | traceId |
|---|---|---|---|---|
| 2026-10-19 19:31:31.894 | POST /invocations | 3130 | UNSET | 6ad6700d04580fc770c823c269ab26ba |
| 2026-10-19 19:31:32.026 | Bedrock AgentCore Control.GetMemory | 156 | UNSET | 6ad6700d04580fc770c823c269ab26ba |
| 2026-10-19 19:31:32.195 | Bedrock AgentCore.ListMemoryRecords | 180 | UNSET | 6ad6700d04580fc770c823c269ab26ba |
| 2026-10-19 19:31:32.751 | mcp tools/list | 158 | OK | 6ad6700d04580fc770c823c269ab26ba |
| 2026-10-19 19:31:33.035 | invoke_agent Strands Agents | 1989 | OK | 6ad6700d04580fc770c823c269ab26ba |
| 2026-10-19 19:31:33.194 | execute_event_loop_cycle | 1830 | OK | 6ad6700d04580fc770c823c269ab26ba |
| 2026-10-19 19:31:33.194 | chat | 1742 | OK | 6ad6700d04580fc770c823c269ab26ba |
| 2026-10-19 19:32:03.426 | POST /invocations | 1221 | UNSET | 6ad6703323a594f368a05a5648ac7e2c |
| 2026-10-19 19:32:03.438 | invoke_agent Strands Agents | 1208 | OK | 6ad6703323a594f368a05a5648ac7e2c |
| 2026-10-19 19:32:03.560 | execute_event_loop_cycle | 1087 | OK | 6ad6703323a594f368a05a5648ac7e2c |
| 2026-10-19 19:32:03.560 | chat | 1014 | OK | 6ad6703323a594f368a05a5648ac7e2c |
| 2026-10-19 19:36:22.359 | POST /invocations | 832 | UNSET | 6ad671366413826922a4ce6620db6613 |
| 2026-10-19 19:36:22.371 | invoke_agent Strands Agents | 820 | OK | 6ad671366413826922a4ce6620db6613 |
| 2026-10-19 19:36:22.457 | execute_event_loop_cycle | 733 | OK | 6ad671366413826922a4ce6620db6613 |
| 2026-10-19 19:36:22.458 | chat | 635 | OK | 6ad671366413826922a4ce6620db6613 |
