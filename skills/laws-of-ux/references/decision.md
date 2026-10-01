---
description: "Choice and memory laws: Hick, Miller, serial position, Pareto. Read for menus, pricing, filters, and nav order."
connections: [expectation, gestalt, complexity, anti-patterns]
---

# Decision

These laws govern how many options a surface puts in front of someone, and which of those options survive memory. Pair with [expectation principles](expectation.md) when the issue is recognition rather than count, and with [Gestalt principles](gestalt.md) when the fix is visual chunking.

## Hick's Law

Decision time grows with the number and complexity of equivalent choices (Hick 1952, Hyman 1953). The relationship is roughly logarithmic, not linear. Equivalent is the load-bearing word: four buttons with the same weight are a Hick problem; one primary and three text links are not.

Flag: peer CTAs, plan grids, filter sets, or mega-menus where every option has the same visual weight.

Fix: cap a decision to a few peer options. Demote the rest. Recommend one. Do not hide the only path forward.

Do not cite for a single obvious action, or for a list the user is scanning rather than choosing from.

## Miller's Law

Working memory is small. Miller's 1956 7±2 is a channel-capacity remark that got turned into a UI quota. Cowan's later estimate is closer to 4 chunks. The usable rule is chunk, not "stop at seven."

Flag: a nav, feature row, or settings list of peer items with no grouping.

Fix: group into labeled chunks of about three to five. Phone numbers work because of chunks, not because 11 digits fit in memory.

Do not cite merely because a page has more than seven words on it.

## Serial position effect

People remember the first and last items in a series better than the middle. Put durable destinations at the ends. The middle is where items disappear.

Flag: the primary destination buried mid-nav; the recommended plan in the center of five equal cards with no other emphasis.

Fix: ends for the items that must stick. Combine with [expectation principles](expectation.md) von Restorff if one item also needs to look different.

## Pareto principle

A small share of actions covers most sessions. Give that share the weight. Do not design rare paths at the same volume as the common one.

Flag: a settings page or hero where a once-a-year action has the same prominence as the daily one.

Fix: design the common path. Park the long tail behind a progressive disclosure. This is a prioritization rule, not a license to delete a legally required path.

## Occam, as a choice rule

When two flows both complete the task, prefer the one with fewer assumptions. The complexity version lives in [complexity principles](complexity.md). Cite it here only to break a tie between two viable choice sets.

