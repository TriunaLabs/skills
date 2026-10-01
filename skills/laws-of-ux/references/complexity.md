---
description: "Complexity budget: Tesler's Law, Parkinson's Law, Occam's Razor. Read when a flow grew, or when the user is holding steps the system could hold."
connections: [decision, expectation, anti-patterns]
---

# Complexity

## Tesler's Law

Complexity is conserved. Also called the law of conservation of complexity (Tesler). The design choice is who holds it — the system, or the user — not whether it exists.

Flag: a required choice pushed to the user that a default, a derivation, or an earlier answer could have settled; instructions that exist to explain a step the product added.

Fix: absorb the step with a smart default, inline derivation, or a tolerant parser (see [expectation principles](expectation.md) Postel). Hiding a required choice is not the same as absorbing it. If the user must decide, surface the decision where it happens.

## Parkinson's Law

Work expands to fill the time allowed. In UI, a form, settings page, or onboarding expands to fill the space and the sprint.

Flag: a field set that grew because there was room; optional questions asked with the same weight as required ones.

Fix: cap fields and steps on purpose. A limit is a product decision. Pair with Pareto in [decision principles](decision.md) to decide what the cap keeps.

## Occam's Razor

Prefer the explanation or the design with fewer assumptions. In a review, this breaks a tie: if a simple flow and a clever flow both complete the task, ship the simple one.

Flag: an extra mode, state, or branch that exists for a case no one has hit.

Fix: delete the branch until a real case needs it. Do not cite Occam to remove a safeguard the domain requires.

