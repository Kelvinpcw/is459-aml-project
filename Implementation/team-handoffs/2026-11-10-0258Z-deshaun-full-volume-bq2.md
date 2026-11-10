# Full-volume on-demand BQ2

- **Owner** Deshaun, with Codex.
- **Status** IN_PROGRESS. Preparation, distributed detection and five-model scoring passed on the full file. Evaluation reached its job timeout before writing an evaluation or publication.
- **Scope** One isolated historical full-volume run with the approved five models. The main workflow changes target only after the acceptance checks pass.

The new Glue path streams the original transaction file into date-partitioned facts, runs the distributed graph rules, scores those facts and cases with the saved models, validates evidence and measures coverage against separate historical references. It publishes to a separate acceptance pointer that TRACE can read. The existing daily pointer keeps its latest cutoff during the backfill.

Acceptance requires one successful Step Functions execution from the original full file through every stage. Independently check the population reconciliation, all five model fingerprints, evaluation and ranked evidence in TRACE. The main update changes only the daily child target and its execution permissions and wait time. Scheduling is outside this attempt.

Evaluation now downloads the needed evidence shards in parallel and looks up payments by their prepared date partition. The recovery uses Step Functions redrive at Evaluate with the existing successful outputs. The daily route remains gated on verification. [Input and release contracts](../ml_replay/README.md#fresh-bq2-workflow)
