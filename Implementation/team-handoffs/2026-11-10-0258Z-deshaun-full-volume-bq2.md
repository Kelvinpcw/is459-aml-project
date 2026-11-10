# Full-volume on-demand BQ2

- **Owner** Deshaun, with Codex.
- **Status** PLANNED. The full-file acceptance run is pending.
- **Scope** One isolated historical full-volume run with the approved five models. The main workflow changes target only after the acceptance checks pass.

The new Glue path streams the original transaction file into date-partitioned facts, runs the distributed graph rules, scores those facts and cases with the saved models, validates evidence and measures coverage against separate historical references. It publishes to a separate acceptance pointer that TRACE can read. The existing daily pointer keeps its latest cutoff during the backfill.

Acceptance requires one successful Step Functions execution from the original full file through every stage. Independently check the population reconciliation, all five model fingerprints, evaluation and ranked evidence in TRACE. The main update changes only the daily child target and its execution permissions and wait time. Scheduling is outside this attempt.

No new Glue compute has started. The isolated stack, fresh output namespace and private run review govern the first execution. [Input and release contracts](../ml_replay/README.md#fresh-bq2-workflow)
