> **Current status — 2026-10-27T15:47:03.623179+08:00: PAUSED at user request. Exact evaluator grant approved/applied; role and input files deployed. Glue job remains unsaved; no paid evaluator run started. Resume from PROJECT_CHECKPOINT.md and finish job configuration. The single bounded-run approval is unconsumed. Earlier pending-approval statements below are historical.

# Isolated Q2 evaluator — development pilot

27 October 2026, Singapore. **Implemented, tested and replayed locally; not deployed or run in AWS.** The new evaluator access grant and single cloud test still require concrete confirmation. Preparation/Q1/Q2 remain unchanged.

## What this version establishes

The evaluator consumes frozen cases after detection. It joins historical labels only here, matches annotated source transactions against the complete eligible fact population, and writes metrics/evidence in an evaluation-only namespace. It never modifies detector inputs, rules, cases or thresholds.

The first-minute replay **passes pipeline/evidence checks but cannot establish detection performance**. Its 43,681 eligible transactions contain zero positive labels. All 2,756 annotated attempts fall outside this minute; the earliest annotation transaction is at 00:08. Detector and amount diagnostic each flag 840 distinct transactions and have 0 labelled true positives: transaction precision0; recall/lift/attempt recovery are null with explicit reasons. None of this makes 15 cases proven false or establishes a useful production/holdout detector. A wider scalable study and a frozen early-data calibration policy remain necessary.

## Frozen contracts

- Dataset `ibm-hi-medium-b1b99c68b765580f`, prep `dev-20220901-v2`, detector analysis `q2-dev-20220901-m00-v1`, proposed evaluation `eval-dev-20220901-m00-v1`.
- Window **2022-09-01 00:00 inclusive to 00:01 exclusive**, cutoff 00:01, dataset-local timestamps. Source timezone unspecified; UTC is Spark’s internal parsing convention only.
- Source is `jobs/evaluate_q2.py`, frozen deployment copy `releases/evaluation-v1/evaluate_q2-v1.py`. No Q2 source/role changes.
- `aws/manifests/evaluation-input-m00-v1.json` pins preparation/Q2 quality reports by canonical JSON SHA256, the original annotation file by raw SHA256, and every complete case by its deterministic emitted JSON hash. The trusted builder `scripts/make_evaluation_manifest.py` verifies the saved cloud cases against the earlier independent replay. Q2 cannot read this new handoff.
- The Spark adapter reconciles **all 4,465,985 facts and labels**, unique/non-null source keys, dates/dataset/run, exact decimal(38,8) amounts, full inner-join population and independent per-format positive counts before filtering/collecting the bounded window. It refuses missing, duplicate, foreign or changed labels. Labels are then passed separately into the evaluator core.
- Frozen case IDs, namespace, source evidence, actual topology, counts and first/last times are revalidated against facts. Every transaction on each included directional pair must be present. Complete index rows and bundle hashes are checked before scoring. An explicit Parquet schema handles zero-case output without inference.

## Metrics and reference matching

1. Headline transaction population includes **all accepted facts in the declared window/cutoff**, including self transactions. Alerted transactions are the union of core source IDs across cases; overlaps count once. Case support counts retain overlap separately. TP/FP/FN/TN/precision/recall/lift compare this union with source labels. Zero alerts yield null precision; zero positives yield null recall/lift. No headline accuracy statistic is presented.
2. Parse annotation BEGIN/END blocks strictly. Attempt ID is annotation checksum plus block ordinal. Match timestamp, composite normalized bank/account endpoints, both exact amounts/currencies and payment format to all eligible facts. No annotation source ordinal is invented. Multiple matching source records, repeated annotation rows resolving to one source, missing matches or label conflicts are audited and excluded. Legitimate identical-looking transactions remain distinct.
3. Eligibility requires supported actual topology/size (fan degree >=5; simple directed 2–4-node cycle), whole attempt inside window and cutoff, and unambiguous source matching. Do not trust header “Max N” as actual shape. Unsupported types, long cycles, malformed shapes, boundary/future attempts, missing/ambiguous matches and label conflicts remain visible in an attempt audit. Exclusion counts overlap and must not be summed as disjoint groups.
4. Typed recovery requires correct pattern and hub, or the same directed cycle, and **at least 80% of annotated source transactions in one case**. Annotation edges here mean row-identifiable transaction edges, including distinct parallel payments; topology is separately deduplicated by directed bank/account pair. The comparison uses exact integer arithmetic,5×hits>=4×total. It does not pool different cases to meet typed recovery. Missed eligible attempts remain in the denominator. Unannotated cases are never labelled false from annotation absence.
5. Fair type-agnostic annotated-edge coverage is reported for both the union of detector alerts and the amount diagnostic using the same 80% criterion/eligible denominator.
6. The amount comparator ranks **amount_paid within Payment Currency**, descending amount then source ID for deterministic ties. Each currency receives exactly the detector’s distinct alert count for that currency. It uses the full eligible population, not case-only rows, and never pools currencies or uses labels to rank. This is an **evaluation-only matched-volume diagnostic**, not a trained/calibrated deployment threshold. The current evaluator explicitly refuses the 9–16 September holdout until a separately frozen development calibration policy exists.

