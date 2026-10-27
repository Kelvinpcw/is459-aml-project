# IS459 AML project — paused checkpoint

Updated 26 October 2026 (Singapore). **PAUSED at the user's request. Preparation v2 and Q1 both SUCCEEDED; their reports are verified. No project compute remains running.**

## Resume exactly here

1. Wait for the user to resume. Read this checkpoint first. Use AWS account **160885259244**, IAM user **g2team7**, region **us-east-1**. The local AWS CLI is authenticated to a DIFFERENT account; never mutate project resources with it. Use the signed-in project console or a separately verified matching session. Browser tab IDs are transient; tabs can be closed safely.
2. **Do not rerun preparation or Q1.** Existing outputs are saved in S3. The single approved Q1 run has completed and its approval is consumed. First inspect the existing Q1 Parquet schema/sample if useful; then register its explicit Catalog database/table/date partition and run bounded summary validation queries in the prepared Athena workgroup.
3. Athena workgroup **is459-aml-dev** is already created and verified: Athena SQL engine version 3, IAM auth, customer-managed results `s3://is459-aml-g2team7-160885259244-us-east-1/query-results/q1/`, expected owner `160885259244`, SSE-S3, override client settings ON, **50 MB per-query scan limit**, CloudWatch performance metrics OFF, requester-pays OFF, no provisioned capacity. **No Athena SQL statement has run. No project Catalog database/table/partition has been created.** Do not create a duplicate workgroup or use the unrestricted primary workgroup.
4. Planned metadata is `is459_aml_dev.q1_daily_counts_dev20220901_v2`; table/partition DDL is `Implementation/sql/q1_catalog_draft.sql`. It points at the successful Q1 analysis output below and uses decimal(38,8), event_date DATE partition. Run one statement at a time after verifying paths/schema; use the existing administrator console identity. The Q1 role has no Catalog/Athena grants and need not be expanded for this manual prototype setup. No crawler is required.
5. Then use `Implementation/sql/q1_segment_ranking.sql` and a small reconciliation query to verify all-format totals 4,465,985 / 1,056 and selected-currency baselines. Log query IDs, scanned bytes and results. These queries should cost far below a cent; keep the total prototype budget at US$1. The user broadly authorized continuing and requested notification only for significant cost, then explicitly paused. Routine authorized setup does not need repeated permission questions. Any new security-sensitive grant must follow applicable action-time confirmation rules; the unchanged Q1/preparation grants are already approved.
6. Afterwards continue Q2/evaluation, release gate/published manifest, dashboard, and Step Functions. These are still unimplemented. The full architecture has NOT been deployed. Current validated population is one day (1 September 2022), not the full dataset or holdout.
7. Update this checkpoint and ledger after resuming. Stop project-created costly compute when finished, retain S3 data/results, and never alter unrelated shared-account resources.

## Latest Q1 completion

