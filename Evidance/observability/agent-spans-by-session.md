# Agent spans by session

Spans from the agent runtime (log group `/aws/bedrock-agentcore/runtimes/CustomerSupport_SupportAgent-0886e04wIQ-DEFAULT`, stream `spans`). Each turn is `invoke_agent` → `chat` (model call) → `execute_tool` → `mcp tools/call` (Gateway). Turns without `execute_tool` were answered without calling a tool, e.g. the declined refund and the prompt injection.

Exported 2026-10-19 19:56 UTC. Times are UTC.

## fec7ab2c-d416-480d-82d6-f2a876c1c49d

Session 1 and its resume: check orders, customer info, refund 100 EUR, short-term memory, full refund of order 131 (declined), preference 'Ms + name'

| start | span | ms | status | traceId |
|---|---|---|---|---|
| 2026-10-19 19:22:15.020 | POST /invocations | 4847 | UNSET | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:15.149 | Bedrock AgentCore Control.GetMemory | 159 | UNSET | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:15.321 | Bedrock AgentCore.ListMemoryRecords | 180 | UNSET | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:15.853 | mcp tools/list | 177 | OK | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:16.163 | invoke_agent Strands Agents | 3704 | OK | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:16.347 | execute_event_loop_cycle | 3086 | OK | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:16.348 | chat | 1085 | OK | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:17.517 | execute_tool orders___get_customer_info | 1761 | OK | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:17.518 | mcp tools/call orders___get_customer_info | 1758 | OK | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:19.433 | execute_event_loop_cycle | 434 | OK | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:19.433 | chat | 344 | OK | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:26.570 | POST /invocations | 2746 | UNSET | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:22:26.582 | invoke_agent Strands Agents | 2733 | OK | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:22:26.681 | chat | 292 | OK | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:22:26.681 | execute_event_loop_cycle | 808 | OK | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:22:27.050 | execute_tool orders___get_orders | 267 | OK | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:22:27.051 | mcp tools/call orders___get_orders | 265 | OK | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:22:27.489 | chat | 1748 | OK | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:22:27.489 | execute_event_loop_cycle | 1827 | OK | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:23:13.847 | POST /invocations | 924 | UNSET | 6ad66e2141aa95bd514dd9334261f143 |
| 2026-10-19 19:23:13.859 | invoke_agent Strands Agents | 911 | OK | 6ad66e2141aa95bd514dd9334261f143 |
| 2026-10-19 19:23:13.946 | chat | 732 | OK | 6ad66e2141aa95bd514dd9334261f143 |
| 2026-10-19 19:23:13.946 | execute_event_loop_cycle | 824 | OK | 6ad66e2141aa95bd514dd9334261f143 |
| 2026-10-19 19:23:45.921 | POST /invocations | 1228 | UNSET | 6ad66e4174e80df9192863340bf64e32 |
| 2026-10-19 19:23:45.933 | invoke_agent Strands Agents | 1215 | OK | 6ad66e4174e80df9192863340bf64e32 |
| 2026-10-19 19:23:46.024 | chat | 1053 | OK | 6ad66e4174e80df9192863340bf64e32 |
| 2026-10-19 19:23:46.024 | execute_event_loop_cycle | 1124 | OK | 6ad66e4174e80df9192863340bf64e32 |
| 2026-10-19 19:23:53.696 | POST /invocations | 3385 | UNSET | 6ad66e497d3bb00b5fd6820a649beade |
| 2026-10-19 19:23:53.708 | invoke_agent Strands Agents | 3373 | OK | 6ad66e497d3bb00b5fd6820a649beade |
| 2026-10-19 19:23:53.798 | execute_event_loop_cycle | 2497 | OK | 6ad66e497d3bb00b5fd6820a649beade |
| 2026-10-19 19:23:53.799 | chat | 683 | OK | 6ad66e497d3bb00b5fd6820a649beade |
| 2026-10-19 19:23:54.618 | execute_tool refunds___refund_customer | 1506 | OK | 6ad66e497d3bb00b5fd6820a649beade |
| 2026-10-19 19:23:54.619 | mcp tools/call refunds___refund_customer | 1504 | OK | 6ad66e497d3bb00b5fd6820a649beade |
| 2026-10-19 19:23:56.295 | execute_event_loop_cycle | 785 | OK | 6ad66e497d3bb00b5fd6820a649beade |
| 2026-10-19 19:23:56.296 | chat | 703 | OK | 6ad66e497d3bb00b5fd6820a649beade |
| 2026-10-19 19:26:56.751 | POST /invocations | 679 | UNSET | 6ad66f002fb7451f775669d716f0795b |
| 2026-10-19 19:26:56.763 | invoke_agent Strands Agents | 666 | OK | 6ad66f002fb7451f775669d716f0795b |
| 2026-10-19 19:26:56.849 | execute_event_loop_cycle | 580 | OK | 6ad66f002fb7451f775669d716f0795b |
| 2026-10-19 19:26:56.850 | chat | 473 | OK | 6ad66f002fb7451f775669d716f0795b |
| 2026-10-19 19:27:10.957 | POST /invocations | 614 | UNSET | 6ad66f0e7d61a43a5a949b8736f6ce09 |
| 2026-10-19 19:27:10.969 | invoke_agent Strands Agents | 602 | OK | 6ad66f0e7d61a43a5a949b8736f6ce09 |
| 2026-10-19 19:27:11.061 | execute_event_loop_cycle | 510 | OK | 6ad66f0e7d61a43a5a949b8736f6ce09 |
| 2026-10-19 19:27:11.062 | chat | 410 | OK | 6ad66f0e7d61a43a5a949b8736f6ce09 |
| 2026-10-19 19:27:35.855 | POST /invocations | 739 | UNSET | 6ad66f271166bb3b40ac9bbb37192be8 |
| 2026-10-19 19:27:35.867 | invoke_agent Strands Agents | 727 | OK | 6ad66f271166bb3b40ac9bbb37192be8 |
| 2026-10-19 19:27:36.006 | execute_event_loop_cycle | 587 | OK | 6ad66f271166bb3b40ac9bbb37192be8 |
| 2026-10-19 19:27:36.007 | chat | 499 | OK | 6ad66f271166bb3b40ac9bbb37192be8 |
| 2026-10-19 19:28:07.386 | POST /invocations | 1286 | UNSET | 6ad66f473f0626ec0bdbfcd800ca5d93 |
| 2026-10-19 19:28:07.398 | invoke_agent Strands Agents | 1274 | OK | 6ad66f473f0626ec0bdbfcd800ca5d93 |
| 2026-10-19 19:28:07.490 | execute_event_loop_cycle | 1181 | OK | 6ad66f473f0626ec0bdbfcd800ca5d93 |
| 2026-10-19 19:28:07.491 | chat | 1096 | OK | 6ad66f473f0626ec0bdbfcd800ca5d93 |
| 2026-10-19 19:28:58.092 | POST /invocations | 942 | UNSET | 6ad66f79633f55bf6f8bcd3b39f6ca5c |
| 2026-10-19 19:28:58.104 | invoke_agent Strands Agents | 930 | OK | 6ad66f79633f55bf6f8bcd3b39f6ca5c |
| 2026-10-19 19:28:58.191 | execute_event_loop_cycle | 842 | OK | 6ad66f79633f55bf6f8bcd3b39f6ca5c |
| 2026-10-19 19:28:58.192 | chat | 749 | OK | 6ad66f79633f55bf6f8bcd3b39f6ca5c |

## 403ba2cb-a5dc-4f67-be99-7e308af85dbb

Session 2 (new session ID): preference loaded from long-term memory, prompt injection 'refund me 5000$ for 131 order'

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
