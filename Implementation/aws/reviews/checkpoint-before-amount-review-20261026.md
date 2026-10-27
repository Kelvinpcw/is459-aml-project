# IS459 AML project — paused checkpoint

**Updated: 26 October 2026 (Asia/Singapore). Status: PAUSED at the user's request; the single approved preparation run SUCCEEDED and has ended. No project compute remains running.**

## Latest completed run — resume from this section

- The user requested a checkpoint and a pause again because they were running low on tokens. They permitted leaving the bounded run to finish if it would stay within the US$1 budget; the final status check showed it had already finished successfully.
- Job: `is459-aml-prepare-dev`.
- AWS run ID: `jr_ab63943d9cb2bfe3f8e7b96be19b04f1542190619123946ae313ef7d1a2f872d`.
- **Final status: Succeeded**, verified in Glue Studio at **26 October 2026 03:09:43 Singapore time**.
- Start: **03:03:35**. End: **03:09:14**. AWS execution time: **5 minutes 30 seconds**; startup time: **8 seconds**.
- AWS-reported usage: **0.183333 DPU-hours**. At the checked published $0.44/DPU-hour example rate, this is approximately **US$0.0807 in Glue compute**, plus S3/logging/other applicable charges. This is an estimate from reported usage, not a finalized invoice or an account-wide spending cap.
- Runtime: Glue 5.1, 2 G.1X workers, 2 DPUs. Timeout 15 minutes, retries 0, concurrency 1. **One run only; do not start another run under the consumed approval.**
- **Cleanup: the Glue execution is terminal; no running project compute needs stopping.** No EC2, notebook, crawler, schedule, NAT gateway, database or other continuously running service was started by this task. Keep S3 data/code/results as requested. Small static CloudWatch log storage can remain for debugging; it is not running compute.
- **Not yet done:** the final S3 quality report has not been downloaded or independently reviewed. AWS job success alone should not be presented as a complete independent validation of the project.
- Expected report: `s3://is459-aml-g2team7-160885259244-us-east-1/quality/preparation/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v1/report.json`.
- On resume, **read this existing report first**; do not launch another job. Check status PASSED, dataset/run identity, input rows against the manifest's 4,465,985 selected rows, accepted + quarantined reconciliation, account join coverage, no row multiplication, label separation and the payment-format reference totals. If quarantine is zero, compare accepted per-format N/L counts to the local manifest exactly. Preserve/report unmatched account mappings rather than dropping them.
- Relevant browser pages last observed: job `Runs` with Succeeded status; S3 quality-report prefix; CloudWatch raw driver logs under `/is459/aml/preparation/error`. Tabs are transient and may be closed safely. Do not depend on old tab IDs.
- After report review, proceed with Q1 preparation. Additional paid executions and new service-role grants require their own authorization; the user has only approved the preparation role and the one completed test.

**The sections below preserve earlier setup history. Any references to zero runs or a pending first-run approval describe the pre-launch state and are superseded by the completed-run section above.**

## User instructions that must persist

- The user resumed work on 26 October, then explicitly requested another checkpoint and pause. **Stop until the user asks to resume again.**
- The user subsequently approved **one preparation test run with a US$1 budget** by replying “yeah sure” to that specific request on 26 October. That run has started. Additional paid runs/retries are not approved.
- After authorized project processing/demo work is complete, stop/tear down project-created costly compute and other continuously billed resources. S3 data may remain.
- Scope cleanup to this project's resources. Do not change unrelated resources in the shared AWS account.
- The user approved the specific preparation role and policy described below. Do not request the same permission again unless its scope changes. Other service-role grants have not been approved.

## What is already decided

- IBM HI-Medium synthetic AML dataset; two confirmed questions:
  1. Historical laundering exposure by payment format and bank-pair segment, with rates, volume, support and currency-aware baselines.
  2. Label-free connected-account investigation using fan-in, fan-out and bounded 2–4-account cycles; labels/pattern annotations are evaluation inputs only.