- Job **is459-aml-q1-dev**, AWS run ID **jr_8294653931045d22019ac21fc20f4d840159cba73f0600cc03aa25ee752a30c9**.
- Status **Succeeded**. Start **26 October 2026 16:26:28**, end **16:29:25** Singapore. Execution **169 seconds / 2m49s**, startup **8 seconds**, usage **0.094167 DPU-hours**.
- Glue 5.1, two G.1X workers, timeout 15 minutes, retries 0, concurrency 1. No auto scaling, queueing, VPC connections, Catalog metastore integration, optional metrics, Spark UI or lineage.
- Script `s3://is459-aml-g2team7-160885259244-us-east-1/scripts/q1/q1_risk-v1.py`; exact complete editor source compared with the frozen local copy before save. Local source: `Implementation/jobs/q1_risk.py`; frozen deployed copy: `Implementation/releases/q1-v1/q1_risk-v1.py`. The docstring's old prepared/not-deployed wording is historical; preserve the executed source.
- Parameters: `--preparation-report=s3://is459-aml-g2team7-160885259244-us-east-1/quality/preparation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/report.json`; `--output-root=s3://is459-aml-g2team7-160885259244-us-east-1`; `--analysis-id=q1-dev-20220901-v1`; custom logs `/is459/aml/q1`; temp `temporary/q1/`.
- Q1 quality **PASSED**, independently compared to the preparation report: **4,465,985 transactions and 1,056 labelled laundering**; dataset/run/analysis identity matches. Daily grain retains both currency dimensions, bank pair, format, date and dataset/run. Amount sums remain exact decimal(38,8).
- Report: `s3://is459-aml-g2team7-160885259244-us-east-1/quality/q1/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q1-dev-20220901-v1/report.json`.
- Daily counts: `s3://is459-aml-g2team7-160885259244-us-east-1/gold/risk/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q1-dev-20220901-v1/daily_counts/`.
- Local report: `Implementation/aws/reviews/q1-report-q1-dev-20220901-v1.json`; terminal evidence `q1-terminal-console.txt`. Actual Q1 cloud Parquet schemas/samples have not yet been independently read through Athena/local download; do not claim that check is complete.
- Q1 role **AWSGlueServiceRole-is459-aml-q1** exists, trusts only Glue, and has exactly one policy **is459-aml-q1-data-access**. Reads v2 facts/labels/report and Q1 code; lists needed prefixes; manages only Q1 gold/quality/temp; writes project Q1 logs. No administrator or Catalog permissions. Verified after creation. Both policy/trust sources and approval hashes are in `Implementation/aws/` and `reviews/q1-pending-authorization.json` (historical filename; status now consumed/completed).
- User approval: “yeah go ahead. All permission is allowed only let me know if the cost might be significant.” This approved the concrete Q1 role and single bounded test. Keep the earlier US$1 prototype budget as the ceiling unless the user changes it; flag significant/exceeding costs before proceeding. Their latest request explicitly pauses work.

## Costs and cleanup

- Preparation v1: 0.183333 DPU-hours, approximately US$0.080667 compute.
- Preparation v2: 0.194722 DPU-hours, approximately US$0.085678 compute.
- Q1: 0.094167 DPU-hours, approximately US$0.041433 compute.
- **Combined Glue compute approximately US$0.207778 ≈ US$0.21**, using checked $0.44/DPU-hour example pricing, plus S3/logging/other applicable charges. This is a usage estimate, not a finalized invoice or an account-wide hard cap.
- All three processing runs are terminal. **No project compute running.** No EC2, notebook, Glue interactive session, crawler, Athena query, Step Functions execution, schedule, NAT gateway or database compute was launched by this task.
- The idle Athena workgroup and saved Glue definitions are configuration, not running compute. Keep S3 outputs/code/raw inputs and small static CloudWatch logs. Log retention has not been changed.
- Old v1 disposable test output was deleted only after preparation v2 validation, as requested: 35 objects, roughly 414 MB, zero failures, across curated, references/labels, quarantine/preparation and quality/preparation v1 prefixes. Raw inputs, v1/v2 code, all v2/Q1 results and local review evidence remain. No further deletion was requested or performed this turn.

## Preparation and data context

Private bucket **is459-aml-g2team7-160885259244-us-east-1**: all public access blocked, ACLs disabled/bucket owner enforced, SSE-S3, versioning disabled. Input under `raw/development/20220901/`; full original files have not been uploaded.

Dataset version **ibm-hi-medium-b1b99c68b765580f**. Original transaction file: 31,898,238 records. Development slice: 4,465,985 records on 1 September 2022, 1,056 positive labels, ingestion quarantine 0. Source IDs are original transaction CSV SHA256 + colon + original 1-based data-record ordinal; preserve legitimate duplicate-looking records. Timestamps are dataset-local, timezone unspecified, UTC only a fixed internal parsing convention. Before scaling, consider chunked input because one gzip serializes parsing.

