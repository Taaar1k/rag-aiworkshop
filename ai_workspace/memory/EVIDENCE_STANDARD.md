# EVIDENCE STANDARD

## Minimum Proof Bundle (required for DONE)

1. **Scope proof** — which files changed and why.
2. **Execution proof** — at least one verification command/check and its result.
3. **Outcome proof** — what now works that did not work before.
4. **Residual risk** — any unverified path, assumption, or deferred validation.

## Light vs Strict

- **Light:** minimal scope proof, one targeted verification, short outcome proof.
- **Strict:** full scope proof, multiple verifications, explicit risk and rollback notes.

## Reject DONE if:
- Verification is missing or irrelevant.
- Evidence references files not actually changed.
- Outcome is asserted without observable proof.
- Residual risks are hidden for high-risk changes.

## Evidence Template
```md
## Evidence Bundle
- Scope: [files changed, rationale]
- Execution: [command/check, result]
- Outcome: [what works now]
- Residual risk: [remaining risk, follow-up]
```
