# Latest continuation — 26 October 2026

Q1 Catalog DB/table/date partition registered and independently read-validated through Athena. All-format population, both decimal(38,8) amount columns, USD format rates/lifts and supported segment ranking match source references. No new Glue run; seven SQL executions are terminal, three successful scans cost below US$0.001 estimated. No active project compute/queries. Next: Q2 implementation. See ../PROJECT_CHECKPOINT.md and results/Q1_VALIDATION.md. Earlier pause/setup notes below are historical.

# Current pause — 26 October 2026

Q1 completed in AWS: Succeeded, 2m49s, report PASSED, 4,465,985 transactions / 1,056 positives. Role/policy/code/job are deployed. No active project compute. Athena workgroup is459-aml-dev exists with private SSE-S3 output and 50 MB/query scan limit; no SQL or project Catalog registration performed yet. Next on user resume: Catalog table/date partition and bounded Athena validation over existing Q1 results. Do not rerun Glue. Canonical source: ../PROJECT_CHECKPOINT.md.

Historical setup notes follow.

# AWS implementation status

26 October 2026: preparation v2 succeeded and its report was independently verified. **No project compute running.** Canonical continuation instructions: `../PROJECT_CHECKPOINT.md`.

- Account 160885259244, user g2team7, us-east-1. Local AWS CLI uses another account; do not mutate with it.
- Private project bucket, approved preparation role/policy and one saved Glue job exist. No role permissions changed.
- Current Glue job `is459-aml-prepare-dev`: `scripts/preparation/prepare-v2.py`, `--run-id=dev-20220901-v2`, zero-quarantine limit, Glue 5.1, two G.1X workers, 15-minute timeout, zero retries, concurrency one.
- Exactly two runs exist, both terminal Succeeded. v1 incorrectly quarantined 93,554 valid transactions because it required two decimal places. v2 retains all 4,465,985 transactions and all 1,056 positive labels with zero quarantine. Account mapping/label separation and all payment-format counts reconcile.
- v2 execution 5m50s, 0.194722 DPU-hours, about US$0.086 compute; combined test compute about US$0.17 plus storage/logs. Both single-run approvals are consumed; additional paid processing needs authorization.
- User-authorized deletion of superseded v1 synthetic test outputs completed: 35 objects, approximately 414 MB, zero failures. Retained source data, code, corrected v2 results, local review evidence and small static logs.
- 12 local tests passed, including real Spark precision/Parquet/aggregation checks. Full local amount audit and independent cloud report/manifest comparison passed. Actual v2 cloud Parquet samples/schemas have not yet been independently read.
- Next: review local Q1 role/job permission drafts in `aws/q1-*.json`, prepare its security grant review, code upload, job and catalog/table setup. No Q1 deployment/grant or paid run is approved yet. No Q2/evaluator/dashboard deployment exists.
- Historical v1 config: `aws/preparation-job.json`; current reproducible intent: `aws/preparation-job-v2.json`. Review/evidence: `aws/reviews/` and `evidence/`.

See `TEARDOWN.md` for future cleanup. Keep S3. No continuously running project services were introduced.

## Q1 continuation update

Q1 aggregation and actual query template now pass six additional local Spark tests (18 total). Query points at v2; exact table/partition DDL and separate analysis-attempt ID added. IAM policy draft validated with zero errors/warnings and staged at Review and create, but not created. Pending grant/run request and source hashes: `aws/reviews/q1-pending-authorization.json`. No Q1 role/code upload/job/execution or Catalog setup performed. Full architecture status: `STATUS.md`; exact deployment review: `Q1_READINESS.md`.
