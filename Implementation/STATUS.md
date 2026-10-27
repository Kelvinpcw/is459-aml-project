# Full architecture and current implementation

Updated 27 October 2026, Singapore. **Deployment remains paused.** The last cloud handoff is **2026-10-27T15:47:03.623179+08:00**: evaluator role/policy and input files deployed, Glue evaluator job unsaved, no cloud evaluator run started. Repository/documentation work does not resume that deployment.

## GitHub connection — 27 October 2026

Q1 now has a verified manual GitHub push/pull connection on `codex/glue-github-connection`; its script is unchanged. Main has not been merged, other jobs are not connected, and no processing run or automatic deployment was started. Work is paused at the user's request. See [team instructions](glue/README.md) and [verification](aws/reviews/github-glue-q1-connection-20261027.json).

The table below summarises retained evidence, not a new live AWS inventory. The proposal/diagrams describe the target design, not implemented features.

| Component | Purpose | Current state |
| --- | --- | --- |
| S3 ingestion and shared Glue preparation | Clean transactions, enrich accounts, separate labels | Development slice validated: 4,465,985 transactions, 1,056 positive labels, no quarantine. Full source has 31,898,238 transactions and has not been processed/uploaded in full. |
| Q1 reporting | Counts, rates, lift and support by format/bank pair, with currency filters | Glue Q1 and Athena validation complete for one day; full/format/USD baseline counts, rates, lifts and precision independently verified. Bank-pair support limitation documented. No dashboard/holdout result yet. |
| Q2 detection | Label-free fan-in, fan-out and 2–4-account cycles with supporting cases | Cloud first-minute run PASSED: 15 fan-out cases / 840 evidence transactions. Every complete bundle/hash and all 15 Athena index rows match the frozen replay. Bounded prototype only; wider detection/evaluation remain. |
| Separate evaluator | Compare frozen detector outputs with labels and eligible annotations | Local evaluator tests/replay verified. First-minute positives and eligible annotations are both zero, so recall/recovery are not measurable. Exact evaluator role/policy and manifest/annotations deployed; job unsaved and no cloud evaluator run. Calibrated holdout remains. |
| Release checks and published manifest | Publish only complete, validated outputs; retain previous successful release on failure | Preparation/Q1/Q2 per-stage checks exist. Shared publication gate is not implemented. |
| Glue Data Catalog and Athena | Describe/query summaries and case index | Q1 summary and Q2 case-index tables/partitions registered and read-validated. Ten saved Athena statements are terminal (seven Q1, three Q2). Private SSE-S3 results and 50 MB/query limit retained. |
| EC2 dashboard | Streamlit/Plotly Q1 charts and PyVis Q2 case inspection | Planned; not implemented or launched. |
| Step Functions | Preparation, parallel Q1/Q2, evaluator, checks, publication | Planned; not implemented or launched. |

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
3. Evaluator cloud completion only when explicitly resumed; preserve existing exact grant/attempt boundaries rather than recreating resources.
4. Development calibration and frozen holdout evaluation on the declared eligible population.
5. Shared release gate, one published-run manifest, dashboard and Step Functions integration.
6. Full-run benchmarks, recovery tests, setup/run videos and final resource cleanup.

See [pipeline design](../Proposal/Architecture/Pipeline_Explanation.md), [Q1 validation](results/Q1_VALIDATION.md), [Q2 validation](results/Q2_VALIDATION.md), [local evaluation](results/EVALUATION_LOCAL_VALIDATION.md) and [deployment checkpoint](../PROJECT_CHECKPOINT.md). AWS profile names are machine-local; each member must verify their own project login. See [SETUP.md](SETUP.md).