Preparation v2 run **jr_bede7c68199d9eeec1e051d1b1a69bf9d9842aad199e097915f604c8ad246f08** succeeded at 10:21:29 Singapore on 26 October. Report PASSED, all 4,465,985 accepted, zero quarantine, 2,087,786 valid account mappings, no invalid mappings or unmatched endpoints. Exact per-format N/L counts reconcile, including Bitcoin 92,751 / 16. Raw amounts are preserved and typed as decimal(38,8); excess precision cannot silently round. Facts exclude labels. The legacy v1 two-decimal rule incorrectly quarantined 93,554 valid rows and 16 positives; v1 output is deleted and must not be reused.

Preparation role **AWSGlueServiceRole-is459-aml-prepare**, approved policy **is459-aml-prepare-data-access**, Glue trust only, unchanged. Job **is459-aml-prepare-dev**, source `scripts/preparation/prepare-v2.py`, parameter run ID `dev-20220901-v2`, zero-quarantine gate. Keep Glue 5.1: its SDK supports required conditional S3 PutObject IfNoneMatch; Glue 5.0's bundled SDK did not.

## Full design and local tests

Q1 measures supported historical exposure by format/bank pair, with additive counts, rates/lift and currency-aware baselines. Q2 finds label-free fan-in/out and bounded 2–4-account cycles as leads, followed by isolated evaluation using labels/annotations. No ML or graph database is required.

Full flow: S3 → shared preparation → independent Q1/Q2 → isolated evaluator → shared release gate/published manifest → Athena summaries/case index + S3 case bundles → on-demand EC2 Streamlit/Plotly/PyVis dashboard. Step Functions coordinates batch processing. Development/calibration 1–8 September 2022; holdout 9–16; sparse tail 17–28 separate. Only 1 September has been processed so far.

18 local tests passed (8 ingestion, 4 amount/preparation contract, 6 Q1). Q1 tests exercise production aggregation and query template in local Spark, including precision through Parquet, date/currency denominators, legitimate duplicate preservation, missing/duplicate labels, reference count changes, null/foreign keys and label leakage. Local runtime PySpark 3.5.6/Python 3.11/Java 21. Q1 now also ran successfully in Glue. Query template points to v2 and supports summing counts before rates. Separate analysis IDs allow a later approved Q1 attempt without rerunning preparation or overwriting partial output.

## Key files and evidence

- `Implementation/aws/resource-ledger.json`, `environment.json`, `last-console-verification.json`
- `Implementation/aws/q1-job-draft.json` (original intended config; description is historical), Q1 role policy/trust JSON, `reviews/q1-saved-job-console.txt`
- `Implementation/sql/q1_catalog_draft.sql`, `q1_segment_ranking.sql`
- `Implementation/aws/reviews/q1-report-q1-dev-20220901-v1.json`, `q1-terminal-console.txt`, `athena-workgroup-console.txt`
- `Implementation/evidence/q1-role-created-20261026.jpg`, `q1-job-ready-20261026.jpg`, **q1-run-succeeded-20261026.jpg**, `athena-workgroup-limited-20261026.jpg`
- `Implementation/STATUS.md`, `Q1_READINESS.md`, `SETUP.md`, `TEARDOWN.md` (earlier readiness text is historical; this checkpoint is current)
- `Proposal/Project_Proposal.md`, `Proposal/Architecture/Pipeline_Explanation.md` and Detailed/Simplified architecture packs

Browser notes: use signed-in project Chrome. Prefer S3 **Open** to render JSON, then read the visible body and save it; download event handling stalled for minutes. Never extract credentials or reuse signed URL tokens. Explicitly focus and replace fields before typing; custom job parameter keys/values may need selecting their “Use …” option. Saving a clone can show stale/loading state briefly: verify success and persisted role/paths before Run, and click Run only once. No tabs are required to preserve the checkpoint.

Earlier checkpoint archived at `Implementation/aws/reviews/checkpoint-before-q1-completion-pause-20261026.md`.
