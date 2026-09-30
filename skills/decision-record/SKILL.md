---
name: decision-record
description: Turn an engineering decision into a concise, evidence-backed decision record. Use when comparing implementation options or documenting a consequential technical choice.
license: MIT
---

# Decision record

Capture a decision another engineer can revisit without reconstructing the conversation.

1. Identify the actual decision, constraints, owner, and deadline from the request. Separate hard constraints from preferences; ask only about unknowns that could reverse the choice.
2. Inspect relevant project evidence. Compare the current approach and credible alternatives against the same criteria, including operational cost and reversibility. Do not invent measurements or vendor guarantees.
3. Recommend an option and explain the strongest reason against it. State what evidence would change the recommendation.
4. Use [the record template](assets/decision-record.md) if the project has no established format. Mark undecided items explicitly. A recommendation is not an approved implementation decision.
5. Deliver the record with source links, unresolved questions, and a concrete revisit trigger. Write it to the requested destination; do not change implementation as part of documentation alone.
