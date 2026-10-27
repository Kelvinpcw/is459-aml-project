## FULL WORKFLOW RUNNING — do not start again

The approved named execution is **RUNNING**: `arn:aws:states:us-east-1:160885259244:execution:is459-aml-full-pipeline:full-20261028-v1`, started **28 October2026 03:34:07 Singapore**. Start request/response: `Implementation/aws/reviews/full-workflow-request.json`, `full-workflow-start.json`. **Never call the start phase again.** Use `deployment/monitor.py --profile IS-459-BDA --enforce-budget` or the read-only status phase. The original **US$30 total ceiling** remains active; nominal compute max14.19 and output-estimate guard10 plus other reserves. Exact roles/config/code/input were verified before execution in `full-deployment-verification.json`.

First full preparation run: `jr_f0de5b0ce1549c24b37f25e1319158643acb135ca646c717f38cbc30c23b9887`, job`is459-aml-full-prepare`, five G.1X workers,45min timeout,0retries. Last observed RUNNING at330execution seconds; no Q1/Q2/evaluator run yet at that observation. Later state is in `full-monitor-latest.json` and `full-latest-status.json`; always read those before acting. Published pilot remains until all full gates pass.

Full stack `is459-aml-full-v1` is CREATE_COMPLETE, all six approved role trusts/policies and five job definitions match exact reviewed parameters. CodeVersion/full source is frozen`full-v1`, commit`7aaa65c`, package source-tree SHA`73eef6902a704b49b9b90957c068051b1e820f68e60409ab682b764039f2e4d7`. Complete raw input uploaded and checksum-verified:796,449,934byte transactions gzip,44,719,352byte accounts gzip,empty quarantine and manifest;31,898,238records/35,230labels.

Draft PR5: https://github.com/Kelvinpcw/is459-aml-project/pull/5 (attached). Add actual full results/cleanup to this PR. The future dashboard/SSM role is already specifically approved in the same seven-role confirmation; do not re-ask for the unchanged reviewed dashboard template. No EC2 launched yet. Official t3.small Linux price verified0.0208USD/hour in `dashboard-price-check.json` (IPv4/disk separate). Launch only for final validation, then delete its own stack and confirm termination/root-volume deletion.

Monitor current jobs to terminal, diagnose failures without overwriting frozen outputs or blindly retrying. Any recovery needs a new immutable script/output identity when code changes and must stay within remaining30; do not retune using holdout answers. Final tasks: observe/report full counts, evaluate metrics/baselines/target, validate private EC2 app, record performance/recovery/UI evidence, remove costly compute, update documentation/checkpoint/ledger/PR. Local server session69287 and CUA`projectTab`may still be running; no AWS server cost from that local process.

---

## Access approval received — continue deployment

The user explicitly answered **“Approve these exact roles and deployment”** to the prepared seven-role review on28October. This resolves the earlier automatic-review rejection; do not ask again for these unchanged grants. Exact template hashes/account/region/budget are recorded in `Implementation/aws/reviews/full-access-grant-authorization-20261028.json`. Proceed with the approved full stack and future dashboard stack, retaining the **US$30** total ceiling. Full input/code uploads have completed; check their review records. No full-data paid run has started yet.

## Current blocker — new AWS access approval

Automatic approval review rejected `deploy.py --phase create` before execution because the new persistent IAM roles require action-time approval for their exact grants. **Do not bypass the rejection or retry through another tool.** No stack or full-data paid run has started. Review `Implementation/aws/reviews/full-access-grant-review-20261028.md`; the next user approval question covers the six full-pipeline roles plus the future read-only dashboard/SSM role in the exact templates, with the US$30 budget unchanged. Code uploaded successfully; draft PR5 opened and attached. Full input upload is still in progress in session43603; read `/private/tmp/is459-full-upload.log` and its final review before retrying.

## Frozen full-data build ready — 28 October 2026

`Implementation/releases/full-v1/` is now frozen and must not be edited. Its deterministic package manifest and per-file SHA256 values are recorded in `manifest.json`; source/ZIP contents passed credential inspection. Full67test suite and final application smoke passed. Final **US$30** ceiling: nominal maxcompute14.19 plus output-estimate guard10 and other overhead/prior charges. Glue capacity and default VPC preflight passed. Input upload/code upload/idle stack creation are next; check their review records before retrying any operation. **No full-data paid processing has started yet.**

## Latest active build — 28 October 2026

Continue the user's **whole-project completion** task on `codex/project-completion`; latest budget is **US$30 total**, replacing US$80. No full-data paid run has started. Do not stop at the old evaluator milestone. Implementation and checks are ready for final packaging; all67local tests passed after the latest baseline/eligibility changes. Both CloudFormation templates pass cfn-lint; AWS validated the full template before the latest budget/CodeVersion parameter update. Regenerate/validate current templates before deploying.

The complete input copy is ready at `Implementation/data/full-20220901-29-v1/`:31,898,238selected/source records,35,230positive labels,0outside/ingestion-quarantined. Original files unchanged; do not regenerate it. `Implementation/deployment/upload_input.py` performs conditional multipart uploads with per-part server SHA256 and whole-local-file verification to new `raw/full-v1/`; **not run yet**.

