# Historical Q2 ML replay

This is the source handoff for the ML replay of the October 30 rules release. The batch covers the archived HI-Medium transactions from September 1 through 28, 2022. The archive measures coverage of eligible IBM annotations in searchable cases. The daily queue experiment measures what an investigator can reach under a review limit. [Findings and comparison](../team-handoffs/2026-11-09-1619Z-deshaun-q2-full-month-ml-replay.md)

| Stage | Source | Where it ran |
| --- | --- | --- |
| Clean payments and detect graph patterns | Existing preparation and distributed Q2 jobs | AWS, before the ML replay |
| Rebuild the clean fact projection | [Glue entry point](glue/glue_shadow.py) and [fact projection](glue/project_facts.py) | AWS Glue, using the original label-free facts and a locally prepared case projection |
| Generate payment features | [Graph context](experiments/trace-ml-experiment/features.cpp), [account history](experiments/trace-q2-triage/history.cpp), and [transfer features](experiments/trace-kaggle-transfer/features.cpp) | AWS Glue, running the uploaded native extractors |
| Score payments and rank cases | [Payment scoring](glue/score_payments.py), [shortlist](glue/rank_shortlist.py), and [archive algorithms](glue/archive_algorithms.py) | AWS Glue, loading five locally fitted estimators and writing the ranked cases and payment alerts |
| Verify and evaluate | [Source verification](local/verify_source.py) and [independent evaluator](local/evaluate_preview.py) | Local, using the saved AWS outputs, the original labels, and the IBM annotations |
| Prepare and display the historical release | [Overlay builder](local/prepare_trace_overlay.py) and [TRACE loader](../dashboard/ml_replay.py) | The overlay was prepared locally, uploaded to S3, and pinned in TRACE on EC2 |

The [editable architecture](../../Proposal/Architecture/Simplified/ML_Replay_Architecture.drawio) shows how this path fits into the existing shared pipeline. Use commit `d53c2ca` for the exact historical Glue and native sources when reproducing the frozen scores. The experiment source resolves private local input locations through the workspace described below. [AWS validation and release handoff](../team-handoffs/2026-11-09-1658Z-deshaun-q2-ml-glue-shadow.md)

## Model producers

| Estimator used by Glue | Local producer | Local artifact |
| --- | --- | --- |
| Graph context | [model.py](experiments/trace-ml-experiment/model.py), command `fit` | `work/boosted_context.joblib` |
| Account history | [fit_history.py](experiments/trace-q2-triage/fit_history.py), model `history_boost` | `work/history_boost.joblib` |
| HI-Small transfer | [fit_transfer.py](experiments/trace-kaggle-transfer/fit_transfer.py), function `fit()` | `work/transfer.joblib`, staged as `hi_small.joblib` |
| Case shape | [case_rank.py](experiments/trace-q2-ml-v2/case_rank.py), command `freeze` | Pointwise estimator in `case-models.joblib`, staged as `case-shape.joblib` |
| Evidence progress | [case_backlog.py](experiments/trace-q2-ml-v2/case_backlog.py), command `freeze` | `progress-model.joblib`, staged as `evidence-progress.joblib` |

The fitting and evaluation code use labels offline. The Glue job uses label-free facts, case evidence, and frozen models. A repeatable AWS training job, managed evaluator, and automatic release promotion remain future work.

## Local workspace

Copy `experiments/` to a private workspace and preserve its sibling directory names. Use Python 3.11 with the [pinned runtime dependencies](glue/glue-requirements.txt) and a C++20 compiler for the native extractors. Set `TRACE_PROJECT_ROOT` to the absolute path to this checkout and `TRACE_HI_MEDIUM_DIR` to the folder containing the original `HI-Medium_Patterns.txt`. Set `PYTHONPATH` to the checkout's `Implementation` and `Implementation/ml_replay/glue` directories.

- Put the verified rules-release mirror in `trace-local-release/mirror` and its inventory beside it at `trace-local-release/base-inventory.json`. Put the earlier download inventory and first sixteen days of Parquet in `trace-fan-out-experiment/published-files.json` and `trace-fan-out-experiment/published-parquet/`.
- [prepare.py](experiments/trace-q2-full-replay/prepare.py) and [replay.cpp](experiments/trace-q2-full-replay/replay.cpp) build the payment and case projection in `trace-q2-full-replay/work`. The model producers use the feature outputs, frozen calibration inputs, and development labels in the historical workspace. [prepare_transfer.py](experiments/trace-kaggle-transfer/prepare_transfer.py) verifies the original HI-Small CSV at `trace-kaggle-transfer/inputs/HI-Small_Trans.csv`.
- For the historical Glue package, obtain the approved input manifest, fact inventory, case projection, auxiliary metadata, model files, native executables, and frozen policy through the project owner. The entry point verifies its input manifest digest and writes four immutable files under the isolated attempt output prefix.
- Run `evaluate_preview.py EXPERIMENTS ATTEMPT OUTPUT` with the saved `source-check.json` in `ATTEMPT` and the replay manifest and two output tables in a fresh `OUTPUT` directory. It writes the measured report before checking exact parity with the local checkpoint. The AWS replay produces the verified report and fails that exact-parity check because its alert and snapshot selections differ.
- Run `prepare_trace_overlay.py LOCAL_TRACE EVALUATED_REPLAY DASHBOARD DESTINATION NAME EVALUATION_SHA` to assemble a local package and its evidence index from a reviewed report. Use a fresh destination. Deployment and pinning require a separate release action.

