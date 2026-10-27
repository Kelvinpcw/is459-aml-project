# Q2 local validation — first minute only

26 October 2026, Singapore. **PASSED locally; no Q2 cloud deployment or execution yet.**

| Check | Result |
| --- | --- |
| Full local test suite | 30 passed, including 12 Q2 tests |
| Immutable input | Both selected transaction/account gzip SHA256 values match ingestion manifest |
| Declared scope | 1 September 2022 00:00 inclusive to 00:01 exclusive; cutoff 00:01, dataset-local time |
| Scoped transactions | 43,681 |
| Self transactions excluded from graph | 31,702 |
| Non-self transactions / distinct directed pairs | 11,979 / 11,760 |
| Leads | 15 fan-out; 0 fan-in; 0 cycles of length 2–4 |
| Supporting transactions | 840 distinct source IDs, every case independently reconciled to all supporting source rows |
| Unknown mappings / truncation | 0 / none |
| Largest bundle / all bundles | 218,819 / 602,619 bytes |

Fan-out requires at least five distinct non-self receivers. Same-looking transactions keep distinct original source IDs. Cases are investigation leads; no labels or pattern annotations were used and no detection-quality metric has been calculated.

The first minute was chosen chronologically from label-free workload sizes. No real-data cycle exists in this tiny window. Cycle logic is verified against a separate exhaustive oracle and 2/3/4-account fixtures; that is not evidence of cycle detection performance across the development period. No wider-window, holdout or full-dataset claim is supported.

Spark validates/filter inputs and a guarded small window is collected for deterministic graph assembly. This bounded driver implementation is not ready for unbounded full-day graphs. All limits fail the whole analysis without clipping cases or evidence. The separate evaluator, full architecture release gate, dashboard and Step Functions are not implemented.

Machine-readable inventory/config/input checksums/bundle SHA256 values: `../aws/reviews/q2-local-replay-m00-v1.json`. Complete local bundles: `../data/q2-local-m00-v1/`. Frozen detector: `../releases/q2-v1/q2_detect-v1.py`. Cloud readiness/access scope: `../Q2_READINESS.md`.
