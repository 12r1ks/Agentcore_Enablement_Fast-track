# Gateway policy decisions

Every Cedar decision logged by the Gateway (log group `/aws/vendedlogs/bedrock-agentcore/CustomerSupport-gateway`) during testing. Calls by `assumed-role/AgentCore-CustomerSupport-…` are the agent; calls by `user/ADMIN` are direct calls with local credentials. The 17:49 check ran in LOG_ONLY mode: decisions were logged but not enforced, so the denied ADMIN calls still reached the Lambda. The 19:15 calls ran in ENFORCE mode: the denied ADMIN calls were blocked at the Gateway with `Tool Execution Denied`.

Exported 2026-10-19 19:56 UTC. Times are UTC.

| time | decision | policy | principal | trace_id |
|---|---|---|---|---|
| 2026-10-19 17:49:05.298 | ALLOW | PermitOrderReads-lvdffusibv | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad658082f68e6ba645adeca07eedd56 |
| 2026-10-19 17:49:07.524 | ALLOW | PermitOrderReads-lvdffusibv | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad658082f68e6ba645adeca07eedd56 |
| 2026-10-19 17:49:28.626 | ALLOW | PermitRefundUpToLimit-gdhjj4nas2 | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad65827687eacfc0e7d14d56d68c0d2 |
| 2026-10-19 17:49:51.176 | DENY |  | arn:aws:iam::715075932719:user/ADMIN | 6ad6583f65ab06aa1f34314b582da480 |
| 2026-10-19 17:49:51.475 | DENY |  | arn:aws:iam::715075932719:user/ADMIN | 6ad6583f6860ef867d9175d5173bb3ff |
| 2026-10-19 17:49:51.650 | DENY | ForbidRefundOverLimit-5le1494lmi | arn:aws:iam::715075932719:user/ADMIN | 6ad6583f13350ebe221a39773c0ff72b |
| 2026-10-19 18:09:52.365 | ALLOW | PermitOrderReads-lvdffusibv | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad65ce51f2baf214082f5444aaad774 |
| 2026-10-19 18:10:01.766 | ALLOW | PermitOrderReads-lvdffusibv | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad65cf8526050a310a4753f0f186c15 |
| 2026-10-19 18:11:33.027 | ALLOW | PermitRefundUpToLimit-gdhjj4nas2 | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad65d520051d51f0afa94b67500b7e0 |
| 2026-10-19 19:14:55.925 | ALLOW | PermitOrderReads-lvdffusibv | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad66c25327dd7ba6b8ec7eb5241889a |
| 2026-10-19 19:14:56.612 | ALLOW | PermitOrderReads-lvdffusibv | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad66c25327dd7ba6b8ec7eb5241889a |
| 2026-10-19 19:15:04.659 | DENY |  | arn:aws:iam::715075932719:user/ADMIN | 6ad66c385760e3f23c1ea90445a0004d |
| 2026-10-19 19:15:04.903 | DENY |  | arn:aws:iam::715075932719:user/ADMIN | 6ad66c387c767ec916bd553f006ce9c9 |
| 2026-10-19 19:15:05.075 | DENY | ForbidRefundOverLimit-5le1494lmi | arn:aws:iam::715075932719:user/ADMIN | 6ad66c3861c2375b210418485bd0527a |
| 2026-10-19 19:22:19.272 | ALLOW | PermitOrderReads-lvdffusibv | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad66de05724f8f438b904b30ef1d6bd |
| 2026-10-19 19:22:27.312 | ALLOW | PermitOrderReads-lvdffusibv | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad66df22608e48b059be7d9294be44c |
| 2026-10-19 19:23:56.120 | ALLOW | PermitRefundUpToLimit-gdhjj4nas2 | assumed-role/AgentCore-CustomerSupport-ApplicationAgentSupportAg-aaSeBABLnqht | 6ad66e497d3bb00b5fd6820a649beade |
