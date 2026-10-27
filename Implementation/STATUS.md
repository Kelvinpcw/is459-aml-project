# Full architecture and current implementation

**Active completion work, 28 October:** user requested the whole project, then revised the final total ceiling to **US$30**. A new publication layer, live pilot dashboard, distributed detector/evaluator and on-demand deployment/cleanup tools are implemented on `codex/project-completion`. The 67-test suite passed; final packaging checks are underway. A complete local input copy accounts for all31,898,238records/35,230labels. The pilot release is published. **The final full-data cloud run has not started**; v2 scale/holdout and EC2/workflow operation are not yet cloud-validated. See [completion plan](COMPLETION_PLAN.md) and [runbook](RUNBOOK.md).


Updated 28 October 2026, Singapore. **The scoped evaluator continuation is complete.** Its single approved run succeeded and all four raw output files match frozen local predictions. All five known project Glue runs and ten recorded Athena statements are terminal; S3 is retained. No further processing or deployment is in progress. See [cloud evaluator validation](results/EVALUATION_CLOUD_VALIDATION.md).

## GitHub connection — 27 October 2026

Q1 now has a verified manual GitHub push/pull connection on `codex/glue-github-connection`; its script is unchanged. Main has not been merged, other jobs are not connected, and no processing run or automatic deployment was started. Work is paused at the user's request. See [team instructions](glue/README.md) and [verification](aws/reviews/github-glue-q1-connection-20261027.json).

The table below summarises retained evidence, not a new live AWS inventory. The proposal/diagrams describe the target design, not implemented features.

| Component | Purpose | Current state |
| --- | --- | --- |
| S3 ingestion and shared Glue preparation | Clean transactions, enrich accounts, separate labels | Development slice validated: 4,465,985 transactions, 1,056 positive labels, no quarantine. Full source has 31,898,238 transactions and has not been processed/uploaded in full. |
| Q1 reporting | Counts, rates, lift and support by format/bank pair, with currency filters | Glue Q1 and Athena validation complete for one day; full/format/USD baseline counts, rates, lifts and precision independently verified. Bank-pair support limitation documented. No dashboard/holdout result yet. |
| Q2 detection | Label-free fan-in, fan-out and 2–4-account cycles with supporting cases | Cloud first-minute run PASSED: 15 fan-out cases / 840 evidence transactions. Every complete bundle/hash and all 15 Athena index rows match the frozen replay. Bounded prototype only; wider detection/evaluation remain. |
| Separate evaluator | Compare frozen detector outputs with labels and eligible annotations | Local evaluator tests/replay verified. First-minute positives and eligible annotations are both zero, so recall/recovery are not measurable. Glue run succeeded; all four raw artifact hashes/bytes match the frozen local reference. This completes pilot evaluation mechanics; calibrated holdout remains. |
| Release checks and published manifest | Publish only complete, validated outputs; retain previous successful release on failure | New gate tested; pilot publication observed after physical Parquet/count checks. Immutable release + conditional current pointer; full-data publication still pending. |
| Glue Data Catalog and Athena | Describe/query summaries and case index | Q1 summary and Q2 case-index tables/partitions registered and read-validated. Ten saved Athena statements are terminal (seven Q1, three Q2). Private SSE-S3 results and 50 MB/query limit retained. |
| EC2 dashboard | Streamlit/Plotly Q1 charts and PyVis Q2 case inspection | App implemented and locally tested against published pilot; private on-demand EC2 template validated locally, not yet launched. |
| Step Functions | Preparation, parallel Q1/Q2, evaluator, checks, publication | On-demand workflow and isolated roles/jobs implemented; template validated locally and by AWS. No execution yet. |

The runtime flow is S3 → shared preparation → Q1 reporting and Q2 detection → separate Q2 evaluation → release checks → Athena summaries/case index and S3 case bundles → dashboard. Step Functions coordinates the sequence; the dashboard reads a single published dataset/run manifest.

This is on-demand batch analysis of synthetic data. The current one-day prototype is not the complete architecture or a validated holdout result. Development/calibration is 1–8 September, holdout is 9–16 September, and 17–28 September is a separate sparse tail.

## Important implementation limits

- Q1's one-day scope comes from its prepared inputs; its aggregation already groups by date. Wider inputs/configuration, permissions and benchmarks still need review/validation.
- Q2's scope is **one minute**, not one second. Spark filters/validates before collecting the bounded graph to the driver; the default guard is 50,000 transactions. Do not merely widen the dates or remove limits to claim full-day processing. Separate non-overlapping minute runs would miss cross-boundary patterns.
- The pilot minute has zero positive labels and eligible annotations. Local evaluation is a mechanics diagnostic, not useful recall/recovery or a holdout benchmark.
- Under Q1's current one-day bank-pair/format support threshold, qualifying segments have zero positive labels; do not present their zero-lift ranking as meaningful positive-exposure priorities.

## Work remaining

1. Scalable Q2 fan patterns and bounded cycles over agreed lookbacks, with complete source evidence.
2. Wider preparation/Q1 runs and eventual full-source accounting, after local validation and scoped authorisation.
3. Integrate the completed pilot evaluator into a shared release gate; preserve frozen attempts and consumed approvals.
4. Development calibration and frozen holdout evaluation on the declared eligible population.
5. Shared release gate, one published-run manifest, dashboard and Step Functions integration.
6. Full-run benchmarks, recovery tests, setup/run videos and final resource cleanup.

See [pipeline design](../Proposal/Architecture/Pipeline_Explanation.md), [Q1 validation](results/Q1_VALIDATION.md), [Q2 validation](results/Q2_VALIDATION.md), [cloud evaluation](results/EVALUATION_CLOUD_VALIDATION.md), [local evaluation](results/EVALUATION_LOCAL_VALIDATION.md) and [deployment checkpoint](../PROJECT_CHECKPOINT.md). AWS profile names are machine-local; each member must verify their own project login. See [SETUP.md](SETUP.md).
