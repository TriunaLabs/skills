# S2C as a Triuna Labs tool

**Decision direction · October 27, 2026.** Present Scan to Comprehend as a public, evidence-rich visual audit and research demonstration on `triunalabs.com/tools/scan-to-comprehend/`. Keep the current portable skill and deterministic core in GitHub. Use the same versioned JSON artifacts for the website, CLI, API, and an eventual MCP adapter. Treat calibrated gaze prediction and commercial workflow features as research or later products until they are validated.

## Public experience

1. A visitor pastes a public URL, or uploads one self-contained HTML prototype, plus an optional reader question and up to five phrases they want crawlers to find. The free result shows dated screenshots, a short prioritized action list, browser checklist, page basics, robot visibility, source structure, assistive paths, and explicitly experimental attention and retrieval views. A final action plan collects every flagged item.
2. Every number opens its rule, evidence, viewport, capture date, and limits. The report keeps a visual route from a finding to the actual page region or DOM element. An editable scoring profile can create a new revision from a saved capture without recrawling.
3. Link directly to the [open skill source](https://github.com/TriunaLabs/skills/tree/main/skills/scan-to-comprehend), the method and held-out evaluation, reproducible case studies, and the ongoing `gaze-element-map` research once that separate repository has a verified public URL. The current Triuna Labs page already links to the skill and examples; add the live audit entry point only when public deployment has its URL intake and storage policy.
4. Keep the unauthenticated scan bounded. Accounts can later add private reports, longer retention, exports, saved comparison history, team workspaces, and verified site ownership. An unauthenticated report should have a clear retention period and should not imply the submitter owns the URL.

## Product boundary

The free tool demonstrates S2C's distinctive work: comprehension-oriented structure, annotated page evidence, reading order, customizable rubrics, and honest research limits. Page speed, broken links, contact routes, privacy links, and terms links are useful adjacent hygiene checks, displayed separately rather than folded into a synthetic comprehension score. A missing homepage link is a discovery gap, not proof that the business lacks a policy. A single browser run is synthetic, not real-user Core Web Vitals.

Robot visibility is another separate check. Raw-versus-rendered differences, `noindex`, and possible `robots.txt` blocks are review candidates, not proof of search invisibility. Confirm high-impact findings with the target crawler's inspection tool. An HTML upload has no live response headers, `robots.txt`, or HTTP performance, and its scripts and external resources are disabled in the local pilot.

PulseLocalIntel's [public site](https://www.pulselocalintel.com/) describes Google Places lead discovery, contact email finding, a website health score, desktop/mobile website quality and performance signals, review data, platform/booking/tracking/trust/social detection, outreach drafts, and a pipeline. Its public copy does not expose the exact scan rules or validate the advertised outcomes. S2C should make its rule evidence and limitations inspectable instead of competing first on lead volume or CRM features.

## Technical path

| Layer | Near-term shape | Release condition |
| --- | --- | --- |
| Core | Versioned Python CLI and schemas in the public skill repository | Deterministic replay, tests, reproducible sample reports, stable finding IDs. |
| Website tool | Queue URL audit jobs, return a run ID, then show report and scoring revisions | Public egress isolation, public-IP and redirect validation at each hop, rate limits, size/time budgets, abuse controls, retention, and audit logs. |
| API | Document the existing local run/status/artifact concepts as a versioned job API | Authentication, quotas, idempotency, storage policy, and OTEL traces with bounded URL and content attributes. |
| MCP | A thin adapter over that API for `submit_audit`, `get_status`, `get_findings`, and `get_report` | Same authorization and result schema as API; clear tool descriptions, no special scoring logic. |
| Plugin | Package only after the API and MCP use cases are proven | Stable credentials, permissions, support expectations, and a useful host-specific workflow. |
| Later products | Team history, monitored regressions, consented on-page interaction signals, and calibrated attention research | Separate evidence and evaluation before predictive claims or paid scoring. |

For public deployment, keep OTEL from the start: stage spans for fetch, capture, link checks, projections, scoring, and rendering; counts and duration as attributes; avoid raw page text or query strings in telemetry. The current local playground already has a small job API and optional OTLP export in the runner, but is loopback-only and should not be exposed directly.

## Initial release and billing decision

Use the existing [public TriunaLabs/skills repository](https://github.com/TriunaLabs/skills) as the v1 source and the Triuna Labs S2C page as the method, case-study, and tool entry point. Publish the deterministic CLI, schemas, and example reports first. Run a limited free hosted URL/HTML beta only after the security and policy gates above. Do not launch a paid subscription or distribute API keys against the current loopback server.

The paid service can follow observed demand: free limited scans; a subscription for private history, exports, scheduled comparisons, team workspaces, and higher API quotas. Stripe should handle checkout, recurring billing, and the customer portal. Server-side webhooks, not a success-page redirect, should update the internal entitlement state. Triuna Labs should issue **its own** scoped, hashed S2C API keys to accounts; Stripe secret keys stay server-side and are never given to MCP or plugin clients. Start with one versioned API contract; MCP is a thin authenticated adapter over the same jobs, findings, and report endpoints. Defer a host-specific plugin until API use cases justify maintaining it. See [Stripe Checkout fulfillment](https://docs.stripe.com/payments/existing-customers?platform=web&ui=stripe-hosted), [customer portal](https://docs.stripe.com/payments/checkout/pricing-table), and [API key types](https://docs.stripe.com/keys).

Before a hosted upload or saved report is offered, extend the existing Triuna Labs [privacy policy](https://triunalabs.com/privacy/) and [terms](https://triunalabs.com/terms/) with the actual S2C data path: submitted URLs, uploaded HTML and screenshots, retention and deletion, whether reports are public or private, provider access, site ownership claims, acceptable scanning, and subscription terms. Set these from deployed behavior and have the final legal language reviewed. The current local pilot stores extracted evidence and reports on this computer until manually removed; it must not promise public-service retention it does not yet enforce.

## Interface direction

Paul prefers shadcn/ui's composable controls and Extend.ai's technical, confidence-oriented visual style. Use the user-supplied redesigned audit as the report reference: sticky navigation, light canvas, strong typographic hierarchy, compact metric cards, prominent action cards, and evidence sections. The report generator now uses that shell direction; the public tool should use the same design tokens and interaction states without copying either external site's assets or branding.
