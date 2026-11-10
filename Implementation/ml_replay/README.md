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
| Case shape | [case_rank.py](experiments/trace-q2-ml-v2/case_rank.py), command `freeze` | `case-models.joblib`, staged as `case-shape.joblib`. Glue selects its pointwise estimator. |
| Evidence progress | [case_backlog.py](experiments/trace-q2-ml-v2/case_backlog.py), command `freeze` | `progress-model.joblib`, staged as `evidence-progress.joblib` |

### Training steps and fitted parameters

1. **Prepare local features and targets.** Use the checksummed HI-Medium facts and graph evidence to build payment and case features. Join IBM labels and annotations to build training targets. The graph model uses context available at the daily cutoff. The account-history model uses events strictly before the payment minute. Prepare HI-Small separately with its own features and labels.
2. **Fit the two HI-Medium payment models.** Train on September 1–5, 2022, using all 7,172 IBM-positive payments and 600,000 sampled IBM-zero payments per model. Use seed 459 for sampling and weights of 3 for positives and 1 for negatives. Compare payment models on September 6–8. The graph experiment compares a logistic baseline, payment-only boosting, and boosting with graph context using average precision.
3. **Fit the HI-Small transfer model.** Split HI-Small chronologically into approximately 60% training, 20% validation, and 20% test, keeping same-minute payments together at the boundaries. Use balanced class weights. Fit on HI-Small, calibrate its experiment thresholds on the validation block, and apply the saved estimator to HI-Medium features for supporting payment scores.
4. **Fit the case models.** Use HI-Medium development snapshots from September 1–6 and validate on September 7–8. Case shape learns from snapshots matched to annotated patterns and clean controls. Evidence progress treats matches with at least 80% of the annotated evidence as positive training examples. Partial matches and cases with no IBM-positive evidence provide controls. Both use training weights that reduce the influence of repeated positive snapshots of the same topology.
5. **Save and package the selected estimators.** Use the fitting entry points listed above, then bundle their fitted files, feature encodings, extractors, and ranking policy. Glue verifies the bundle hashes and reuses the saved parameters for each batch.

All five estimators used by Glue are scikit-learn 1.7.1 histogram gradient boosting classifiers. These are the settings in the approved fitted bundle.

| Estimator | Learning rate | Iteration cap / fitted | Max leaves | Max depth | Min samples per leaf | L2 | Seed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Graph context | 0.09 | 115 / 115 | 31 | 6 | 35 | 1.5 | 459 |
| Account history | 0.075 | 150 / 150 | 31 | 7 | 30 | 1.5 | 459 |
| HI-Small transfer | 0.10 | 300 / 52 | 31 | Unbounded | 20 | 0 | 0 |
| Case shape (pointwise) | 0.065 | 85 / 85 | 12 | 4 | 12 | 4.0 | 459 |
| Evidence progress | 0.065 | 85 / 85 | 12 | 4 | 12 | 4.0 | 459 |

HI-Small used early stopping with an internal 10% validation fraction from its training block. The other four ran their full iteration caps. See the fitting scripts for the full estimator and feature definitions.

### Alert and ranking calibration

The deployed shortlist averages the graph-context and account-history scores. It uses a **0.636** standalone alert cutoff and a **0.6400573** case rejoin cutoff. The graph score selects the top **0.25%** of payments per day as seeds and the top **2%** as supporting candidates, with at least two seeds for the anchored route. The HI-Small model can suggest supporting payments at a score of **0.85** or above under the bounded case-completion rules. Each retained snapshot gets the mean of its case-shape and evidence-progress scores. An investigation ranks by its best snapshot score, with up to **9,493** investigations retained per release. [Ranking implementation](glue/rank_shortlist.py)

Model and feature comparisons used chronological development and validation blocks. The final shortlist size, ranking policy, and standalone cutoff were selected using the historical month. Report that replay as a historical result, and keep the September 9–16 holdout results from the earlier experiment separate. [Historical policy experiments](../team-handoffs/2026-11-09-1619Z-deshaun-q2-full-month-ml-replay.md) · [Earlier holdout](../team-handoffs/2026-11-09-1200Z-deshaun-q2-ml-replay.md)

Training runs locally with offline labels. The current AWS batch scores label-free facts and case evidence with the frozen models. Its separate evaluator can use verified labels and annotations before Glue publishes the release. The [approved Linux bundle manifest](model-bundle-manifest.json) records the exact file digests. Its SHA-256 is `6638cdeac221574910c01ba58f4102e22bb5d9f282922e77ff21d79ba75b8c2e`.

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

Place CSVs in `fresh-bq2/incoming/` and list them in a `ready.json` with schema version 1. Supply `dataset_version` beginning with `fresh-bq2-`, the `history_start`, `batch_start` and exclusive `cutoff` as ISO dates, the transaction `files`, and the `accounts` file. Each file reference contains its `key` and `sha256`. A daily run declares one new day. A historical run can include multiple days. The supplied period including history is at most 29 days. Preparation streams rows into date-partitioned Parquet and reports the rows excluded at the boundaries. Glue Detect runs distributed seven-day snapshots across all prepared partitions. The local graph runner is for small fixtures.

An optional `labels` reference under `fresh-bq2/reference/` contains JSON rows with `source_id` and binary `is_laundering`. For a fully labelled single-file batch, `complete_labels` can instead declare its `source_sha256`, total `rows`, and `positive_ordinals`. Optional `annotations` contain `annotation_id`, `pattern_type`, and `source_ids`. Only the evaluator reads these references. Every batch must pass evidence and integrity validation. Metrics without a denominator display as unavailable.

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

The [daily BQ2 update generator](../deployment/build_daily_bq2.py) adds a route to the main Standard state machine using its deployed CloudFormation template as input. Upload a day's files, then write `fresh-bq2/incoming/day=YYYY-MM-DD/ready.json` with `batch_start` matching that date. Start the main workflow with `{"mode":"daily-bq2","batch_date":"YYYY-MM-DD"}`. The main workflow checks the manifest date and passes its object key and ETag to the reviewed fresh BQ2 workflow. The nested execution name uses the batch date and ETag so starting the same manifest again cannot create a second execution during the Standard workflow name retention period. For a failed batch, inspect the child and use the applicable redrive or recovery procedure.

The main route update only changes the state machine and its execution role. The scale stack supports `scale-check.json` as a separate publication pointer for historical acceptance. For a local TRACE mirror of that release, set `TRACE_BQ2_POINTER` to the corresponding project S3 URI along with `TRACE_BQ2_LOCAL_MIRROR`. Daily publication uses `published/bq2/current.json` and only advances its cutoff.
