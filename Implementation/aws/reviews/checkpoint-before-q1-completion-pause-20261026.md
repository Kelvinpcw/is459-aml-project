# IS459 AML project checkpoint

Updated 26 October 2026 (Singapore). **Q1 RUNNING: jr_8294653931045d22019ac21fc20f4d840159cba73f0600cc03aa25ee752a30c9, started 16:26:28 Singapore on 26 October 2026. User approved role and single bounded run. Policy and role created, code/job saved. Do not start another run. Preparation v2 remains complete.**

Current steering: user said all permission is allowed and to flag significant cost. Keep US$1 total prototype budget. Q1 role has only its approved custom policy, Glue trust only. Setting up Athena metadata/query workgroup using existing administrator console identity, without expanding the Q1 role. Latest sections below describe pre-launch status and are superseded by this running notice.

## Latest continuation — Q1 ready for approval

User asked to continue and whether preparation was the whole architecture. Clarified that only shared preparation on one day is validated; the full S3 → preparation → Q1/Q2 → separate evaluator → release gate → Catalog/Athena + S3 case bundles → dashboard flow remains planned. Step Functions coordinates it. Full deployment status: `Implementation/STATUS.md`. Proposal workflow status now points to that file.

- `Implementation/jobs/q1_risk.py` now exposes production `aggregate_daily` for local Spark regression checks. It validates unique/non-null fact and label keys, exact decimal(38,8) input schema, dataset/run identity, row joins and independent per-format N/L preparation references. The six Q1 tests cover precise Parquet output, legitimate duplicate-looking source records, date/currency filtering before counts/baseline, recomputed period rates (not averaged daily rates), missing/duplicate labels, altered labels, wrong decimal schema, leakage and null/foreign run keys. **18 total tests passed**, including the previous 12; this is local Spark, not a cloud Q1 execution.
- Fixed `Implementation/sql/q1_segment_ranking.sql` from the old v1 run to v2 and the intended Catalog table. Added `q1_catalog_draft.sql` with decimal(38,8) and explicit date partition. DDL is not executed; Q1 processing role has no Catalog grant, so automatic table registration is still unimplemented and will need its own reviewed setup.
- Added required `--analysis-id=q1-dev-20220901-v1` to Q1 job draft. It appends `analysis_id=...` below the preparation dataset/run for gold/quality output, allowing a separately approved future Q1 attempt without redoing preparation or overwriting partial output.
- Frozen source copy `Implementation/releases/q1-v1/q1_risk-v1.py`; intended S3 script `scripts/q1/q1_risk-v1.py`. No code uploaded or Q1 job saved yet.
- Role request: **AWSGlueServiceRole-is459-aml-q1**, policy **is459-aml-q1-data-access**, trust Glue only. Read v2 facts/labels/report and Q1 code, list only relevant prefixes (including folder metadata probes), manage only Q1 gold/quality/temp output, write only `/is459/aml/q1/*` logs. No IAM administration, input modification or unrelated data access.
- Policy JSON exactly matched local file in IAM editor; AWS showed zero errors/warnings/suggestions. Wizard is at **Review and create**, name/description populated. **Create policy has NOT been clicked. No Q1 policy or role exists from this task.** Screenshot `Implementation/evidence/q1-policy-review-20261026.jpg`; review text `Implementation/aws/reviews/q1-policy-review-console.txt`. Browser tab IDs transient; reconstruct from local files if closed.
- Pending user question requests the above grant, Q1 job save, and **one** Q1 test within remaining US$1 total prototype budget: Glue 5.1, two G.1X workers, 15-minute timeout, zero retries, concurrency one. About US$0.22 compute if it runs 15 minutes at the checked $0.44/DPU-hour example; prior preparation compute estimate US$0.166345, storage/logs additional. This is not an account-wide hard cap. Athena queries, Catalog grants/registration, Q2/evaluator, EC2 and schedules are not part of this request.
- Exact pending scope/hashes: `Implementation/aws/reviews/q1-pending-authorization.json`. **Do not grant access or start Q1 until the user approves this concrete request.** If they approve, apply only this policy to the new Glue-trusted role, upload frozen code, save the bounded job, verify source/settings, inspect existing v2 Parquet schema/sample if feasible, then run once and record the AWS run ID. No automatic retries. Require 4,465,985 transactions and 1,056 positive labels, quality PASSED, immutable outputs and terminal compute. Review readiness steps in `Implementation/Q1_READINESS.md`.
- No additional cloud processing or service grant occurred this turn. Earlier two preparation approvals remain consumed. No Q2/evaluator/dashboard/release gate/orchestrator exists.

