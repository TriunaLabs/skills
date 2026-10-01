# Event, registry, decision, and receipt schemas

## Event

```json
{
  "id": "evt-auth-response-v2",
  "source": {"session_id": "api-session", "agent": "codex"},
  "summary": "The authentication response now returns session.expires_at.",
  "repo": "platform",
  "branch": "feature/auth-v2",
  "components": ["api:auth"],
  "changed_paths": ["packages/api/openapi/auth.yaml"],
  "topic": "authentication response contract",
  "evidence_ref": "commit:abc123",
  "requested_action": "Review the contract and update affected consumers."
}
```

Required fields are `source.session_id`, `summary`, `repo`, `evidence_ref`, and `requested_action`. Supply at least one nonempty `changed_paths` entry or `topic`. `components`, `branch`, and `id` are optional. Use stable repository and component identifiers shared by the registry.

Labeled evaluation fixtures may include `expected_recipients`. Do not populate it during live routing: it represents ground truth used to calculate missed recipients and unnecessary messages after the route is produced.

## Active-session registry

```json
{
  "sessions": [
    {
      "session_id": "mobile-session",
      "active": true,
      "agent": "codex",
      "repo": "mobile-client",
      "branch": "main",
      "task": "Maintain mobile authentication",
      "components": ["client:mobile"],
      "owned_paths": ["apps/mobile/**"],
      "depends_on": ["api:auth"],
      "topics": ["authentication", "mobile"],
      "transport": {"kind": "codex-thread", "target": "thread-id"}
    }
  ]
}
```

`active` must be a Boolean. Ownership patterns use shell-style glob matching. `components`, `owned_paths`, `depends_on`, and `topics` are arrays of strings. Transport configuration is descriptive; the routing script does not claim delivery on its own.

## Decision-service request

The router batches only ambiguous candidates:

```json
{
  "schema_version": "1.0",
  "provider": "laya",
  "question": {
    "type": "choice",
    "instructions": "Decide whether this candidate session needs this event.",
    "answers": ["relevant", "not_relevant", "uncertain"]
  },
  "event": {},
  "candidates": [{"candidate": {}, "signals": {}}]
}
```

The service returns:

```json
{
  "provider": "laya",
  "model": "pinned-model-name",
  "version": "model-or-adapter-version",
  "decisions": [
    {
      "candidate_id": "mobile-session",
      "answer": "relevant",
      "confidence": 0.91,
      "probabilities": {"relevant": 0.91, "not_relevant": 0.06, "uncertain": 0.03},
      "latency_ms": 18,
      "cost_usd": 0
    }
  ]
}
```

Confidence and probability fields are optional because provider contracts differ. When confidence is missing, the decision is held unless the configured adapter supplies an evaluated acceptance policy.

## Transport receipts

```json
{
  "receipts": [
    {
      "recipient_id": "mobile-session",
      "status": "delivered",
      "transport": "codex-thread",
      "attempted_at": "2026-09-30T23:00:00Z",
      "latency_ms": 42,
      "detail": "Message accepted by transport."
    }
  ]
}
```

Allowed statuses are `delivered`, `held`, `unavailable`, and `failed`. `delivered` means the transport accepted the message; it does not mean the recipient read or acted on it.
