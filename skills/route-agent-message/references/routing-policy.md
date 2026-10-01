# Routing policy

## Order of authority

1. Explicit recipient declarations and exact ownership rules.
2. Component dependency and changed-path ownership rules.
3. A bounded decision for each ambiguous active candidate.
4. A confidence gate and hold-for-review fallback.
5. Transport delivery and its independent receipt.

Do not let a decision provider override an explicit exclusion, inactive status, or deterministic ownership match. Keep one decision per candidate so an event can reach several recipients.

## Default provider policy

`route-event` defaults to `laya`. The default endpoint is read from `ROUTE_AGENT_DECISION_URL`, falling back to `http://127.0.0.1:8791/v1/route-decisions`. A decision service may instead be selected with `--provider jev` or `--provider openai-decisions`; the endpoint adapter must accept and return the provider-neutral schema.

Use `--config` for a JSON object such as:

```json
{
  "provider": "jev",
  "threshold": 0.82,
  "decision_service": {
    "endpoint": "https://router.example/v1/route-decisions",
    "api_key_env": "ROUTE_AGENT_API_KEY",
    "timeout_seconds": 20
  }
}
```

Do not put API keys in the configuration file. The router reads the named environment variable only when calling the configured endpoint.

The OpenAI Decisions API adapter remains external until OpenAI publishes and stabilizes its public request and response contract. Do not infer a native endpoint or convert a normal generative response into a claimed Decisions API result.

## Acceptance and fallback

- Accept `relevant` only when confidence meets the configured threshold.
- Accept `not_relevant` only when confidence meets the threshold.
- Hold `uncertain`, missing, malformed, or low-confidence results.
- If the decision service is unavailable, preserve deterministic routes and hold ambiguous candidates. Include the error in the route artifact.
- Version the question wording, provider adapter, model, threshold, and evaluation set together before trusting automatic delivery.

Evaluate against labeled routing events. Track missed recipients, unnecessary messages, decision coverage, delivery success, latency, and cost. Missed recipients are the primary error; tune thresholds against the interruption cost of unnecessary messages.
