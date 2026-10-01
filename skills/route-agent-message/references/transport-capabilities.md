# Transport capabilities

Routing and delivery are separate operations. Discover the tools available in the current environment and use only an authorized transport.

| Transport | Suitable target | Receipt boundary |
| --- | --- | --- |
| Codex agent-tree messaging | A known live subagent in the current task tree | Tool accepted the message for that target |
| Codex task messaging | An existing accessible Codex task identified by task ID | Codex accepted the user-visible follow-up |
| Claude peer messaging | A reachable Claude session when the runtime exposes peer tools | Runtime accepted the peer message |
| External adapter | Independently launched sessions registered with an adapter endpoint | Adapter-specific accepted/failed result |
| No available transport | Candidate is relevant but cannot currently be reached | `unavailable`; preserve the proposed message |

Before sending, verify that the target ID still represents the intended session and that the user has authorized messaging in the current task. Deduplicate by event ID, recipient ID, and evidence reference. Do not retry indefinitely; record failure after the transport's bounded retry policy.

Use this concise message shape:

```text
Change: <event summary>
Evidence: <stable evidence reference>
Action: <requested action>
Why you: <ownership, dependency, or accepted relevance decision>
Source: <source session>
```

Never put provider credentials, raw private context, or unrelated session content into a routed message. Acknowledgment and action are later events, not properties inferred from delivery.
