# IS459 AML project checkpoint

Updated 26 October 2026 (Singapore). **Preparation v2 RUNNING, approved by user; AWS run jr_bede7c68199d9eeec1e051d1b1a69bf9d9842aad199e097915f604c8ad246f08. Started 10:15:05 Singapore. Do not start another run.**

Latest steering: user approved the corrected run within the remaining US$1 test budget and authorized deleting old output. Delete only v1 synthetic development outputs after v2 passes validation; plan `Implementation/aws/reviews/v1-output-cleanup-plan.json`. Sections below describe the pre-launch checkpoint and are superseded by this running status.

## Resume here

1. Read this checkpoint. Use project AWS account **160885259244**, user **g2team7**, region **us-east-1**. Browser tab IDs are transient. **Local AWS CLI belongs to another account; never use it for project mutations.**
2. The existing v1 Glue run succeeded technically, but independent review found its accepted population incomplete. Do not use it for Q1/Q2. No need to download the report again: copies and audit are under `Implementation/aws/reviews/`.
3. The correction is already saved in existing job `is459-aml-prepare-dev`, with script `scripts/preparation/prepare-v2.py`, new parameter `--run-id=dev-20220901-v2` and `--max-quarantine-rows=0`. Do not recreate the job or change the approved service role.
4. **Do not click Run until the user approves the replacement run.** The earlier approval was for exactly one run and is consumed. The intended request is one corrected preparation run within the remaining US$1 prototype-test budget, 2 G.1X workers, 15-minute timeout, zero automatic retries, concurrency 1. Estimated additional compute at $0.44/DPU-hour is about $0.08 if runtime repeats, or $0.22 for 15 minutes, plus storage/logs/other charges. This is not an account-wide billing cap.
5. If approved, recheck account, script, parameters and bounds, click Run once, record the new AWS run ID, and watch to terminal status. Do not automatically retry or reuse output namespaces.
6. Review v2 report at `s3://is459-aml-g2team7-160885259244-us-east-1/quality/preparation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/report.json`. Require schema 2, PASSED, decimal(38,8), zero quarantine, 4,465,985 accepted, 1,056 positive labels, exact per-format N/L reconciliation, 2,087,786 valid account mappings, no multiplying joins, unknown endpoint counts reported and no labels in facts. Check actual output schema/sample as appropriate; local tests are not a full AWS v2 execution.
7. Then continue Q1. Q1 role, permissions, job, catalog/table and execution still need preparation/review and relevant approvals. No Q2 detector, evaluator, dashboard or orchestration exists yet.
8. Before ending processing/demo, verify project compute is terminal and update ledger. Retain S3 data/results. Do not change unrelated shared-account resources.

## Why v1 is blocked

The run succeeded in AWS and its report says PASSED, but that only covered the old script's checks. The two-decimal amount rule rejected valid six-decimal values.

| Item | Count |
| --- | ---: |
| Input transactions | 4,465,985 |
| Accepted by v1 | 4,372,431 |
| Quarantined by v1 | 93,554 |
| Rejected Bitcoin transactions | 92,721 of 92,751 |
| Rejected ACH transactions | 625 |
| Rejected Wire transactions | 208 |
| Positive labels incorrectly quarantined | 16 |

A full independent local scan reproduced every quarantined row through the old amount rule, and accepted + rejected payment-format and label totals exactly reconcile with the original ingestion manifest. All selected input amounts fit decimal(38,8): observed maximum scale 6, maximum significant integer digits 13, zero representation rejects. The architecture/business questions remain unchanged; this is an implementation bug.

Existing report verified: embedded source manifest exactly matches local manifest, input/accepted/quarantine totals reconcile, valid account mappings 2,087,786, invalid mappings 0, unmatched sender/receiver rows 0, fact column list excludes labels. Actual cloud Parquet objects have not all been independently inspected.

## Correction and verification

- `Implementation/jobs/prepare.py`: decimal(38,8), reject excess precision instead of silently rounding, preserve original raw amount strings in facts, report schema 2 and explicit amount policy, zero-quarantine default gate, per-reason quarantine counts, exact accepted+quarantine per-format N/L reconciliation against ingestion reference.
- `Implementation/jobs/q1_risk.py`: rejects legacy preparation schema/amount contract and requires source-reference reconciliation, so v1 cannot feed Q1.
- Saved complete source in Glue editor compared exactly with local source (16,265 characters) before Save; console showed successful update, saved filename and both new parameters verified. Original executed v1 source archived locally. The v1 S3 source/results were retained.
- **12 tests passed**: eight ingestion tests, two real Spark decimal/Parquet/aggregation regressions and two Q1 contract tests. Spark regression covers six/eight decimal exactness, mixed currency totals, excess-scale rounding trap, malformed/null amounts and overflow. Local environment: temporary PySpark 3.5.6, Python 3.11, installed Java 21; not a complete Glue environment.
- Full input amount audit: `Implementation/scripts/audit_preparation_amounts.py`, saved output `Implementation/aws/reviews/preparation-review-dev-20220901-v1.json`.
- `Implementation/aws/preparation-job-v2.json`: reproducible intended current config. Console may serialize additional/default arguments differently.
- `Implementation/releases/preparation-v2/prepare-v2.py`: exact local deployed-source copy.

