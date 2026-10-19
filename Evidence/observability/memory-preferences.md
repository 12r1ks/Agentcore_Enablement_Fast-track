# Long-term memory: customer preferences

USER_PREFERENCE records for customer CUST-001 in AgentCore Memory `CustomerSupport_UserPreference-FfAp5g9pL2`, namespace `/strategies/UserPreference_Userpreference-4VLEzRA24B/actors/CUST-001/`. AgentCore extracts them in the background from session events; the agent loads them when a new session starts. Both task-style preferences are stored: how to address the customer, and the task's own example, the preferred AWS region.

Exported 2026-10-19 19:56 UTC. Times are UTC.

| created | preference |
|---|---|
| 2026-10-19 19:30:04 | Always be referred to as Ms. Emma de Vries (Ms + first and last name) |
| 2026-10-19 19:37:27 | Preferred AWS region is eu-west-1 |

## Retrieval in a new session: the task's scenario

[was_region_preference.png](../ScreenShots/was_region_preference.png): a new session
(`81c9deb2-7efc-42a6-b69f-86b3ee9d632e`, trace `6ad68b4e5c5aa9227428891c384ff076`, 2026-10-19) asks
"what is my prefered region" and the agent answers "Your preferred AWS region is eu-west-1."

| Start (UTC) | Span | ms |
| --- | --- | --- |
| 21:27:49.509 | `Bedrock AgentCore Control.GetMemory` (find the USER_PREFERENCE strategy) | 152 |
| 21:27:49.673 | `Bedrock AgentCore.ListMemoryRecords` (load the customer's preferences) | 177 |
| 21:27:50.722 | `chat` (answer) | 994 |

No tool was called: the preference stored at 19:37 in an earlier session came from long-term memory, loaded
into the system prompt when this session started.
