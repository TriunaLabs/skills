# Release evidence policy

## What Git establishes

An explicit range establishes commit membership, file changes, authored commit text, and line statistics. It does not prove that code shipped, tests passed, an issue is resolved in production, a migration is safe, or a performance claim is true.

## Claim rules

- Trace every release entry to at least one commit ID.
- Treat issue references found in commit text as unverified until a supplied issue record matches the ID.
- State test and deployment results only from supplied records with evidence references.
- Treat conventional-commit categories and keyword risks as deterministic routing signals, not semantic proof of user impact.
- Put absent verification, deployment, rollback, and breaking-change migration details in `evidence_gaps`.
- Keep performance quantities, security guarantees, and compatibility claims out unless their evidence is supplied.

## Optional semantic review

A later Laya, Jev, or OpenAI Decisions adapter may propose bounded categories such as `user_visible`, `operator_only`, `internal`, or `uncertain`. Such review must remain advisory, carry provider/model/version/confidence provenance, and never override Git membership or verification evidence.
