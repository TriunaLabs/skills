# Local API, MCP, and explicit reader journeys

The local playground at `http://127.0.0.1:8787/` keeps each run on the user's computer. `POST /api/runs` accepts one public URL or one `.html` prototype. `GET /api/runs/{run_id}` returns status; `GET /api/runs/{run_id}/result` returns the deterministic [result schema](api-result.schema.json) after completion; `/report` returns the HTML report. The local service has no account boundary or remote access and must stay on loopback. Results are not evidence of domain ownership.

The optional stdio MCP adapter uses the same runner. Install `integrations/requirements-mcp.txt`, then register `python integrations/mcp_server.py` from this skill directory in a local MCP host. It exposes `audit_public_url` and `audit_html_prototype`. The adapter caps saved runs at ten in its local output directory under the system temporary directory unless `S2C_MCP_RUN_ROOT` is set. It sends no model request or telemetry by default. It is not a hosted or authenticated MCP endpoint.

For a role task, create a [scenario JSON](journey-scenario.schema.json) with a role, goal, optional same-origin target, required phrases, and success-action label. Run:

```text
python scripts/s2c_journey.py --site-graph graph.json --scenario task.json --snapshot capture/snapshot.json --output journey-output
```

The evaluator searches only fetched page titles/headings and visible elements in the captured start viewport. It compares routes through initial HTML and a rendered start-page overlay. Each phrase and action has evidence or a review/not-checked state. The role is an explicit task framing input; the program does not infer gaze, motivation, task success, or comprehension from a persona label. A changed scenario should be saved as a new JSON revision.

For live URL capture, the browser now receives public-IP-pinned same-origin GET responses with a request and byte cap. Cross-origin assets, non-GET requests, and WebSockets are blocked. The report records counts and this rendering limitation. A live URL run checks `robots.txt` before fetching content. This local guard is defense in depth; a publicly hosted arbitrary-URL service still needs an isolated browser runtime, ingress controls, abuse limits, private artifact storage, retention, and end-to-end telemetry checks.
