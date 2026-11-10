# Verify a fresh BQ2 batch on public TRACE

- **Owner:** Deshaun (request and presentation); Codex (execution).
- **Branch / PR:** [#33](https://github.com/Kelvinpcw/is459-aml-project/pull/33).
- **Status:** COMPLETED
- **Evidence kind:** AWS execution history, S3 readback and live browser verification on 10 November 2026.

One manual Daily BQ2 execution of the main Step Functions workflow picked up the new synthetic day's S3 manifest. All five Glue jobs succeeded: Prepare, Detect, Score and Rank, Evaluate, and Publish. The run honored the exclusive cutoff, and all five model fingerprints matched the approved saved bundle. Validation passed for the unlabeled batch; precision, recall and pattern recovery were unavailable without reference data.

Publication automatically advanced the BQ2 pointer. After reloading the existing public TRACE URL, Evaluation & coverage showed the new batch and alert count, and Connected cases opened the matching ranked case and source payments. A conditional pointer update then restored the full-volume presentation release, confirmed in S3 and on public TRACE. Immutable test results remain available.

Both executions and their Glue jobs finished. No workflow, dashboard, IAM or schedule change. Exact run locators, measurements, costs and screenshots stay in the private operator record. Use the test as proof of on-demand publication; use the restored full-volume release for the performance results.
