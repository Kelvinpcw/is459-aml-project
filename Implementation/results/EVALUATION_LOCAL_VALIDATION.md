# Q2 evaluator local development validation

27 October 2026. **Local PASSED; not deployed or run in AWS.**

| Measurement | Detector | Matched-volume amount diagnostic |
| --- | ---: | ---: |
| Eligible transactions in frozen first minute | 43,681 | 43,681 |
| Positive historical labels in that population | 0 | 0 |
| Distinct alerted source transactions | 840 | 840 |
| Labelled true-positive transactions | 0 | 0 |
| Transaction precision | 0 | 0 |
| Recall / lift | Not measurable: zero positives | Not measurable: zero positives |
| Eligible annotated attempts / recovery | 0 /not measurable | 0 /not measurable |

All 2,756 annotations fall outside 00:00–00:01; the earliest annotated transaction is00:08. All 15 frozen cases are fan-out leads and all840 supporting transactions have label0. These are transaction-label measurements, not case-level truth. Annotation absence never makes a case false. The window/threshold was not changed after viewing references.

The complete source gzip checksum and full 4,465,985 transactions/1,056 positives/per-format counts reconcile with passed preparation. Annotation checksum verified. The evaluator checks the complete eligible population and preserves same-looking legitimate source records. The baseline ranks paid amounts within payment currency at exactly matched per-currency alert counts, using source-ID ties. It is an evaluation diagnostic, not a calibrated holdout rule.

All 49 current tests are covered:30 earlier regressions,19 evaluator tests, including Spark full-input joins, overlap deduplication, annotation eligibility/ambiguity, correct type/hub/oriented cycle, exact80% recovery in one case, missed attempts in denominators, zero denominators, immutable cases and zero-case Parquet. A final formatting-specific assertion also passed. No new AWS services or paid runs were started.

This validates evaluator mechanics for a tiny development pilot. It cannot assess useful detector recall, annotated-pattern recovery or improvement over baseline. Wider scalable Q2, development calibration and frozen holdout evaluation remain outstanding.

Detailed ready-to-review contracts/access/run plan: `../EVALUATION_READINESS.md`. Compact results/provenance/artifact hashes: `../aws/reviews/evaluation-local-m00-v1.json`. Full output artifacts: `../data/evaluation-local-m00-v1/`. Shared release gate, dashboard and orchestration remain unimplemented.
