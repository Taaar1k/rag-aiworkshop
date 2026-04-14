# EXECUTION MODE POLICY

## Modes
- `light`: minimal overhead, fast execution loop.
- `strict`: full controls, expanded verification, tighter reporting.

## Use `light` when ALL true:
- Single objective with clear acceptance criteria.
- Low-risk change with limited blast radius.
- Few files and no contract/migration impact.

## Use `strict` when ANY true:
- Multi-step task with ambiguous requirements.
- High-risk or cross-file/cross-role impact.
- Changes affect governance contracts or role boundaries.

## Escalation
- Escalate from `light` to `strict` immediately if risk grows or unknowns appear.
- Downgrade only after complexity is resolved and documented.
