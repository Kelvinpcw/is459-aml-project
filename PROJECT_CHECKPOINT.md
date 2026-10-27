# IS459 AML project — checkpoint

Updated **28 October 2026, Singapore**. The user explicitly resumed and supplied their project CLI profile. **The scoped evaluator continuation is complete; no known project compute or queries are active.** S3 data/results and idle definitions are retained. No further deployment or processing has started.

## Resume here

1. Read `AGENTS.md`, `README.md`, `Implementation/STATUS.md`, requirements and the relevant review before choosing the next scoped task. Reading this checkpoint is not authority for a new paid run or IAM grant.
2. Evaluator cloud completion is **done**. Do not rerun preparation, Q1, Q2, evaluator or completed Athena queries. All five recorded run approvals are consumed. Preserve immutable pilot outputs and frozen releases.
3. Next architecture gap is the **shared release gate and single published-run manifest**. Begin with a scoped local design/implementation using existing contracts and synthetic tests. No publication, orchestration, dashboard/EC2 or wider paid processing is pre-started. Coordinate owners/contracts before shared deployment.
4. Scalable wider-window Q2, development calibration, frozen holdout evaluation, dashboard and Step Functions remain incomplete. Do not widen the bounded driver graph/remove its 50,000-row guard or claim independent minute windows preserve cross-boundary patterns.
5. Existing **US$1 total prototype budget** remains. Estimated recorded Glue compute is **US$0.280623**, plus S3/logs/Athena/Catalog and applicable overhead; estimates are not an invoice or hard cap. Flag material cost before further work. Retain S3; stop project-created costly compute after any authorised activity. Avoid unrelated shared-account resources.

## Account and authentication

Expected account **160885259244**, Region **us-east-1**, user **g2team7**. On this member's machine, the user selected **`IS-459-BDA`**. It was verified using `bash Implementation/scripts/check_aws_profile.sh IS-459-BDA` and the configured region matched. **The default profile is account 372014757586 and must not be used for this project.** Profile names/authentication are local to each teammate; reverify before cloud actions and use explicit profile/region. Never copy credentials into the repository or chat.

## Evaluator cloud completion — fresh 28 October observations

- Job **is459-aml-evaluation-dev**, run **jr_4791027e006652a752058e511a3d00afa0ac3e2c5bf19145ad72437b8db6fe23**, evaluation **eval-dev-20220901-m00-v1**, **SUCCEEDED**. Start **01:37:35**, end **01:40:16 Singapore**; execution **153 seconds**, **306 DPU-seconds / 0.085 DPU-hours**. Glue5.1, two G.1X workers, 15-minute timeout, retries0, concurrency1, no triggers/VPC/new IAM grants.
- Existing evaluator role **AWSGlueServiceRole-is459-aml-evaluation** was verified: Glue-only trust, exactly one reviewed managed policy, no inline policies. Existing uploaded manifest and original annotations matched their pinned raw SHA256 values; no reuploads or grant recreation.
- Frozen source `Implementation/releases/evaluation-v1/evaluate_q2-v1.py`, SHA256 **0416846ba0c00b93b77c122c4d663051d8480131de89b0f6cd2cc2b35639a9ec**, source commit **bc7e3fc9e777eaf1d2120c323aea65726e853bbf**. Uploaded conditionally to `scripts/evaluation/evaluate_q2-v1.py`; downloaded and byte-hashed. Every reviewed job field matched the saved API definition. The historical `evaluation-job-draft.json` is now deployed.
- The evaluator reconciled **4,465,985 facts/labels** before the bounded window. **43,681 eligible transactions**, **15 fan-out cases**, **840 distinct supporting alerts**, **0 positive labels**, **2,756 annotation attempts, 0 eligible**. Recall/lift/recovery are null because the denominators have no positives/eligible annotations. These are mechanics/traceability results, not proof of detector effectiveness or case-level falsehood.
- Quality **PASSED**. All **four actual raw S3 objects** were downloaded, independently hashed and byte-length checked against frozen local predictions. All matched, including the complete attempt audit and alert lists. No expected hashes/source/configuration were changed. Cloud copies are in ignored `Implementation/data/evaluation-cloud-m00-v1/`.
- S3 bucket **is459-aml-g2team7-160885259244-us-east-1**. Suffix `dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q2-dev-20220901-m00-v1/evaluation_id=eval-dev-20220901-m00-v1`. Four artifacts under `evaluation/<suffix>/`; report at `quality/evaluation/<suffix>/report.json`. Do not overwrite/reuse this attempt.
- New run compute estimate **US$0.037400** at checked US$0.44/DPU-hour. Existing US$0.243223 + this run = **US$0.280623**. Other charges separate. [AWS Glue pricing](https://aws.amazon.com/glue/pricing/) checked 28 October 2026.
- At **2026-10-28T01:41:00.120855+08:00**, all **five known Glue runs** and **ten recorded Athena statements** were freshly read as terminal. No evaluator triggers exist. This is a scoped project audit, not an account-wide billing/resource inventory. No deletions were necessary; no unrelated resources were changed.

## Evidence to read

- `Implementation/results/EVALUATION_CLOUD_VALIDATION.md` — result, complete hashes, limitations and costs.
- `Implementation/aws/reviews/evaluation-cloud-verification-m00-v1.json` — raw-file verification, terminal project job/query inventory.
- `Implementation/aws/reviews/evaluation-run-api-20261028.json` and `evaluation-job-deployed-api-20261028.json` — actual AWS API responses.
- `Implementation/aws/reviews/evaluation-preflight-api-20261028.json` — exact existing grants/inputs verified before deployment.
- `Implementation/aws/reviews/evaluation-report-eval-dev-20220901-m00-v1.json` — PASSED quality report.
- `Implementation/aws/last-api-verification.json`, `resource-ledger.json` — current resource/cost state. `last-console-verification.json` is older console evidence, superseded by the API verification for this continuation.
- `Implementation/aws/reviews/evaluation-pending-authorization.json` — historical filename; current status is consumed and successfully verified.
- Local tests/replay previously covered all49 tests; not rerun this continuation because production source did not change. Cloud execution/raw-file comparison is new evidence.

## Earlier validated scope and integration

Preparation/Q1 remain validated for **1 September 2022 only**: 4,465,985 accepted transactions, 1,056 positives, zero quarantine/unknown endpoints. Q1 currency-specific counts/rates were physically validated through Athena. Its one-day bank-pair support threshold leaves zero-positive qualifying segments; do not present zero-lift rankings as useful priorities.

Q2 remains a **bounded first-minute development detector**, 00:00 inclusive to00:01 exclusive on1September, dataset-local time/cutoff00:01. It reads no labels/annotations/Q1 scores/evaluation. 15fan-out cases/840evidence transactions, nofan-in/cycles. All complete bundles and physical Athena index rows were verified previously. Full input31,898,238transactions has not been processed in full.

Q1's manual GitHub push/pull connection remains on **codex/glue-github-connection**, repository `Kelvinpcw/is459-aml-project`, folder `Implementation/glue/is459-aml-q1-dev`; integration PR3 is open, main has not been merged. Preparation/Q2/evaluator have no GitHub connection. Do not repeat successful sync for screenshots, retrieve stored credentials or silently switch the connected branch. See `Implementation/glue/README.md` and the27October integration review. This continuation uses separate branch **codex/evaluator-cloud-completion** and does not change the shared Q1 job.

The complete previous handoff/history is preserved at `Implementation/aws/reviews/checkpoint-before-evaluation-cloud-completion-20261028.md`. Its unsaved-job/unconsumed-approval instructions are historical and superseded by this checkpoint.
