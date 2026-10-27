# IS459 AML project — checkpoint

Updated 26 October 2026 (Singapore). **Q1 development summaries are registered and independently validated through Athena. All runs/queries are terminal; no active project compute. Next: Q2 implementation.**

## Resume exactly here

1. Use project AWS account **160885259244**, IAM user **g2team7**, region **us-east-1**. Local AWS CLI uses a DIFFERENT account: never perform project mutations through it. Browser tab IDs are transient. Work was resumed by the user; no new pause was requested on this turn.
2. **Preparation v2 and Q1 are complete for the one-day development slice, including Athena validation. Do not rerun either job or repeat completed queries without a specific new reason.** The next implementation milestone is **Q2: label-free pattern detection and case generation**, then the separate evaluator, shared release gate/published manifest, dashboard and Step Functions. These remaining stages are not implemented. The full architecture is not complete.
3. Read `Implementation/results/Q1_VALIDATION.md` for results and limits. Existing registered table: **is459_aml_dev.q1_daily_counts_dev20220901_v2**, event_date **2022-09-01**, pointing at the successful immutable Q1 analysis output. Database/table/partition DDL is applied; its historical filename is `Implementation/sql/q1_catalog_draft.sql`. No crawler or new role grant was used.
4. Athena workgroup **is459-aml-dev** remains engine 3, IAM, private customer-managed S3 results `query-results/q1/`, SSE-S3, expected owner 160885259244, override client settings ON, 50 MB/query cutoff, performance metrics OFF, requester-pays OFF, no provisioned capacity. Use this workgroup rather than primary. All seven SQL executions are terminal (three metadata successes, one ordering validation rejection before scan, three successful read validations). No query is running.
5. For Q2, begin with local design/code/tests and reviewed output contracts. Detector inputs must be only label-free preparation facts and account/entity mappings; it must not read labels, Patterns.txt or Q1 labelled summaries. Labels/annotations enter only the separate evaluator after detection. Preserve source IDs and distinct legitimate transactions; use bank/account composite identity, explicit time windows/cutoffs and bounded 2–4-node cycles. Degree patterns are leads, not proof. Plan scalable joins/limits before authorizing any paid Q2 run on millions of rows.
6. User instruction persists: “All permission is allowed only let me know if the cost might be significant.” Keep the **US$1 total prototype budget** unless changed; flag significant/exceeding costs before proceeding. Do not re-request unchanged preparation/Q1 grants or routine already-authorized setup. For a materially new service-role grant, prepare exact scope and comply with applicable action-time confirmation requirements; do not apply unreviewed access based on this checkpoint. Prior single preparation/Q1 run approvals are consumed. No concrete Q2 cloud role/run has been reviewed yet.
7. Retain S3 raw/code/results, saved job definitions, idle Athena/Catalog configuration and static logs. Stop costly project compute after authorized work, update ledger/checkpoint and never touch unrelated shared-account resources.

## Athena validation completed on 26 October 2026

- **Catalog database/table/date partition created and physically queried**. No new Glue run, IAM change, crawler, EC2, notebook or schedule was introduced this turn.
- Full accepted population reconciles: **4,465,985 transactions, 1,056 positive labels, seven payment formats**. Athena read **1,628,879 summary rows**. Both amount columns read as **decimal(38,8)**, with zero missing amount rows and zero invalid count rows. Fractional Bitcoin totals remain represented (11,050 fractional paid-Bitcoin groups across formats). This supersedes earlier claims that actual cloud Q1 Parquet had not been independently read.
- USD payment-currency population: **1,634,628 transactions, 382 positive labels**. Its seven format counts, rates, lifts and support flags exactly match an independent scan of the original selected-input gzip, whose SHA256 matches the ingestion manifest. Top-20 bank-pair/format query ordering and N/L/baseline values also match the independent source calculation.
- Observed USD ACH: **134,032 transactions / 259 positive labels**, rate **0.193237%**, lift **8.268883** vs the USD baseline (~0.023369%). This is a synthetic historical one-day description, not a production prediction.
- **Support limitation:** with the current demo bank-pair/format support minimum 1,000, **57 segments qualify (75,388 transactions), but none contains a positive label**. The top 20 therefore all have zero lift; do not present this as a positive-exposure priority list. Use the broader format view for the one-day demo; calibrate support on the planned development period before holdout. The threshold was not lowered to manufacture a positive ranking. USD Bitcoin has 12 transactions and is correctly low_support.
- SQL: `q1_validate_population.sql`, `q1_segment_ranking.sql` (v2, explicit baseline columns, deterministic ties, LIMIT 20), `q1_format_exposure.sql` in `Implementation/sql/`. Independent source auditor: `Implementation/scripts/audit_q1_usd_reference.py`.
- Three successful data scans displayed **26.36 MB**, **11.14 MB**, **3.56 MB**. Estimated scan cost ~**US$0.00025**, below US$0.001 using the checked US$5/TB example and per-query minimum; additional S3/logging/Catalog charges are separate. Combined earlier Glue compute estimate remains US$0.207778 (~US$0.21); not a finalized/account-wide invoice or hard cap.
- Query IDs/status/SQL/results: `Implementation/aws/reviews/athena-query-executions-20261026.json`. IDs:
  - DB create: `2c1951da-79a0-4de7-a050-924fd05f5d79`
  - table create: `c3f06be7-491b-4362-b166-a519df8c27b8`
  - partition: `b93c0ef7-df0a-49a9-9d7a-18a09ceebdaf`
  - rejected ordering check, no scan: `0cfeed32-ebae-4d49-8c26-a41b77df9110`
  - population/precision: `65e43660-f6e4-4ef0-b20a-a83ac0fc5cb1`
  - USD supported segment ranking: `8f0c18d4-6a26-480b-b9b6-84d846de1030`
  - USD format exposure: `43fcc7f2-9ee5-4ef7-8644-55aa1da17f41`