The private replay workspaces, model binaries, cloud manifests, operator records, and datasets are supplied separately by the project owner.

## Local scoring for a new prepared batch

The [batch scorer](glue/score_batch.py) takes a label-free detector input manifest and the matching PASSED report from `q2_snapshots.py`. Its local S3 mirror supplies the run's curated Parquet facts and case index. The scorer builds the binary projection, computes features with the available earlier payments, loads the five saved estimators and writes a ranked-case table, a unique payment-alert table, the original case evidence locators and a manifest with input and model hashes.

Supply a prepared corpus with original file checksums and record ordinals, plus consecutive seven-day detection snapshots from the first supplied history day through the final cutoff. The scorer maps each full source ID to an internal index, so two files can contain the same row number. Feature history comes from the supplied corpus.

Keep the model bundle private. Include `models/` with the five estimator files used by the Glue replay, `runtime-models.json`, `frozen-policy.json`, and `category-codes.json` with the training run's `currency_codes` and `format_codes`. Compile the following sources with C++20, using the current source revision for the dynamic input sizes.

| Source under `experiments/` | Executable under the bundle's `native/` |
| --- | --- |
| `trace-q2-full-replay/replay.cpp` | `replay` |
| `trace-ml-experiment/features.cpp` | `boosted_context` |
| `trace-q2-triage/history.cpp` | `history_boost` |
| `trace-kaggle-transfer/features.cpp` | `hi_small` |

Record the reviewed files and their SHA-256 digests as the `files` mapping in `bundle.json`, keyed by the paths relative to the bundle. Use the approved digest of that manifest to run the scorer.

```sh
PYTHONPATH=Implementation:Implementation/jobs:Implementation/ml_replay/glue \
  python3 Implementation/ml_replay/glue/score_batch.py \
  --input-manifest /path/to/detector-inputs.json \
  --detector-report /path/to/detector-report.json \
  --mirror /path/to/s3-mirror \
  --model-bundle /path/to/bundle --model-bundle-sha256 APPROVED_SHA256 \
  --release-id NEW_RELEASE_ID --destination /path/to/new-results
```

## Fresh BQ2 workflow

The [stage runner](glue/fresh_glue.py) takes a ready manifest through Prepare, Detect, Score and rank, Evaluate, and Publish. Its local runner exchanges checksummed stage files across the same boundaries as the Glue entry point. TRACE reads the published pointer and the case evidence from the same release.

Place CSVs in `fresh-bq2/incoming/` and list them in a `ready.json` with schema version 1. Supply `dataset_version` beginning with `fresh-bq2-`, the `history_start`, `batch_start` and exclusive `cutoff` as ISO dates, the transaction `files`, and the `accounts` file. Each file reference contains its `key` and `sha256`. One run scores one new day against up to 29 days of supplied context. Preparation reports rows excluded at the time boundaries. The bounded detector accepts up to 50,000 input payments and enforces its snapshot and cycle guards.

An optional `labels` reference under `fresh-bq2/reference/` contains JSON rows with `source_id` and binary `is_laundering`. Optional `annotations` there contain `annotation_id`, `pattern_type`, and `source_ids` for the known pattern. The evaluator uses those references to measure payment and pattern metrics. Every batch must pass evidence and integrity validation. Metrics without a denominator display as unavailable.

```sh
PYTHONPATH=Implementation:Implementation/jobs:Implementation/ml_replay/glue \
  python3 Implementation/ml_replay/glue/fresh_glue.py --stage local \
  --local-mirror /path/to/mirror --ready-key fresh-bq2/incoming/example/ready.json \
  --local-bundle /path/to/bundle --model-bundle-sha256 APPROVED_SHA256 \
  --attempt-id example-1

PYTHONPATH=Implementation TRACE_BQ2_LOCAL_MIRROR=/path/to/mirror \
  python3 -m streamlit run Implementation/dashboard/app.py
```

Run the [integration test](../tests/test_fresh_bq2_flow.py) with `TRACE_TEST_MODEL_BUNDLE` and `TRACE_TEST_MODEL_BUNDLE_SHA256` set to the private approved model bundle and its manifest digest. It exercises two fresh cutoffs, the actual five fitted models, case evidence from both raw files, labelled and unlabelled evaluation, duplicate delivery, and publication after validation.

The [AWS stack generator](../deployment/build_fresh_bq2_stack.py) defines one Standard Step Functions execution with five sequential Glue jobs and a disabled S3 event rule. Build the [Glue code package](../deployment/build_fresh_bq2_bundle.py) with the pinned wheels, and build the native extractors for the Glue Linux runtime before deployment. The first cloud acceptance check is a single manual execution on a fresh fixture and a TRACE readback of its published cases and source payments.
