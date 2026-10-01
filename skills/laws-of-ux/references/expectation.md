---
description: "Expectation and distinctiveness: Jakob's Law, Postel's Law, von Restorff. Read for convention, input tolerance, and emphasis."
connections: [decision, motor, complexity, anti-patterns]
---

# Expectation

## Jakob's Law

Users spend most of their time in other products, so they expect this one to work the same way (Nielsen). Convention is the default. Novelty has to pay for the relearning.

Flag: a logo that is not home, a cart or settings control in an invented place, nav labels that rename standard destinations, a checkout that hides the total.

Fix: reuse the category convention. Keep novelty for the part that is actually different.

Do not cite Jakob to freeze a bad pattern the category already regrets. Cite it when the user will bring a specific expectation and the page breaks it.

## Postel's Law

Be liberal in what you accept, conservative in what you send (Postel, RFC 760). For UI: accept the formats a reasonable person will type, normalize them, and display a clean value. Do not reject a phone number for a missing hyphen.

Flag: format errors on input the user could not have predicted; paste rejected for whitespace; a date field with one unspoken format.

Fix: accept, trim, normalize, then show the canonical form. Keep the error for values that are actually impossible.

Do not use Postel to excuse a sloppy payload sent to another system. Output stays strict. Complexity of the tolerant parser belongs with the system, per [complexity principles](complexity.md) Tesler.

## Von Restorff effect

The item that differs from its peers is the one remembered (von Restorff 1933). Also called the isolation effect.

Flag: every plan highlighted; every nav item bold; a single important action that looks like its neighbors.

Fix: one emphasized item. If everything is emphasized, nothing is. Combine with serial position in [decision principles](decision.md) when order and contrast are both wrong. Do not emphasize a destructive action just to make it memorable.

