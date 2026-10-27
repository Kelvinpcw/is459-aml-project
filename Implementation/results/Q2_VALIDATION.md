# Q2 development cloud validation

27 October 2026, Singapore. **SUCCEEDED and independently VERIFIED for the first minute only. No active project compute/query remains.**

Job `is459-aml-q2-dev`, run `jr_3b40b2a7f316355a065f2df49bf430c50ca60d4d389bb49f12ba4ee4bfc35687`. Start03:45:28, end03:48:02 Singapore; execution145sec, startup9sec, 0.080556DPUh. Two G.1X, Glue5.1, timeout15min, no retries.

| Check | Result |
| --- | --- |
| Immutable input population | 4,465,985 prepared facts reconciled |
| Declared window | 2022-09-01 00:00 inclusive to00:01 exclusive, cutoff00:01, dataset-local time |
| Scoped / self / non-self transactions | 43,681 /31,702 /11,979 |
| Distinct non-self directed pairs | 11,760 |
| Leads | 15 fan-out,0 fan-in,0 cycles of length2–4 |
| Supporting evidence | 840 distinct source transactions, all retained |
| Unknown mappings / truncation | 0 /none |
| All15 cloud bundles | Every field/evidence record and deterministic canonical JSON hash matches frozen local replay |
| Actual Athena Parquet read | All15 index rows, every field, match verified cases; 5.75KB displayed scan |
| Terminal state | Glue run succeeded; table, partition and full index SQL all succeeded |

Role `AWSGlueServiceRole-is459-aml-q2` trusts only Glue and has exactly the user-created reviewed policy `is459-aml-q2-data-access`. Detector reads label-free enriched facts and a sanitized handoff. No labels/Patterns/Q1 results enter detection. Structural leads are not proof of laundering or chronological funds return. Detection precision/recall has not been evaluated.

This is a guarded driver graph prototype for one explicit minute, not scalable full-day/full-dataset Q2. Thirty local tests passed before deployment; cloud source was unchanged. Separate evaluator, shared publication gate, dashboard and orchestration remain unimplemented.

Athena table `is459_aml_dev.q2_case_index_dev20220901_m00_v1`, date partition2022-09-01. Workgroup `is459-aml-dev` retained; no provisioned capacity. Query IDs: table `4be2b02b-1167-4d58-9730-71a0f997bd7c`; partition `1b1c5ad1-8a57-4cb5-add7-f7c0a6257a85`; inventory `ec566c8f-4f0a-4011-aab2-c12a5a5d72c2`. Complete row comparison supersedes the optional aggregate-check draft.

Compute estimate for Q2 **$0.035445**, combined Glue estimate **$0.243223 (~$0.24)** at the checked $0.44/DPU-hour example; Athena, S3/logs/Catalog additional. This is not finalized billing or an account-wide cap. [Glue pricing](https://aws.amazon.com/glue/pricing/), [Athena pricing](https://aws.amazon.com/athena/pricing/) checked27October2026. Existing US$1 prototype budget persists.

Machine evidence: `../aws/reviews/q2-cloud-verification-m00-v1.json`, `q2-report-q2-dev-20220901-m00-v1.json`, `q2-athena-case-index-rows.json`, `q2-athena-query-executions-20261027.json`. Complete cloud copies `../data/q2-cloud-m00-v1/`; frozen reference `../data/q2-local-m00-v1/`. Verifier `../scripts/verify_q2_cloud.py`. Screenshot `../evidence/q2-run-succeeded-20261027.png`. All data/code/results retained in S3; no expensive service was left running.