## Cloud resources and completed spending

- Private S3 bucket `is459-aml-g2team7-160885259244-us-east-1`: block all public access, ACLs disabled, SSE-S3, versioning disabled. Retain.
- Development input prefix `raw/development/20220901/`: transactions/accounts gzip, manifest and empty ingestion quarantine. Full originals were not uploaded.
- Scripts `scripts/preparation/prepare.py` (v1) and `scripts/preparation/prepare-v2.py` (current saved job).
- IAM role `AWSGlueServiceRole-is459-aml-prepare`, trust Glue only, exactly one approved custom policy `is459-aml-prepare-data-access`. Same approved permissions, unchanged. Do not ask for this unchanged grant again. Other roles are not approved.
- Saved Glue job `is459-aml-prepare-dev`: Glue 5.1, 2 G.1X workers, 15 minutes, retries 0, concurrency 1, queueing/auto scaling/optional metrics/Spark UI/Catalog metastore/lineage off, no VPC connections. Project temp and log paths unchanged. Saving a definition starts no compute.
- **Only one AWS run exists**, verified again after v2 save. It is terminal Succeeded: `jr_ab63943d9cb2bfe3f8e7b96be19b04f1542190619123946ae313ef7d1a2f872d`.
- v1 start 26 October 03:03:35, end 03:09:14 Singapore, execution 330 seconds, 0.183333 DPU-hours, approximate compute US$0.0807 at checked $0.44/DPU-hour. Not a finalized invoice.
- Small CloudWatch logs retained under `/is459/aml/preparation/error` and `/output`; log retention was not changed. No ongoing project compute.
- No EC2, notebook/session, crawler, Athena query, Step Functions execution, schedule, NAT gateway, database or other continuously running project service was launched. This does not describe unrelated account services or account-wide charges.

## Persistent project decisions

IBM HI-Medium synthetic AML dataset. Q1: historical exposure/priorities by format/bank pair with counts, support, rates/lift and currency-aware filters. Q2: label-free fan-in/out and bounded 2–4-account cycles as investigation leads; labels/pattern references for isolated evaluation only. No ML or graph database required.

Shared S3 → Glue preparation → independent Q1/Q2 → isolated evaluator → quality gate/published manifest → Athena summaries/index + S3 case bundles → on-demand dashboard. See `Proposal/Project_Proposal.md` and `Proposal/Architecture/Pipeline_Explanation.md`. Development/calibration 1–8 September 2022; holdout 9–16; sparse tail 17–28 separate. Current prototype is 1 September only.

Dataset version `ibm-hi-medium-b1b99c68b765580f`. Full transaction source 31,898,238 records; selected 4,465,985; source labels 1,056 positive and 4,464,929 negative; original ingestion rejects 0. IDs use original CSV SHA256 + colon + original 1-based data-record ordinal. Preserve legitimate duplicate-looking records. Source timestamps are dataset-local, timezone unspecified; UTC is only fixed internal parsing convention. Consider chunked inputs before full-scale work because one gzip serializes parsing.

Keep Glue 5.1: bundled SDK supports conditional S3 PutObject IfNoneMatch. Glue 5.0's bundled SDK did not. Both job scripts fail early if capability is absent.

## Evidence and records

- `Implementation/aws/resource-ledger.json`
- `Implementation/aws/last-console-verification.json`
- `Implementation/aws/reviews/preparation-report-dev-20220901-v1.json`
- `Implementation/aws/reviews/preparation-review-dev-20220901-v1.json`
- `Implementation/aws/reviews/prepare-v1-executed.py`
- `Implementation/aws/reviews/saved-preparation-v2-console.txt`
- `Implementation/aws/reviews/preparation-run-history-after-v2-save.txt`
- `Implementation/evidence/preparation-v2-saved-20261026.jpg`
- `Implementation/evidence/preparation-v2-no-new-run-20261026.jpg`
- `Implementation/TEARDOWN.md`

Earlier checkpoint archived as `Implementation/aws/reviews/checkpoint-before-amount-review-20261026.md`; its earlier zero-run and unreviewed-report statements are historical.
