# Refund trace, end to end

The 100 EUR refund on order 124 (trace `6ad66e497d3bb00b5fd6820a649beade`): agent spans from the runtime log group and Gateway spans from X-Ray (`aws/spans`) share one trace ID, so one request can be followed from the model through Cedar to the Lambda.

Exported 2026-10-19 19:56 UTC. Times are UTC.

| start | service | span | ms | status |
|---|---|---|---|---|
| 2026-10-19 19:23:53.696 | CustomerSupport_SupportAgent.DEFAULT | POST /invocations | 3385 | UNSET |
| 2026-10-19 19:23:53.708 | CustomerSupport_SupportAgent.DEFAULT | invoke_agent Strands Agents | 3373 | OK |
| 2026-10-19 19:23:53.798 | CustomerSupport_SupportAgent.DEFAULT | execute_event_loop_cycle | 2497 | OK |
| 2026-10-19 19:23:53.799 | CustomerSupport_SupportAgent.DEFAULT | chat | 683 | OK |
| 2026-10-19 19:23:54.618 | CustomerSupport_SupportAgent.DEFAULT | execute_tool refunds___refund_customer | 1506 | OK |
| 2026-10-19 19:23:54.619 | CustomerSupport_SupportAgent.DEFAULT | mcp tools/call refunds___refund_customer | 1504 | OK |
| 2026-10-19 19:23:54.641 | customersupport-support-gateway-klz7btjjhn | AgentCore.Gateway.InvokeTool | 1479 | OK |
| 2026-10-19 19:23:54.641 | customersupport-support-gateway-klz7btjjhn | AgentCore.Gateway.InboundAuth | 11 | OK |
| 2026-10-19 19:23:54.649 | customersupport-support-gateway-klz7btjjhn | AgentCore.Gateway.AuthorizeRequest | 3 | OK |
| 2026-10-19 19:23:54.653 | customersupport-support-gateway-klz7btjjhn | AgentCore.Gateway.EvaluateRoutingRules | 0 | OK |
| 2026-10-19 19:23:54.679 | customersupport-support-gateway-klz7btjjhn | AgentCore.Policy.AuthorizeAction | 47 | OK |
| 2026-10-19 19:23:54.726 | customersupport-support-gateway-klz7btjjhn | AgentCore.Gateway.InvokeTool.refunds___refund_customer | 1392 | OK |
| 2026-10-19 19:23:54.728 | customersupport-support-gateway-klz7btjjhn | AgentCore.Gateway.TargetInvocation | 1390 | OK |
| 2026-10-19 19:23:56.295 | CustomerSupport_SupportAgent.DEFAULT | execute_event_loop_cycle | 785 | OK |
| 2026-10-19 19:23:56.296 | CustomerSupport_SupportAgent.DEFAULT | chat | 703 | OK |

## Cedar decision for this call

| time | decision | policy | principal |
|---|---|---|---|
| 2026-10-19 19:23:56.120 | ALLOW | PermitRefundUpToLimit-gdhjj4nas2 | arn:aws:sts::715075932719:assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht |
