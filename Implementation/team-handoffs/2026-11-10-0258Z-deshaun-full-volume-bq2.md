# Full-volume on-demand BQ2

- **Owner** Deshaun, with Codex.
- **Status** COMPLETED. The historical execution succeeded and the main daily route points to the verified full-volume workflow.
- **Scope** One historical acceptance execution with the approved five models, followed by the on-demand workflow update. [Review PR #29](https://github.com/Kelvinpcw/is459-aml-project/pull/29)

The Glue path streams the original transaction file into date-partitioned facts, runs the distributed graph rules, scores those facts and cases with the saved models, validates evidence and measures coverage against separate historical references. The acceptance release was published to its own pointer and opened in a separate TRACE preview.

The first evaluation attempt timed out. The revised evaluator downloads evidence shards in parallel and looks up payments by date partition. Step Functions resumed the same execution at Evaluate, reused the three successful upstream outputs, and finished Publish. All 111 local checks passed. The cloud readback independently reconciled the population, the five model fingerprints, evaluation totals, and selected original payment evidence in TRACE.

The deployed main definition now invokes the full-volume child for on-demand daily input. The child writes future daily releases through the current pointer. Both workflows were idle after the stack updates. The historical release and its evidence are retained. The upload rule remains disabled. Use the daily entry point for a new batch after its ready manifest is present and the operator has scoped approval. [Input and release contracts](../ml_replay/README.md#fresh-bq2-workflow)
