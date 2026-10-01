---
description: "Pace and memory of the experience: Doherty Threshold, peak-end rule, Zeigarnik effect, goal-gradient. Read for waits, progress, and endings."
connections: [complexity, anti-patterns]
---

# Feedback

## Doherty Threshold

Interaction feels continuous when the system responds in a few hundred milliseconds. Doherty and Thadani (1982) put the figure near 400 ms. Past that, acknowledge immediately even if the work is not done.

Flag: a submit with no change of state; a spinner that appears late; a control that can be hit twice because nothing happened.

Fix: pending state on the control, optimistic UI where the action is reversible, a skeleton if the wait is for content. This is not a page-load SLA and not a license to fake success that you cannot roll back.

## Peak-End Rule

People judge an experience by its peak moment and its ending (Kahneman, Fredrickson, and others, 1993), not by the average of every step.

Flag: a blank thank-you; an error that blames the user and offers no repair; a flow whose best moment is a marketing illustration and whose end is a dead end.

Fix: spend the craft on the peak and the close. End on the outcome plus one next step. A painful middle with a clear ending is judged better than a smooth middle with a flat ending.

## Zeigarnik effect

Unfinished tasks stay mentally open (Zeigarnik 1927). Progress and "you left this draft" use that. A nag with no way back abuses it.

Flag: a multi-step flow with no sense of remainder; an abandoned draft with no return path; a badge that does not lead to the unfinished thing.

Fix: show what is open and how to close it. Do not open a loop you will not let the user finish.

## Goal-Gradient effect

Effort increases as the goal gets closer (Hull 1932, applied to loyalty and checkout). Show the remainder shrinking.

Flag: a static "step 1 of 5" that never feels closer; a progress bar that jumps backward.

Fix: remaining steps decrease. Do not inflate the early steps to manufacture a late surge.