## Prior checkpoint and persistent boundaries

1. Use AWS project account **160885259244**, user **g2team7**, region **us-east-1**. Browser IDs are transient. **Local AWS CLI is authenticated to another account; never use it for project mutations.**
2. Preparation **v2 has already succeeded and its report was independently verified**. Do not rerun preparation. Both approved runs are consumed. No further paid executions/retries are authorized.
3. Current accepted population: **4,465,985 transactions, 1,056 positive labels, zero quarantine**, 2,087,786 valid account mappings, zero invalid mappings, zero unmatched sender/receiver rows. Exact payment-format N/L totals match the original manifest, including Bitcoin 92,751 / 16. Fact-column contract excludes labels and preserves raw amounts with decimal(38,8). The report checks and earlier local Spark regressions are verified; actual v2 cloud Parquet schemas/samples have not yet been independently downloaded/read. Inspect an existing sample without a new paid job if needed before downstream setup.
4. Existing v2 report: `s3://is459-aml-g2team7-160885259244-us-east-1/quality/preparation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/report.json`. Local copy and independent review: `Implementation/aws/reviews/preparation-report-dev-20220901-v2.json`, `preparation-review-dev-20220901-v2.json`.
5. Next milestone is **Q1 setup**, not another preparation run. Local drafts exist: `Implementation/aws/q1-trust-policy.json`, `q1-permissions-policy.json`, `q1-job-draft.json`. These scope the Q1 role to reading v2 transaction facts/separate labels/report and code, and managing only Q1 gold/quality/temp output plus Q1 logs. **No Q1 role/policy grant, job, code upload, catalog/table or execution has been deployed/approved.** Review these drafts before requesting any required action-time security grant. The approved preparation role remains unchanged; do not ask for that same grant again. Separate authorization is needed for Q1 paid execution. Do not reuse the preparation role for Q1/Q2.
6. No Q2 detector, evaluator, dashboard, release gate or orchestration exists yet. Business questions and architecture remain unchanged.
7. Keep S3 data/results as requested. Verify project compute is terminal after future authorized work. Scope cleanup to this project's resources; never touch unrelated shared-account resources.

## Latest completed run and cleanup

User approved one corrected run within the remaining **US$1 total prototype-test budget** and said “can delete the old output.” That approval is consumed. The old disposable synthetic test outputs were deleted only after v2 passed validation.

- Job `is459-aml-prepare-dev`; AWS run ID `jr_bede7c68199d9eeec1e051d1b1a69bf9d9842aad199e097915f604c8ad246f08`.
- **Succeeded**. Start **26 October 2026 10:15:05**, end **10:21:29**, Singapore time. Execution **350 seconds / 5m50s**, startup **33 seconds**, reported usage **0.194722 DPU-hours**.
- Runtime bounds verified: Glue 5.1, two G.1X workers, 15-minute timeout, zero automatic retries, concurrency one. Script `scripts/preparation/prepare-v2.py`; `--run-id=dev-20220901-v2`, `--max-quarantine-rows=0`.
- Approximate v2 compute **US$0.0857** at the checked $0.44/DPU-hour example rate. Both runs combined **US$0.166345 ≈ US$0.17 Glue compute**, plus S3/logging/other applicable charges. This is usage-based estimation, not a finalized invoice or an account-wide billing cap.
- **Both Glue runs are terminal. No project compute remains running.** No EC2/notebook/session/crawler/Athena query/Step Functions execution/schedule/NAT/database was started by this task.
- Deleted only v1 prefixes for dataset `ibm-hi-medium-b1b99c68b765580f`, run `dev-20220901-v1`: `curated/` (17 objects, 373.1 MB), `references/labels/` (16, 36.5 MB), `quarantine/preparation/` (1, 4.5 MB), `quality/preparation/` (1, 5.8 KB). **35 objects, roughly 414 MB; zero failures.** Detailed delete status and screenshots are saved.
- Retained raw inputs, v1/v2 code, v2 outputs, IAM/job definitions, local v1 report/audit/source and small static CloudWatch logs. Bucket versioning is disabled; the deleted test Parquet output can be regenerated from retained sources only through a separately approved new run.
- Browser download event handling stalled for the JSON report; **Open** rendered it inline successfully. The visible JSON body was read and saved via documented read-only DOM inspection. Prefer Open for JSON on resume; never extract credentials or reuse presigned URL tokens. No new compute was launched during this recovery.

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

