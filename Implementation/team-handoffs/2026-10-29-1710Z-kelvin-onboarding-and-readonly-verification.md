# Session: local onboarding and read-only full-release verification

- **Owner / GitHub handle:** Kelvinpcw (session run with an OpenCode agent)
- **Branch / PR:** `agent/opencode-onboarding-verification`; PR pending.
- **Updated at / observation interval:** 2026-10-29T16:45Z–17:10Z (30 October 2026, 00:45–01:10 +08:00).
- **Status:** COMPLETED
- **Evidence kind:** local setup checks plus fresh AWS read-only observations

## Scope and coordination

- **Requested scope:** set up a fresh clone on Windows, verify the project account/profile, and inspect existing published results end to end without starting or changing cloud resources.
- **AWS actions:** read-only control-plane calls and small S3 reads only. No S3 writes, Athena query execution, Glue job start, Step Functions start, EC2 start, IAM change, deployment, publication change or deletion.
- **Coordination context:** read open PRs [#13](https://github.com/Kelvinpcw/is459-aml-project/pull/13) (configuration-only rerun source; interrupted preparation cancelled and its isolated stack deleted) and [#14](https://github.com/Kelvinpcw/is459-aml-project/pull/14) (read-only orchestration-check handoff). Neither changes the current publication.
- **Account/region verification:** the member-created local profile `is459-project` resolved to account `160885259244`, region `us-east-1` at 2026-10-29T16:50Z. The repository guard returned `OK`. The local `default` profile was not used.

## Changes and checks

- **Repository source changed:** none. This record is the only new tracked file.
- **Local tools installed:** AWS CLI v2.39.1, Python 3.11.9 and GitHub CLI 2.103.3 via `winget`, with the user's approval. A project `.venv` was created from Python 3.11 and `Implementation/requirements.txt` was installed.
- **Local tests:** the synthetic suite ran on Windows. 82 tests passed; remaining failures were environment-specific, not code failures: PySpark local Parquet writes need `winutils.exe`/`HADOOP_HOME`, four profile-guard tests pass a Windows path to POSIX Bash, and one dashboard packaging test needs symlink privileges. The affected code paths were not changed. Re-running with `PYSPARK_PYTHON` pointed at the venv fixed the Python-worker failures; the Parquet-write cases still need a Windows Hadoop shim or WSL.
- **Release checked:** `full-20261028-v1` remained the current publication throughout. The pointer SHA256 exactly matched the downloaded manifest bytes, and the preparation, Q1, Q2 and evaluation quality reports all reported `PASSED`.
- **Inputs:** the raw full-run prefix contains the gzipped transaction/account ingestion copies, an empty quarantine artifact and the ingestion manifest. Object sizes match the manifest; the manifest records the original CSV SHA256 and sizes. The original CSV itself is not stored in the bucket, so its bytes were not independently re-hashed in this session.
- **Preparation:** 31,898,238 input transactions accepted, 0 quarantined, 35,230 positive labels, 28 date partitions, separate label/reference prefixes, and a label-free curated fact contract. A sampled curated partition had no laundering column, exact `decimal(38,8)` amounts and populated entity fields.
- **Q1:** 28 daily partitions; the report totals reconcile to preparation. Independently summing the 2022-09-01 partition reproduced 4,465,985 transactions and 1,056 positive labels, with exact decimal amount columns.
- **Q2:** 28 daily snapshots over overlapping seven-day lookbacks; 2,251,155 case instances and 81,321,105 evidence memberships including case overlap. No snapshot was truncated or incomplete for its declared window; six early snapshots correctly disclose incomplete pre-dataset history. A sampled case bundle's header hash, declared evidence count and JSONL evidence rows matched its case-index row; source IDs use the original file checksum plus ordinal.
- **Evaluation:** frozen calibration, holdout population 15,025,129 transactions and 17,632 positives. Reported detector precision 0.197%, recall 65.94%; matched-volume amount baseline precision 0.242%, recall 80.80%. Typed eligible-attempt recovery was 122/122 (100%) versus 91.80% baseline coverage, an 8.20 percentage-point gain, so the frozen +5 pp target was met. The detector is a low-precision, high-volume alert set; the baseline is better on individual-payment classification.
- **Orchestration:** five state machines and five executions were observed. The original full pipeline failed in the parallel stage; a Q1/Q2/Catalog recovery was deliberately aborted for a cost pause; two evaluator attempts were aborted/failed; the final evaluator+publish recovery succeeded. No single execution completed the whole chain end to end; the current release reuses completed upstream outputs.
- **Catalog/Athena:** database `is459_aml_full` has Q1 and Q2 tables at the pinned release locations with 28 partitions each. The dashboard workgroup is enabled with a 512 MiB per-query scan cutoff; recent successful queries from 29 October read the same dataset/run and table names as the current release. No query was running during the check.
- **Visualisation:** the connected app verifies `published/current.json` and pins reads to its manifest. Recent dashboard workgroup queries used the current release. The temporary dashboard stack is `DELETE_COMPLETE`; no project EC2 instance or SSM-managed instance exists. The local app was not restarted in this session.
- **Compute/cleanup:** no running Glue job, Step Functions execution, Athena query or project EC2 instance was observed. The `is459-aml-rerun29` stack is `DELETE_COMPLETE`, its jobs/roles/state machine are absent, and no EventBridge/Scheduler schedule was found. The `is459-aml-full-v1` stack is `UPDATE_COMPLETE` with idle job/workflow definitions. S3, Catalog metadata and CloudWatch logs are retained and remain chargeable at rest.
- **Limits:** this was a scoped project check, not an account-wide inventory or billing audit. Original-file bytes, all 433 Q1 Parquet objects and all Q2 bundles were not re-read; one Q1 day and one Q2 case bundle were independently checked. No new Athena query was run. Formal UI latency/user-acceptance measurements were not re-measured.

## AWS scope and cleanup

`AWS: read-only`. No compute was started or stopped. The temporary dashboard and the interrupted rerun stack were already deleted before this session; retention of S3, Catalog, logs and idle definitions is deliberate. Detailed resource locators, raw reports, query history and cost records remain private with the operator.

## Next teammate / agent

- **Next safe step and owner:** reuse the current published release and its outputs. A live local dashboard walkthrough or any new Athena query needs separate approval because normal Athena/S3 read charges apply. A fresh processing run or deployment needs fresh scoped permission, a new attempt identity and ownership coordination.
- **Blockers / don't repeat:** do not rerun preparation, Q1, Q2, evaluation or publication to reproduce this evidence; do not restart terminal Step Functions executions. For full local Spark tests on Windows, install a reviewed Hadoop `winutils` shim or use WSL; that is a local environment choice, not a pipeline change.
- **GitHub sync:** pending push; update this line with the PR link after publication.
