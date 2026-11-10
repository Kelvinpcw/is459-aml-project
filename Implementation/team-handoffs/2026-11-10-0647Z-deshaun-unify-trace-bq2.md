# Use the current BQ2 release in public TRACE

- **Owner** Deshaun with Codex
- **Branch and PR** [Full-volume BQ2 rollout](https://github.com/Kelvinpcw/is459-aml-project/pull/29)
- **Status** COMPLETED
- **Evidence** AWS publication readback and live TRACE inspection

The verified full-volume release initialized the current BQ2 pointer in place of the daily smoke-test fixture. The existing public TRACE dashboard now follows that pointer. Evaluation & coverage reports complete matches, and Connected cases opens the matching ranked investigations and original payment evidence.

The release and published result checksums matched on readback. The existing dashboard service and proxy passed health checks, and the public browser showed the same evaluation and original evidence. The local verification preview is closed. Existing host permissions were reused and the historical artifacts remain available for audit. No processing job or schedule was started.

Next check is one newly uploaded batch through the current main daily route. The [submission index](../../SUBMISSION.md) records the source and private model artifacts. Submission packaging changed no AWS resources.