Historical v1 report verified: embedded source manifest exactly matches local manifest, input/accepted/quarantine totals reconcile, valid account mappings 2,087,786, invalid mappings 0, unmatched sender/receiver rows 0, fact column list excludes labels. Actual cloud Parquet objects have not all been independently inspected.

## Correction and verification

- `Implementation/jobs/prepare.py`: decimal(38,8), reject excess precision instead of silently rounding, preserve original raw amount strings in facts, report schema 2 and explicit amount policy, zero-quarantine default gate, per-reason quarantine counts, exact accepted+quarantine per-format N/L reconciliation against ingestion reference.
- `Implementation/jobs/q1_risk.py`: rejects legacy preparation schema/amount contract and requires source-reference reconciliation, so v1 cannot feed Q1.
- Saved complete source in Glue editor compared exactly with local source (16,265 characters) before Save; console showed successful update, saved filename and both new parameters verified. Original executed v1 source archived locally. The v1 source was retained; its superseded S3 output was subsequently deleted as authorized, after v2 verification.
- **Earlier 12 tests passed**: eight ingestion tests, two real Spark decimal/Parquet/aggregation regressions and two Q1 contract tests. Six further Q1 tests now bring the suite to 18. Spark regression covers six/eight decimal exactness, mixed currency totals, excess-scale rounding trap, malformed/null amounts and overflow. Local environment: temporary PySpark 3.5.6, Python 3.11, installed Java 21; not a complete Glue environment.
- Full input amount audit: `Implementation/scripts/audit_preparation_amounts.py`, saved output `Implementation/aws/reviews/preparation-review-dev-20220901-v1.json`.
- `Implementation/aws/preparation-job-v2.json`: reproducible intended current config. Console may serialize additional/default arguments differently.
- `Implementation/releases/preparation-v2/prepare-v2.py`: exact local deployed-source copy.

## Cloud resources and completed spending

- Private S3 bucket `is459-aml-g2team7-160885259244-us-east-1`: block all public access, ACLs disabled, SSE-S3, versioning disabled. Retain.
- Development input prefix `raw/development/20220901/`: transactions/accounts gzip, manifest and empty ingestion quarantine. Full originals were not uploaded.
- Scripts `scripts/preparation/prepare.py` (v1) and `scripts/preparation/prepare-v2.py` (current saved job).
- IAM role `AWSGlueServiceRole-is459-aml-prepare`, trust Glue only, exactly one approved custom policy `is459-aml-prepare-data-access`. Same approved permissions, unchanged. Do not ask for this unchanged grant again. Other roles are not approved.
- Saved Glue job `is459-aml-prepare-dev`: Glue 5.1, 2 G.1X workers, 15 minutes, retries 0, concurrency 1, queueing/auto scaling/optional metrics/Spark UI/Catalog metastore/lineage off, no VPC connections. Project temp and log paths unchanged. Saving a definition starts no compute.
- Historical v1 AWS run is terminal Succeeded (two total runs now exist): `jr_ab63943d9cb2bfe3f8e7b96be19b04f1542190619123946ae313ef7d1a2f872d`.
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

Latest evidence: `Implementation/evidence/preparation-v2-succeeded-20261026.jpg`, `v1-curated-deleted-20261026.jpg`, `v1-labels-deleted-20261026.jpg`, `v1-quarantine-deleted-20261026.jpg`, `v1-quality-deleted-20261026.jpg`. Cleanup records: `Implementation/aws/reviews/v1-output-cleanup-plan.json` and `v1-output-cleanup-results.json`. Source-report checks: `Implementation/scripts/verify_preparation_report.py`.
