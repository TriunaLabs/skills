---
name: route-agent-message
description: Route a change or question from one working session to the relevant active agents or sessions, with per-recipient relevance decisions and accurate delivery receipts. Use when coordination spans concurrent work; does not manage project memory or assume that a selected recipient received or acted on a message.
license: MIT
---

# Route an agent message

Route one event to every active session that needs it. Keep discovery, relevance, routing policy, transport, and delivery evidence distinct.

1. Capture the event using [the event schema](references/event-and-recipient-schema.md). Require a source, concise summary, repository, evidence reference, requested action, and either changed paths or a topic. Do not embed secrets or unnecessary source content.
2. Discover active candidates from the available session listing and registry. Record each candidate's session ID, repository, task, component, branch, ownership patterns, dependencies, topics, and transport capability. Exclude the source session.
3. Run deterministic ownership and dependency rules first. Read [the routing policy](references/routing-policy.md) before changing thresholds or rules. Make a separate relevance decision for each ambiguous candidate; never collapse a multi-recipient event into one winner.
4. Use Laya by default. Select Jev or OpenAI Decisions only when configured and authorized. The scripts call a provider-neutral decision-service contract so native provider credentials and unpublished API details remain outside the skill. Low-confidence, unavailable, or malformed decisions are held for review rather than treated as relevant or irrelevant.
5. Create a short recipient-specific message containing the change or question, evidence pointer, requested action, source session, and why the recipient may be affected.
6. Deliver only through an available authorized transport. Read [transport capabilities](references/transport-capabilities.md) for the active environment. A routing selection produces `pending`, not `delivered`; record the real transport result as `delivered`, `held`, `unavailable`, or `failed`.
7. Return the route artifact and receipt summary. Report selected recipients, held candidates, unavailable candidates, provider/model/version, decision latency and cost when available, transport, and delivery status. Do not claim that delivery means the recipient read, accepted, or acted on the message.
8. When a human needs to inspect the route, render the same artifact as interactive HTML or Markdown. The visualization is observational: it must not recompute relevance, change selection, or imply delivery.

Use [`scripts/route-event`](scripts/route-event) to produce a deterministic route artifact and batch ambiguous candidates through the configured decision service. Use [`scripts/inspect-route`](scripts/inspect-route) to merge transport receipts and render JSON, Markdown, or a self-contained interactive HTML report:

```sh
python scripts/inspect-route route.json --receipts receipts.json --format html --out route.report.html
python scripts/inspect-route route.json --receipts receipts.json --format markdown --out route.report.md
```

The `samples/` directory contains the five-candidate API-contract acceptance scenario and representative delivery receipts.

LPC and SessionHandoff may consume emitted events through separate integrations. Do not make either system a dependency of this routing skill.
