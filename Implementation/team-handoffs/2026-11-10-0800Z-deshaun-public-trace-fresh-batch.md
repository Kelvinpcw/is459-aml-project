# Task: Verify a new BQ2 batch on public TRACE

- **Owner:** Deshaun (request and presentation); Codex (execution).
- **Branch:** `agent/codex-trace-fresh-public-proof`.
- **Status:** PLANNED
- **Evidence kind:** Preflight inspection.

## Scope and coordination

Run one new synthetic day through the main workflow's Daily BQ2 route. Verify it reads the day’s ready manifest, runs the deployed Glue stages with the saved models, and publishes results visible on the existing public TRACE site. After verifying the test, restore the previous presentation release only if the test still owns the current pointer. Leave immutable release outputs intact.

## AWS scope and cleanup

No workflow, dashboard, IAM or schedule changes. Exact run and release locators, compute measurements and screenshots stay in the private operator record.

## Next teammate / agent

Confirm the date is unused, both workflows are idle, and the published pointer is unchanged before starting. Post the observed result and cleanup state here.
