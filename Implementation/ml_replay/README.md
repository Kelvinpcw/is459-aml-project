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

The [editable architecture](../../Proposal/Architecture/Simplified/ML_Replay_Architecture.drawio) shows how this path fits into the existing shared pipeline. The deployed Glue entry point and its Python modules are preserved byte for byte. The experiment source resolves private local input locations through the workspace described below. [AWS validation and release handoff](../team-handoffs/2026-11-09-1658Z-deshaun-q2-ml-glue-shadow.md)

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

- Put the verified rules-release mirror and its inventory in `trace-local-release/mirror`. Put the earlier download inventory and first sixteen days of Parquet in `trace-fan-out-experiment/published-files.json` and `trace-fan-out-experiment/published-parquet/`.
- [prepare.py](experiments/trace-q2-full-replay/prepare.py) and [replay.cpp](experiments/trace-q2-full-replay/replay.cpp) build the payment and case projection in `trace-q2-full-replay/work`. The model producers use the feature outputs, frozen calibration inputs, and development labels in the historical workspace. [prepare_transfer.py](experiments/trace-kaggle-transfer/prepare_transfer.py) verifies the original HI-Small CSV at `trace-kaggle-transfer/inputs/HI-Small_Trans.csv`.
- For the historical Glue package, obtain the approved input manifest, fact inventory, case projection, auxiliary metadata, model files, native executables, and frozen policy through the project owner. The entry point verifies its input manifest digest and writes four immutable files under the isolated attempt output prefix.
- Run `evaluate_preview.py EXPERIMENTS ATTEMPT OUTPUT` with the saved `source-check.json` in `ATTEMPT` and the replay manifest and two output tables in a fresh `OUTPUT` directory. It writes the measured report before checking exact parity with the local checkpoint. The AWS replay produces the verified report and fails that exact-parity check because its alert and snapshot selections differ.
- Run `prepare_trace_overlay.py LOCAL_TRACE EVALUATED_REPLAY DASHBOARD DESTINATION NAME EVALUATION_SHA` to assemble a local package and its evidence index from a reviewed report. Use a fresh destination. Deployment and pinning require a separate release action.

The private replay workspaces, model binaries, cloud manifests, operator records, and datasets are supplied separately by the project owner.
