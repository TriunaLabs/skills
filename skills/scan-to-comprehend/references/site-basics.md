# Page basics beside an S2C audit

The orchestrated URL run writes `site-basics.json` and a **Page basics** report section. This layer is intentionally separate from the S2C browser checklist, source structural-friction index, and experimental attention estimate. It supplies evidence for triage, not a new composite grade.

| Check | Basis | Interpretation |
| --- | --- | --- |
| Response wait, DOM ready, load event | Chromium Navigation Timing in each of the desktop, mobile, and 320 px navigations | One synthetic audit run. `responseStart − requestStart` is a response-wait signal; this is not field TTFB or a Core Web Vitals assessment. |
| Resource count | Resource Timing entries visible when the capture is taken | A partial count, not total page weight; cross-origin byte sizes are often unavailable. |
| In-page fragments | Captured links compared with IDs and named anchors on the same rendered document | A missing target is a concrete broken fragment for that page state. |
| Same-origin page links | At most eight unique, visible, query-free links tested with `HEAD`, no redirects | 404/410 is **possible broken**, requiring a normal browser confirmation. 403, 405, 429, 5xx, DNS, and TLS failures are inconclusive. External and unsampled links are not checked. |
| Contact, privacy, and terms discovery | Visible link text and destinations in the captured page | A missing route is a **review item on this page**, not proof that the information is absent sitewide or that any law has been violated. Terms may not be needed for every page. |

The link probe resolves and pins a public IP for each same-origin request, uses a three-second timeout, does not follow redirects, and never sends a GET or a query-string URL. The local playground runs it by default for a fresh public URL; offline replay preserves the capture but performs no network probes. A public multi-tenant deployment also needs a hardened egress boundary, request budgets, abuse controls, and an ownership and export policy before enabling wider crawling.

Record capture date, viewport, final URL, sampled-link count, and skipped scope beside the findings. Do not imply that these signals measure usability, legal compliance, or real-user speed. For a performance diagnosis, use a dedicated trace and field data where available. [Navigation Timing](https://developer.mozilla.org/en-US/docs/Web/API/Performance_API/Navigation_timing) and [web.dev's distinction between synthetic and field measurements](https://web.dev/articles/navigation-and-resource-timing) explain the basis.