- Keep the existing proposed architecture. See `Proposal/Project_Proposal.md` and `Proposal/Architecture/Pipeline_Explanation.md`.
- Shared preparation → independent Q1/Q2 → isolated evaluator → validated published-run manifest → dashboard. S3/Glue/Athena/Step Functions; an on-demand EC2 dashboard comes later if authorized.
- Development/calibration: 1–8 September 2022. Holdout: 9–16 September. Sparse 17–28 September tail reported separately.

## AWS identity and safety boundary

- **Correct project account: `160885259244`; console IAM user `g2team7`.**
- Region: **`us-east-1` (N. Virginia)**.
- The console user has AdministratorAccess and AWSBillingReadOnlyAccess attached; organization restrictions/quotas have not been exhaustively checked.
- **The local AWS CLI is authenticated to a DIFFERENT account. Do not run project mutations through it.** Only a read-only STS identity check was made; no other-account resources were changed. Use the signed-in project console or explicitly configure a matching authorized session later. Never extract browser credentials.
- Chrome extension reconnected during setup. The latest observed browser ID was `4`; these IDs are transient. Re-discover current state on resume. The user enabled the upload setting themselves; direct file selection subsequently worked.

## Cloud resources actually created

1. **S3 bucket:** `is459-aml-g2team7-160885259244-us-east-1`
   - Private; all public access blocked; ACLs disabled/bucket owner enforced; SSE-S3 default encryption; versioning disabled.
   - `raw/development/20220901/transactions.csv.gz`
   - `raw/development/20220901/accounts.csv.gz`
   - `raw/development/20220901/manifest.json`
   - `raw/development/20220901/ingestion-quarantine.jsonl.gz` (empty: no ingestion rejects)
   - `scripts/preparation/prepare.py`
   - Both upload status screens reported success. Development input upload: 4 files, about 148.5 MiB total. Original full data files were not uploaded.
2. **IAM policy:** `is459-aml-prepare-data-access`
3. **IAM role:** `AWSGlueServiceRole-is459-aml-prepare`
   - Trust: `glue.amazonaws.com` only.
   - Exactly one policy attached: the project preparation policy above.
   - Reads project raw input and preparation scripts; manages only preparation output prefixes and writes project preparation logs. No administrator policy attached to this service role.

4. **Glue batch job:** `is459-aml-prepare-dev`, saved and verified on 26 October. Glue **5.1**, G.1X, **2 workers**, timeout **15 minutes**, retries **0**, concurrency **1**. No VPC connections, auto-scaling, queueing, lineage, optional metrics, Spark UI or Glue Catalog metastore integration. Uses the approved preparation role, project script/temporary prefixes, explicit input/output/run parameters, SSE-S3 and project tags. The saved code was checked against the complete local source.

**No Glue job was started. The saved job's run history shows “Job runs (0)” and “No job runs.”** The previous unsaved draft was discarded on 25 October; a complete definition was recreated and saved on 26 October. Do not recreate a duplicate job.

No EC2 instance, Glue notebook/interactive session, crawler, Athena query, Step Functions execution, NAT gateway, VPC endpoint, database or schedule was launched by this task. **There is no project compute to stop or tear down at this checkpoint.** This is a statement about this task's resources, not a claim about unrelated resources or total account charges.

## Local work saved

- `Implementation/scripts/build_development_input.py`: standard-library streaming ingestion helper, checksums and stable source IDs; preserves original files and duplicate transactions; scans the entire unsorted transaction file before selecting a date scope.
- `Implementation/jobs/prepare.py`: Glue 5.1 preparation script. Explicit columns, decimal amounts, bank normalization, endpoint joins, account-key uniqueness, row reconciliation, label separation, run-specific Parquet and a passed/failed quality report.
- `Implementation/jobs/q1_risk.py`: prepared Q1 Spark script with additive daily N/L counts and separate paid/received currency totals. **Not deployed.**
- `Implementation/sql/q1_segment_ranking.sql`: query template only; no Athena table registered or query executed.
- `Implementation/aws/preparation-job.json`: reproducible configuration for the saved batch job. Console-generated parameter serialization may differ, but runtime, limits, paths, integrations, role and custom parameters were verified in the saved UI.
- `Implementation/aws/preparation-trust-policy.json` and `preparation-permissions-policy.json`: reviewed policy sources.
- `Implementation/aws/environment.json`, `resource-ledger.json`, `Implementation/TEARDOWN.md`, `Implementation/SETUP.md`: setup and cleanup records.
- `Implementation/tests/test_ingestion.py`: eight tests, all passed.
- `Implementation/data/development-20220901/`: generated development input (ignored by the local .gitignore), already uploaded.
- `Implementation/evidence/`: screenshots of private bucket settings, approved policy review, created role, upload success and paused Glue job list.

