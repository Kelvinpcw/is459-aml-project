> **Current status — 2026-10-27T15:47:03.623179+08:00: PAUSED at user request. Exact evaluator grant approved/applied; role and input files deployed. Glue job remains unsaved; no paid evaluator run started. Resume from PROJECT_CHECKPOINT.md and finish job configuration. The single bounded-run approval is unconsumed. Earlier pending-approval statements below are historical.

# Full architecture and current implementation

Updated 27 October 2026, Singapore. **Resumed. Separate evaluator passed local tests/replay; new evaluator grant and one bounded cloud test await concrete confirmation.** The full architecture remains the proposed design. **Shared preparation and Q1 aggregation have succeeded in AWS on the 1 September 2022 development slice. Q1 summaries are registered and independently validated through Athena. Q2 first-minute cloud run and all case/index checks passed. All known project compute/queries are terminal.**

| Component | Purpose | Current state |
| --- | --- | --- |
| S3 ingestion and shared Glue preparation | Clean transactions, enrich accounts, separate labels | Development slice validated: 4,465,985 transactions, 1,056 positive labels, no quarantine. Full source has 31,898,238 transactions and has not been processed/uploaded in full. |
| Q1 reporting | Counts, rates, lift and support by format/bank pair, with currency filters | Glue Q1 and Athena validation complete for one day; full/format/USD baseline counts, rates, lifts and precision independently verified. Bank-pair support limitation documented. No dashboard/holdout result yet. |
| Q2 detection | Label-free fan-in, fan-out and 2–4-account cycles with supporting cases | Cloud first-minute run PASSED: 15 fan-out cases / 840 evidence transactions. Every complete bundle/hash and all 15 Athena index rows match the frozen replay. Bounded prototype only; wider detection/evaluation remain. |
| Separate evaluator | Compare frozen detector outputs with labels and eligible annotations | Local development evaluator verified:19 evaluator tests, checksum-verified full-population replay. First-minute positives/eligible annotations both0, so recall/recovery not measurable. Cloud grant/run pending; calibrated holdout remains. |
| Release checks and published manifest | Publish only complete, validated outputs; retain previous successful release on failure | Per-stage preparation checks exist. Shared publication gate is not implemented. |
| Glue Data Catalog and Athena | Describe/query summaries and case index | Catalog DB/table/date partition registered; seven Athena executions finished, including three successful data validations. Private SSE-S3 results and 50 MB/query limit retained. |
| EC2 dashboard | Streamlit/Plotly Q1 charts and PyVis Q2 case inspection | Planned; not implemented or launched. |
| Step Functions | Preparation, parallel Q1/Q2, evaluator, checks, publication | Planned; not implemented or launched. |

The runtime flow is S3 → shared preparation → Q1 reporting and Q2 detection → separate Q2 evaluation → release checks → Athena summaries/case index and S3 case bundles → dashboard. Step Functions coordinates the sequence; the dashboard reads a single published dataset/run manifest.

This is on-demand batch analysis of synthetic data. The current one-day prototype is not the complete architecture or a validated holdout result. Development/calibration is 1–8 September, holdout is 9–16 September, and 17–28 September is a separate sparse tail.

See `../Proposal/Architecture/Pipeline_Explanation.md` for the design, `Q2_READINESS.md` for the next deployment review, and `../PROJECT_CHECKPOINT.md` for exact continuation instructions. Q1 execution ended successfully. All processing and queries have ended. The next step is the reviewed evaluator grant and one bounded cloud validation run. Wider Q2 detection and the remaining architecture are outstanding.
