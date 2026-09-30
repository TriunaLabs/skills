---
name: reproduce-bug
description: Create a minimal, repeatable bug reproduction and a regression check from an observed failure. Use when a bug report lacks a reliable reproduction or a fix needs targeted verification.
license: MIT
---

# Reproduce a bug

Reduce uncertainty before changing the implementation.

1. Extract expected and observed behavior, input, environment, and the first known failing version. Keep the reporter's facts separate from hypotheses.
2. Inspect the smallest relevant code path and existing test conventions. Preserve original inputs and work in temporary fixtures when reproduction writes data.
3. Attempt the reported steps, recording the exact command, environment, and observable output. If reproduction fails, say so; vary one plausible factor at a time rather than claiming the bug is fixed.
4. Reduce the case until removing another input or setup step stops reproducing it. Preserve the condition that causes the failure, especially clock, locale, concurrency, or ordering dependencies.
5. Add a regression check at the lowest useful layer. Confirm it fails on the defective implementation for the expected reason. If a fix is requested, make it and confirm the same check passes; report unrelated failures separately.

Use [the reproduction template](assets/reproduction.md) for a handoff. Do not include credentials or identifiable production records in fixtures.
