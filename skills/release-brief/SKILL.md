---
name: release-brief
description: Write user-facing release notes from an explicit Git revision range and linked issue evidence. Use when preparing release communication; does not create tags or publish releases.
license: MIT
---

# Release brief

Translate a verified change range into a useful release brief.

1. Establish the base and target revisions and intended audience. Resolve both refs before inspecting changes. If no range is supplied, inspect available tags and ask which release boundary to use when ambiguous.
2. Read the commit summary and substantive diff. A merged commit is evidence of a change, not proof that it shipped or passed testing.
3. Group entries by user-visible outcome. Exclude mechanical refactors unless they affect users. Explain breaking changes with the old behavior, new behavior, and migration action.
4. Link claims to commits or supplied issues. Keep uncertain deployment status and unverified performance claims out of factual release bullets.
5. Use [the brief template](assets/release-brief.md) when there is no repository convention. List known limitations separately and label the result as a draft until the user publishes it.

Do not create a tag, release, announcement, or outbound message from a request to draft notes.