- Review files in `Implementation/aws/reviews/`: `q1-athena-population-rows.json`, `q1-athena-population-verification.json`, `q1-athena-usd-ranking-rows.json`, `q1-athena-usd-ranking-verification.json`, `q1-athena-usd-format-rows.json`, `q1-athena-usd-format-verification.json`, `q1-usd-source-reference.json`.
- Screenshots: `Implementation/evidence/q1-athena-reconciled-20261026.jpg`, `q1-athena-usd-segments-20261026.jpg`, `q1-athena-usd-formats-20261026.jpg`. The format screenshot is a readable current viewport with table/results; live browser tab marked deliverable, but can be closed safely.
- Browser workgroup switch initially showed an Acknowledge settings dialog and reset the editor; after acknowledgement re-pasted exact SQL and disabled result reuse. First check query's ORDER BY GROUPING(alias) was rejected before scanning; simplified ORDER BY payment_format and reran successfully. These were SQL checks, never Glue retries.

## Latest Q1 completion

- Job **is459-aml-q1-dev**, AWS run ID **jr_8294653931045d22019ac21fc20f4d840159cba73f0600cc03aa25ee752a30c9**.
- Status **Succeeded**. Start **26 October 2026 16:26:28**, end **16:29:25** Singapore. Execution **169 seconds / 2m49s**, startup **8 seconds**, usage **0.094167 DPU-hours**.
- Glue 5.1, two G.1X workers, timeout 15 minutes, retries 0, concurrency 1. No auto scaling, queueing, VPC connections, Catalog metastore integration, optional metrics, Spark UI or lineage.
- Script `s3://is459-aml-g2team7-160885259244-us-east-1/scripts/q1/q1_risk-v1.py`; exact complete editor source compared with the frozen local copy before save. Local source: `Implementation/jobs/q1_risk.py`; frozen deployed copy: `Implementation/releases/q1-v1/q1_risk-v1.py`. The docstring's old prepared/not-deployed wording is historical; preserve the executed source.
- Parameters: `--preparation-report=s3://is459-aml-g2team7-160885259244-us-east-1/quality/preparation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/report.json`; `--output-root=s3://is459-aml-g2team7-160885259244-us-east-1`; `--analysis-id=q1-dev-20220901-v1`; custom logs `/is459/aml/q1`; temp `temporary/q1/`.
- Q1 quality **PASSED**, independently compared to the preparation report: **4,465,985 transactions and 1,056 labelled laundering**; dataset/run/analysis identity matches. Daily grain retains both currency dimensions, bank pair, format, date and dataset/run. Amount sums remain exact decimal(38,8).
- Report: `s3://is459-aml-g2team7-160885259244-us-east-1/quality/q1/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q1-dev-20220901-v1/report.json`.
- Daily counts: `s3://is459-aml-g2team7-160885259244-us-east-1/gold/risk/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q1-dev-20220901-v1/daily_counts/`.
- Local report: `Implementation/aws/reviews/q1-report-q1-dev-20220901-v1.json`; terminal evidence `q1-terminal-console.txt`. Q1 cloud Parquet was subsequently independently read and verified through Athena, as detailed above.
- Q1 role **AWSGlueServiceRole-is459-aml-q1** exists, trusts only Glue, and has exactly one policy **is459-aml-q1-data-access**. Reads v2 facts/labels/report and Q1 code; lists needed prefixes; manages only Q1 gold/quality/temp; writes project Q1 logs. No administrator or Catalog permissions. Verified after creation. Both policy/trust sources and approval hashes are in `Implementation/aws/` and `reviews/q1-pending-authorization.json` (historical filename; status now consumed/completed).
- User approval: “yeah go ahead. All permission is allowed only let me know if the cost might be significant.” This approved the concrete Q1 role and single bounded test. Keep the earlier US$1 prototype budget as the ceiling unless the user changes it; flag significant/exceeding costs before proceeding. That earlier pause was revoked by the latest request to read the checkpoint and continue.

## Costs and cleanup

- Preparation v1: 0.183333 DPU-hours, approximately US$0.080667 compute.
- Preparation v2: 0.194722 DPU-hours, approximately US$0.085678 compute.
- Q1: 0.094167 DPU-hours, approximately US$0.041433 compute.
- **Combined Glue compute approximately US$0.207778 ≈ US$0.21**, using checked $0.44/DPU-hour example pricing, plus S3/logging/other applicable charges. This is a usage estimate, not a finalized invoice or an account-wide hard cap.
- All three processing runs are terminal. **No project compute running.** No EC2, notebook, Glue interactive session, crawler, Step Functions execution, schedule, NAT gateway or database compute was launched. Seven Athena SQL executions were subsequently completed; none remains active.
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
