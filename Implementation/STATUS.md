# Current implementation and validation

Updated 28 October 2026. The user authorised whole-project completion, an exact set of isolated roles/deployments, and a **US$30 total ceiling**. The first full execution failed at the detector export join; all of its compute is terminal. A targeted recovery is prepared and locally tested; do not restart the original execution. The previous pilot remains published until all full gates pass.

| Component | Current evidence |
| --- | --- |
| Shared preparation | Full Glue run SUCCEEDED: 31,898,238 accepted transactions, 35,230 positive labels, zero quarantine, zero unmatched endpoint joins. [Report](aws/reviews/full-preparation-report.json) |
| Q1 | One-day pilot validated. The original full Q1 was cancelled by the parallel-branch failure; recovery uses a fresh output prefix. |
| Distributed Q2 | New Spark fan and balanced 2-hop cycle implementation locally tested and frozen in `releases/full-v1`; the first full attempt failed during export. Frozen full-v2 fixes that join and packs complete evidence into schema3 shards; detection logic is unchanged. Degree/expansion/output guards remain enforced. |
| Separate evaluator | Pilot cloud validation completed. Full development, frozen holdout and sparse-tail metrics await completed detection. No effectiveness claim yet. |
| Shared publication | Pilot is published. Gate checks identities, reports, physical Parquet populations and artifact hashes; immutable manifests and conditional current pointer retain the prior release on failure. Full publication pending. |
| Dashboard | Streamlit/Plotly/PyVis implementation passed local application tests and read the live pilot. Temporary EC2/SSM full-data demonstration pending. |
| Orchestration | `is459-aml-full-v1` stack CREATE_COMPLETE; exact six role policies, five job definitions, frozen code and inputs verified. Named execution `full-20261028-v1` FAILED. A recovery workflow reuses successful preparation and unchanged IAM grants. No recurring schedules. |
| Local verification | Recovery 68-test suite PASSED; additional balanced-cycle, complete-export, temporal-evaluation and application checks passed. Both templates pass cfn-lint. [Record](aws/reviews/completion-local-validation-20261028.json) |

The complete input selection spans 1 September inclusive to 29 September exclusive. Full Q2 reports early unavailable history and cycles excluded by the declared degree-eligible induced graph. It retains all fan evidence and exact source records, including parallel transactions. Development/calibration is 1–8 September, holdout 9–16 and sparse tail 17–28; future snapshots cannot create earlier alerts. A five-percentage-point typed recovery margin against the matched-volume amount diagnostic was frozen before holdout; report its actual result honestly.

## Remaining completion work

Observe full detection/evaluation/publication and independently check the outputs. Diagnose any failure without overwriting a frozen release or blindly rerunning completed stages. Validate the private EC2 dashboard, measure response times and demonstrate the two user scenarios. Remove its compute/disk/IP, verify all project jobs/queries are terminal, and record actual runtime, estimated costs and limitations. Human team ownership, contributions and narrated presentation recordings require real team input; do not fabricate them.

Current operational identities and approval: [checkpoint](../PROJECT_CHECKPOINT.md), [ledger](aws/resource-ledger.json), [exact access review](aws/reviews/full-access-grant-review-20261028.md), [deployment verification](aws/reviews/full-deployment-verification.json), [latest monitor](aws/reviews/full-monitor-latest.json). [Runbook](RUNBOOK.md) explains setup, operation, contracts and cleanup. Latest dated observations supersede earlier planning statements.

## Preserved pilot evidence

Preparation/Q1 were validated for 1 September: 4,465,985 facts and 1,056 positive labels. Frozen Q2/evaluation used the first minute only: 43,681 eligible transactions, 15 fan-out cases and 840 evidence transactions; no positive labels or eligible annotations, so recall/recovery were unmeasurable. The bounded driver detector's 50,000-row guard remains unchanged. These mechanics tests are separate from the new distributed full attempt.

See [Q1 validation](results/Q1_VALIDATION.md), [Q2 validation](results/Q2_VALIDATION.md), [cloud evaluation](results/EVALUATION_CLOUD_VALIDATION.md) and [local evaluation](results/EVALUATION_LOCAL_VALIDATION.md). The older Q1 GitHub connection on `codex/glue-github-connection` remains unchanged; a branch does not isolate shared cloud jobs.
