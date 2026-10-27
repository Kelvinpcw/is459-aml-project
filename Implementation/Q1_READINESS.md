# Current state — Q1 development validation completed

The role/job were approved and executed, and the Catalog table/date partition and Athena checks subsequently completed. Read results/Q1_VALIDATION.md and ../PROJECT_CHECKPOINT.md for current results, support limitations and query IDs. The deployment review below is historical; do not recreate or rerun its resources.

# Q1 deployment review

Status: prepared locally; AWS role grant and processing run await authorization.

Q1 answers the historical question: which payment-format and bank-pair segments show greater labelled exposure, with enough supporting volume? It is not an optimized allocation of monitoring staff.

## Inputs and outputs

- Input: verified preparation v2 transaction facts and separately stored labels, plus its PASSED report.
- Output grain: dataset/run, day, sender bank, receiver bank, payment format, payment currency and receiving currency.
- Measures: additive transaction/positive-label counts and separate exact decimal(38,8) paid/received totals. Filter the population first, sum counts, then compute rates and lift. Keep the two currency dimensions and amount units.
- The proposed first Q1 analysis ID is `q1-dev-20220901-v1`. Output is under `gold/risk/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q1-dev-20220901-v1/daily_counts/`; its report has the corresponding `quality/q1/` prefix. Stage analysis IDs allow a later separately approved attempt without rerunning preparation or overwriting a partial result.

## Validation

The production `aggregate_daily` function is exercised by local Spark tests. They cover preserving distinct source transactions, exact eight-decimal totals through Parquet, both currency dimensions, filtering before the denominator/baseline, and recomputing period rates from summed counts. Negative cases cover duplicate or missing label matches, changed label totals against the independent preparation reference, null/foreign run keys, reduced decimal precision and label leakage into facts.

18 total tests passed on 26 October 2026: the previous 12 plus six Q1 tests. The actual production query template ran against local test summaries with test-specific dates/support. Athena-specific catalog DDL is prepared from AWS documentation but has not been executed; it is a later step after Q1 output validation. Local tests do not claim a completed AWS Q1 run, and actual v2 cloud Parquet schemas/samples have not yet been independently read.

## Requested grant and run

Create policy `is459-aml-q1-data-access` and role `AWSGlueServiceRole-is459-aml-q1` in account `160885259244`. Trust only `glue.amazonaws.com`. The role may read the v2 preparation transaction facts, labels, report and Q1 code; list the necessary prefixes; write/delete only Q1 gold/quality/temp outputs; and write `/is459/aml/q1/*` logs. Spark needs delete permission to commit/clean its own output. There are no rights to change IAM, read unrelated buckets or modify the source/preparation data.

Sources of truth: `aws/q1-trust-policy.json`, `aws/q1-permissions-policy.json`, `aws/q1-job-draft.json`. The first cloud processing run would use Glue 5.1, two G.1X workers, 15-minute timeout, zero automatic retries and concurrency one. It must be explicitly authorized within the remaining US$1 test budget; previous preparation approvals are consumed. At the previously checked $0.44/DPU-hour example, 15 minutes is about US$0.22 compute, plus S3/logging. No Athena query, crawler, EC2 or schedule is part of that single Q1 job approval.

## After authorization

1. Apply only the reviewed role/policy, upload Q1 source, save the bounded job and verify source/settings against the local files.
2. Independently check the existing v2 cloud Parquet schema/sample if feasible, then run Q1 once. Record the new AWS run ID; do not automatically retry.
3. Require Q1 PASSED, 4,465,985 transactions and 1,056 positives, matching input references, complete exact amounts, immutable outputs and a terminal job state.
4. Register explicit Q1 schema/date partitions in the Catalog through a separately reviewed metadata setup; `sql/q1_catalog_draft.sql` is the equivalent table contract. No crawler is required. The Q1 processing role currently has no Catalog permissions, so automated registration is not yet implemented.
5. Prepare a restricted Athena workgroup and output prefix before any separately approved query. Then continue Q2/evaluation, shared release gate, dashboard and orchestration.

No permission grant, Q1 cloud job or paid execution is performed merely by preparing these files or the IAM review page.
