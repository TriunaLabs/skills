---
name: answer-ready-web
description: Audit or create a landing page that clearly answers buyer questions, exposes crawlable semantic content, and ties consequential claims to visible evidence. Use for product, service, consulting, or open-source landing pages and for SEO/AI-search readiness reviews; does not promise rankings or citations.
license: MIT
---

# Answer-Ready Web

Make a page useful and quotable for people first, while preserving the technical clarity that search engines and retrieval systems need.

Choose the smallest mode that satisfies the request:

- **Audit:** inspect an existing URL or local HTML and produce a scored report plus prioritized fixes.
- **Improve:** edit the supplied page in its existing design system, preserving its voice and working behavior.
- **Create:** build a new page from verified product, audience, evidence, and conversion inputs.

For a deterministic baseline, run:

```sh
python scripts/audit_page.py /path/to/page.html --format html --output /path/to/page.answer-ready.html
python scripts/audit_page.py https://example.com/product --format markdown --output audit.md
```

Resolve the script relative to this skill folder. URL analysis requires network access; prefer a local source file when the page is part of the current workspace. The analyzer identifies signals and review targets. It cannot establish search intent, factual truth, indexation, or citation performance by itself.

## Working rules

1. Identify the page's primary audience, decision, and likely question. An H1 may be a question or a direct proposition; do not force query-shaped copy when a clearer heading exists.
2. Put a concise, plain-language answer or value proposition near the top. Treat 40–60 words as a useful pattern, not a quota.
3. Organize the page around the reader's decision path: problem, fit, method, evidence, alternatives or tradeoffs when relevant, cost or next step, and objections.
4. Keep essential information in crawlable text with a logical heading hierarchy, descriptive links, useful image alternatives, canonical metadata, and functional no-JavaScript reading order.
5. Create structured data only for entities and facts visibly supported by the page. Structured data can improve machine understanding; it does not guarantee a rich result, ranking, or AI citation.
6. Build a claim ledger before strengthening marketing copy. Never invent customers, testimonials, benchmarks, reviews, credentials, prices, dates, or performance results. Mark missing support plainly.
7. Use a semantic table only when readers truly need to compare stable attributes. Do not manufacture competitors or pretend unlike offers are equivalent.
8. Write FAQs from real objections or support questions. Do not add FAQ schema merely as an optimization tactic; Google retired FAQ rich results in 2026.
9. Show authorship or organizational ownership when it helps readers judge expertise and accountability. Do not add a ceremonial byline to transactional pages where it has no user value.
10. Use a visible updated date only when the page has actually been reviewed. Keep any `dateModified` value consistent with that visible date.

Read [the review rubric](references/review-rubric.md) when interpreting scores or planning an audit. Read [content and evidence](references/content-and-evidence.md) when drafting or rewriting. Read [technical and structured-data guidance](references/technical-and-structured-data.md) before changing HTML metadata, schema, crawl controls, or AI crawler rules.

## Deliverables

An audit should include the primary audience/question inference, dimension scores with observed evidence, a claim-readiness ledger, critical issues, and fixes ordered by likely user impact. Distinguish deterministic observations from editorial judgment.

A created or improved page should include the actual HTML or Markdown, supported structured data where useful, and a short change ledger. Preserve the site's existing components and brand unless the user requested a redesign. Validate links, headings, metadata, structured data syntax, responsive behavior, focus states, and the page without JavaScript before reporting completion.

Never describe a page as "AI-optimized," "citation-ready," or "SEO-ready" solely because it passes the checklist. Say what was verified and what still requires Search Console, analytics, user research, or external testing.
