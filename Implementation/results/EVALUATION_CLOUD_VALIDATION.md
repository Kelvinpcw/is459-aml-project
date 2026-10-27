# Q2 evaluator cloud validation

28 October 2026, Singapore. **SUCCEEDED and independently verified for the frozen first-minute development pilot.**

Job `is459-aml-evaluation-dev`, run `jr_4791027e006652a752058e511a3d00afa0ac3e2c5bf19145ad72437b8db6fe23`, evaluation `eval-dev-20220901-m00-v1`. Started **01:37:35**, ended **01:40:16** Singapore; execution **153 seconds**, reported **306 DPU-seconds** (0.085 DPU-hours). Glue 5.1, two G.1X workers, 15-minute timeout, zero retries, concurrency one. The existing approved role was reused without new IAM grants. No preparation, Q1, Q2 or Athena statements were rerun.

The uploaded script SHA256 is `0416846ba0c00b93b77c122c4d663051d8480131de89b0f6cd2cc2b35639a9ec`, unchanged from the frozen release at source commit `bc7e3fc9e777eaf1d2120c323aea65726e853bbf`. Live role/trust/policy, manifest and annotation checks matched the reviewed versions before deployment. Every field in the reviewed job configuration matched the saved AWS definition.

The evaluator reconciled **4,465,985 prepared facts and labels** before selecting **43,681 transactions** from `[2022-09-01T00:00:00, 00:01:00)`, cutoff 00:01:00, dataset-local time. It revalidated all **15 fan-out cases** and their complete evidence, then wrote a PASSED quality report and four outputs.

| Measurement | Observed |
| --- | ---: |
| Eligible positive labels | 0 |
| Unique detector alerts | 840 |
| Matched-volume amount diagnostic alerts | 840 |
| Transaction precision, both methods | 0 |
| Recall and lift | Not measurable: no positive labels |
| Annotation file attempts | 2,756 |
| Eligible attempts / recovery | 0 / not measurable |

Annotation absence does not establish that a case is false. This run verifies evaluator mechanics and reproducibility; it does not establish detector effectiveness, scalable detection, calibrated holdout performance or a published release. No scope or threshold was changed after viewing references.

All **four raw S3 objects** were downloaded and independently SHA256-hashed. Their complete bytes and byte lengths match the frozen local predictions, and the quality report's hashes/URIs agree. This checks the files themselves, not only reported hashes.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `metrics.json` | 8,041 | `539d8bc7628440d6508dd2806025fb3e321464be3daa0003eaca8a5aff5787fc` |
| `case_evaluation.jsonl` | 2,567 | `f3b1f43cb465d4c0a1941676bb4ed6d415ae61cd8fe10021f74f3ea82e422698` |
| `attempt_evaluation.jsonl` | 1,167,095 | `ff902357f7b433cf51dbf9624be473f4da3d9f14ee3a6561457dd522c4c14336` |
| `alert_source_ids.json` | 133,004 | `8546f104e9085c0551df4de761202574a2c619e2fcd4fdf2e11e40750935e203` |

The S3 suffix is `dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q2-dev-20220901-m00-v1/evaluation_id=eval-dev-20220901-m00-v1`. Outputs are under `evaluation/<suffix>/`; quality is `quality/evaluation/<suffix>/report.json` in the project bucket. Full downloaded copies remain locally under `Implementation/data/evaluation-cloud-m00-v1/` and are excluded from Git.

Compute estimate: **US$0.037400** for this run; cumulative recorded Glue estimate **US$0.280623**, plus S3/logging/Athena/Catalog and applicable overhead. [AWS Glue pricing](https://aws.amazon.com/glue/pricing/) checked 28 October 2026, using US$0.44/DPU-hour. This is an estimate, not an invoice or hard cap; the prototype budget remains US$1.

At `2026-10-28T01:41:00.120855+08:00`, all **five known project Glue runs** and **ten recorded Athena statements** were freshly read as terminal. No evaluator triggers exist. No compute remains active among those resources; S3 and idle definitions are retained. This is a scoped project check, not an account-wide inventory or billing audit.

No production source changed, so local regression tests were not rerun. The earlier 49-test coverage and independent local replay remain the local evidence; this continuation adds actual Glue execution and exact raw-file verification.

Evidence: [verification](../aws/reviews/evaluation-cloud-verification-m00-v1.json), [run API response](../aws/reviews/evaluation-run-api-20261028.json), [saved job](../aws/reviews/evaluation-job-deployed-api-20261028.json), [PASSED quality report](../aws/reviews/evaluation-report-eval-dev-20220901-m00-v1.json), [preflight](../aws/reviews/evaluation-preflight-api-20261028.json), [local validation](EVALUATION_LOCAL_VALIDATION.md).