## Local verification

The complete original 30 regression tests and initial 16 evaluator tests passed together (46 tests). The final 19 evaluator tests then passed, including 3 added manifest/index/output checks; a final amount-format assertion passed after canonical eight-decimal formatting. Thus all 49 current tests are covered. Runtime local Spark 3.5.6/Python 3.11/Java 21; Glue cloud validation is still pending.

Tests cover overlapping cases, missed attempts retained in denominators, exact80% boundary, single-case recovery, wrong hubs/directed cycles, duplicate-looking ambiguous references, malformed/checksum-invalid blocks, full-population label reconciliation, out-of-window facts, exact money/currency separation/ties, zero denominators, immutable detector cases, unsafe holdout promotion, manifest pins, changed index fields and zero-case Parquet.

`scripts/replay_evaluation_window.py` independently checks the retained source gzip checksum and full 4,465,985/1,056 per-format population, the2.27MB annotation checksum, and the frozen cloud-case verification. It does not rerun detection. Local results are `data/evaluation-local-m00-v1/`; compact proof/hashes `aws/reviews/evaluation-local-m00-v1.json`. Artifacts use the same writer as the proposed cloud job, including fixed eight-decimal audit values and evaluation ID, so all four cloud artifact hashes should reconcile exactly after deployment. Never replace expected hashes to conceal a mismatch.

## Proposed cloud run and permissions

Account **160885259244**, region **us-east-1**, job **is459-aml-evaluation-dev**, role **AWSGlueServiceRole-is459-aml-evaluation**, policy **is459-aml-evaluation-data-access**, trust only `glue.amazonaws.com`. Exact local JSON drafts are in `aws/`.

Read only v2 facts/labels, exact annotations object, exact preparation/Q2 quality reports, this frozen Q2 index/bundles, the exact evaluator manifest and code. Write/manage only this evaluation attempt and evaluator temporary/log paths. Explicit deny on raw/Q1 data; no IAM, Catalog, Athena, EC2 or detector-write permissions. Label/reference access belongs exclusively to this evaluator role; Q2’s role remains unable to read it.

Planned uploads in bucket `is459-aml-g2team7-160885259244-us-east-1`:
- Frozen source → `scripts/evaluation/evaluate_q2-v1.py`.
- Original unmodified `Ibm_dataset_medium/HI-Medium_Patterns.txt` → `references/annotations/dataset_version=ibm-hi-medium-b1b99c68b765580f/HI-Medium_Patterns.txt` (raw SHA256392d748d8d76efc1a96f6dc29ad8dd282c815de96537f0296bb0a7fa96ec4130).
- Trusted manifest → `manifests/evaluator-inputs/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q2-dev-20220901-m00-v1/manifest.json`.

Glue 5.1,2×G.1X,15-minute timeout,0 retries, concurrency1, no optional metrics/notebooks/VPC/schedules. At the checked US$0.44/DPU-hour example,15 minutes estimate **US$0.22 compute** plus separately applicable overhead/S3/logs. Existing Glue estimate$0.243223; nominal combined compute ~$0.463223, within the unchanged US$1 prototype budget. This is not a hard account-wide billing cap. [AWS pricing](https://aws.amazon.com/glue/pricing/) checked 27 October 2026.

The browser-control tool requires confirmation at action time for a new security-sensitive access grant even under general project permission. The exact policy/role plus one bounded test must be confirmed before creating/attaching the grant. Complete local work/review staging first. No existing preparation/Q1/Q2 grant needs reapproval.

## Outputs, limits and resumption

Base `evaluation/dataset_version=<version>/run_id=<prep>/analysis_id=<q2>/evaluation_id=eval-dev-20220901-m00-v1/`: `metrics.json`, `case_evaluation.jsonl`, `attempt_evaluation.jsonl`, `alert_source_ids.json`. Quality at the same namespace under `quality/evaluation/.../report.json`. Metrics are compact; detailed evidence/IDs remain separate. Each artifact is capped 10MB; raw annotations 5MB,5000 attempts,1000 rows/attempt; candidate diagnostics list at most20 IDs while exact candidate counts determine ambiguity. Input window/cases retain Q2’s guarded50k/500 bounds. This is not unbounded evaluation.

Output prefixes must be empty. Conditional S3 writes refuse replacement; PASSED quality is written only after all artifacts succeed. Failures remain FAILED/partial and cannot reuse the attempt namespace. A valid diagnostic report with null recall is completed evaluation, not successful holdout performance. Shared release/publication logic remains unimplemented.

After approval: create/verify exact evaluator policy/role, upload/check exact code/manifest/annotations, save reviewed job, verify role/paths/arguments before one Run. Observe terminal state, stop on failure/no retry, read quality and compare all four reported artifact hashes and metrics with local reference. Keep compute terminal at handoff, update costs/checkpoint, then implement the shared release gate. Never rerun preparation/Q1/Q2 for this step.
