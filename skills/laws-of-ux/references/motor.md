---
description: "Fitts's Law and target distance. Read for button size, placement, and gaps between hit areas."
connections: [expectation, anti-patterns]
---

# Motor

## Fitts's Law

Time to acquire a target depends on distance and size (Fitts 1954). Bigger and closer is faster. Gap between adjacent targets matters as much as size, because the effective target shrinks when neighbors can be hit by mistake.

"Minimize target distance" is this rule, not a separate law. Cite Fitts.

Flag:

- Primary action small, or far from the field the user just filled.
- Icon-only hit area with no padding.
- Destructive action larger than the primary action.
- Adjacent targets with a gap smaller than the pointing error.

Fix:

- Enlarge the primary target and move it next to the current focus.
- On a pointer, corners and edges are cheap because the screen stops the cursor. On a thumb, place high-frequency controls in the natural arc, not the top corner.
- Keep a gap between neighbors. Do not make the dangerous action the easiest one to hit.

Do not cite Fitts for a labeling problem, a color problem, or a choice-count problem. Those are [expectation principles](expectation.md) or [decision principles](decision.md). Accessibility minimums (about 24 CSS px) are a conformance floor owned by an accessibility skill. Fitts still wants the primary action larger than that floor.