New software: `pipeline/release.py`, `dashboard/app.py`/`data.py`, `jobs/q2_distributed.py`, `q2_snapshots.py`, `evaluate_distributed.py`, `control.py`; deployment generators/driver/bundle builder in `Implementation/deployment/`, export/publish CLIs in scripts. Read `Implementation/RUNBOOK.md`. Q2v2 uses balanced2hop cycle joins (no open3hop expansion), degree64cycle scope,200m path guard,2m cases/snapshot and full checksum-addressed evidence chunks. Full workflow has28overlapping7day snapshots. Evaluator separates1–8development,9–16holdout,17–28sparse tail, selects no future snapshots, reports both matched-volume and frozen-fraction amount baselines and all5pattern metrics, freezes a5percentage-point improvement target before holdout. Early unavailable history and cycle exclusions are explicit. No v2 cloud/scale/performance claim yet.

US$30 limits: prepare5workers/45min, risk5/45min, detect10/120min, evaluate5/45min, control2/10min×3; all0retries/concurrency1. Nominal maximum compute US$14.19; per-snapshot conservative output-cost guard US$10; prior recorded Glue estimate US$0.280623 plus small queries/storage. Estimates are not billing caps. Final processing may proceed within the user's scope once code freeze/checks are complete; flag inability to fit30before exceeding it.

Next: final dashboard visual check is open locally at127.0.0.1:8501; server session69287, CUA handle `projectTab` in IAB, though IDs are transient. Local server file watching is now disabled to avoid rebuilds during testing. Do not create/reselect a browser just because context changed; `cua.rewriteDocumentation()` if resuming computer use from summary. CUA proof screenshots should be saved and embedded when reporting UI work. Preliminary faded screenshots were removed; preserve older committed evidence. No EC2 exists yet.

Then run final packaging: `deployment/build_bundle.py` freezes a **new** `releases/full-v1/` (not built yet, never edit after freezing), inspect new files for credentials, commit source/evidence and create a PR. `deploy.py` requires explicit profile and phase upload/create/start/status/dashboard/remove-dashboard. Profile **IS-459-BDA** is verified project160885259244/us-east-1; default is different and prohibited. Deploy helpers never automatically start on upload/create. Current published pilot is `pilot-20220901-m00-v1`; S3pointer changes only after all full gates and ETag CAS. Full user authorisation30is current, historical one-minute approvals remain consumed and pilot must not rerun.

Temporary logs in `/private/tmp/`: `is459-final-budget30-suite.log` (67passed/45.599sec), `is459-balanced-cycle-tests.log` (4passed), `is459-wider-eval-budget30-tests.log` (2passed), `is459-full-ingestion.log`. The latest67suite includes current kernel cleanup, full gate coverage checks, matched/frozen baselines and pattern metrics. Subsequent changes are operational docs/helpers and graph resizing; the application test is rerun for that UI change. Working tree is not yet committed. New pilot release/ledger records exist.

---

## Budget revision — 28 October 2026

The user's latest instruction is **“change the limit to $30.”** The final total project ceiling is now **US$30**, superseding the earlier US$80 instruction below. **No full-data paid run has started.** Only the earlier pilot processing and new small S3 publication/live-dashboard queries exist. Reconfigured full-run maxima: preparation5workers/45min, Q1 5/45min, Q2 10/120min, evaluator5/45min, control2/10min×3, zero retries. Compute timeout estimate **US$14.19** at0.44/DPUh; output cost guard **US$10** (conservative30dayS3storage/PUTs), with remaining room for prior charges/startup/logs/short dashboard validation. These are estimates, not hard billing caps. Do not exceed US$30 or reuse stale US$80 budget arguments/tags. If final validation cannot fit, flag the concrete cost instead of proceeding.

## Active continuation — 28 October 2026

The user requested **completion of the entire project**, followed by a **full-dataset run with US$80 total project ceiling** once implementation/checks are ready. Keep the earlier US$1 development ceiling until that final phase. Do not stop at the evaluator milestone below. Current branch: `codex/project-completion`; implementation is in progress and not yet committed. Read `Implementation/COMPLETION_PLAN.md`.

New publication layer and read-only Streamlit dashboard are implemented locally. Eight publication/data-contract tests pass; two distributed detector tests pass; two distributed evaluator tests pass. Dashboard application testing is in progress. A clearly labelled pilot release was published through the new gate after checking raw report hashes, Catalog locations and actual Parquet population counts. Small S3 objects only; no new Glue run, IAM grant or query was started for publication. Gate source: `Implementation/pipeline/release.py`; CLI: `Implementation/scripts/publish_release.py`; release: `published/releases/pilot-20220901-m00-v1/manifest.json`, initial pointer `published/current.json`. Proof: `Implementation/aws/reviews/pilot-release-published-20261028.json`. Existing pilot report limitations remain explicit.

New distributed detector/evaluator source files are working drafts, not frozen/cloud-deployed: `Implementation/jobs/q2_distributed.py`, `evaluate_distributed.py`. Detector uses distributed fan aggregation, bounded 2–4-cycle joins, explicit degree exclusions and chunked complete evidence; its query-plan lineage is cut between stages to avoid plan-memory explosion. Evaluator uses full population joins and exact bounded reference matching, but broader snapshot/scoring-period integration, calibration artifact creation and production entry points are still being completed. Do not claim full-scale/cloud/holdout validation.

Remaining: finish/test application, distributed snapshot/evaluator contracts, orchestration/deployment/teardown and costed final run. No full-data paid run has started; all five prior AWS Glue runs remain terminal. User's full-project request authorises continuing scoped project work; preserve old pilot outputs and avoid unrelated resources.

---

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
