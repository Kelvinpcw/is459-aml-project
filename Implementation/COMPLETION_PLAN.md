# Completion plan — 28 October 2026

The user requested completion of the whole project, then a full-data run with a **US$30 total project ceiling** (revised by the user from US$80 before the paid full run) after implementation and checks. The earlier US$1 ceiling applies to the current development phase until that final run. This is authorisation for the scoped project, not unrelated account resources. Keep explicit identity verification, timeouts, no recurring schedules and cleanup after validation. Actual spend is not a hard billing cap.

1. Shared release gate: pinned quality/identity/output checks, conditional immutable release and compare-and-swap current pointer; failed attempts retain the previous release. Label the existing mixed one-day/one-minute release as a pilot.
2. Dashboard: Q1 date/currency/format/segment filters, honest support/denominator warnings; Q2 bounded graph and full evidence download; all reads pinned to one release. Read-only role and private on-demand EC2 through SSM.
3. Scalable Q2: Spark aggregations/pruned 2–4-cycle joins over complete lookbacks, distributed cases/evidence; declared exclusion accounting and expansion guards. Preserve the frozen pilot.
4. Wider evaluator: distributed eligible-population metrics, exact annotation source matching, frozen development calibration before holdout. No performance claim from the pilot.
5. On-demand Step Functions workflow, per-stage failure paths, publication/recovery checks and reproducible deployment/teardown.
6. Full input accounting and final costed AWS run up to the authorised US$30 total; runtime/cost/quality/evaluation/UI validation, user-test/demo runbook and cleanup. Flag material changes before starting.

Completion means tested working components and an observed full-data result, with limitations and unmet acceptance targets stated. Local tests/configuration alone are not a deployed full run.

## Current progress

Publication and pilot pointer are deployed; the read-only dashboard passed application tests against the live pilot. All 67 local regressions and additional export/cycle/baseline checks passed. Frozen `full-v1` code and all raw inputs were uploaded and independently verified. The exact roles/deployment were approved by the user. The on-demand full workflow is running; full preparation has passed for all 31,898,238 transactions and 35,230 labels. Full Q1/Q2, evaluation, publication, temporary EC2 validation, measured full metrics/runtime and cleanup remain in progress. Read the latest checkpoint/monitor before any cloud action; do not restart completed stages.