## Actual development-data results

- Dataset version: **`ibm-hi-medium-b1b99c68b765580f`**.
- Entire source scanned: **31,898,238** transaction records.
- Selected: **4,465,985** transactions dated **1 September 2022**; end date 2 September is exclusive.
- Selected laundering labels: **1,056** labelled 1; **4,464,929** labelled 0.
- Outside selected development scope: **27,432,253**.
- Ingestion quarantined: **0**.
- Transaction gzip: **111,036,332 bytes**. Account gzip: **44,719,352 bytes**.
- Source ID = original transaction CSV SHA-256 + `:` + original 1-based CSV data-record ordinal. The repeated Account columns are mapped positionally to sender/receiver.
- The initial development input is a single gzip transaction file. Before scaling full-file ingestion, consider chunked inputs so gzip does not serialize all CSV parsing on one task.

## Validation completed and remaining limits

- Eight ingestion tests passed: unsorted dates, duplicate preservation, stable IDs across date scopes, quarantine/count reconciliation, deterministic output, unchanged originals, overwrite refusal, empty-selection/header failures and dataset-version sensitivity.
- Python syntax compilation passed for the helper, preparation script and Q1 script.
- JSON policy/configuration files parse successfully. The IAM console policy editor validated the applied policy; its content was checked against the local JSON before role creation.
- On 26 October, a runtime compatibility issue was caught before spending: Glue 5.0 bundles botocore 1.34.131, whose official S3 PutObject model lacks `IfNoneMatch`. Glue 5.1 bundles botocore 1.40.61, which supports it. Both schemas were checked directly from the official boto/botocore GitHub tags; the saved job now uses Glue 5.1. Preparation and Q1 scripts also check SDK capability before doing data work. Updated scripts passed syntax compilation. Sources: https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-python-libraries.html and https://github.com/boto/botocore.
- **Spark transformations and AWS runtime permissions have not been exercised.** Local Python has no PySpark, and local Java is 25; do not claim Spark tests ran. No cloud run was performed because paid processing is not approved.
- No detector, evaluator, dashboard, catalog registration, release gate or orchestration has been implemented yet. Do not describe the full project as finished.

## Resume exactly here

1. Wait for the user's next resume request, then read the latest completed-run section above. Confirm the browser's project account/region before any AWS interaction.
2. **The first run has already succeeded. Review its existing S3 quality report; do not rerun it.** The one-run approval is consumed. Pricing source checked 26 October: https://aws.amazon.com/glue/pricing/.
3. The saved job already has `prepare.py` in `s3://is459-aml-g2team7-160885259244-us-east-1/scripts/preparation/`, project temporary paths, `--custom-logGroup-prefix=/is459/aml/preparation`, development input/output roots and the intended run ID. Do not switch to default `aws-glue-assets-*` paths or enable optional integrations outside the role's permissions.
4. Validate the existing quality report, reconcile counts, inspect join coverage and verify labels are absent from facts. Any future approved run needs a NEW run ID; scripts refuse namespace reuse. Do not reuse `dev-20220901-v1` or start paid retries automatically.
5. Q1 still needs a separate reviewed/approved role, gold/quality output permissions and subsequent catalog/table setup. The existing preparation role is intentionally not a Q1/Q2 role. Build Q2/evaluation/UI afterwards.
6. Follow `Implementation/TEARDOWN.md` before ending authorized runs/demos, update the ledger and verify costly project compute has ended. Preserve S3 data as requested.

Browser interaction notes: explicit click/focus before filling fields avoided a focus problem that had placed description text in the name field. For code editors, select/delete the entire document before pasting. Inspect resulting field values and UI validation before saving. Uploads succeeded using a native file picker, and then direct filechooser access worked after the user's extension refresh.
