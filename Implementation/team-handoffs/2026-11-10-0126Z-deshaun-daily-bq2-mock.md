# Verified dated batch pickup through the BQ2 mock

- **Owner** Deshaun, with Codex.
- **Status** COMPLETED. One manual AWS execution succeeded through the isolated mock parent.
- **Scope** Dated synthetic S3 input, the previously verified five-stage BQ2 child workflow, the separate BQ2 test release and a TRACE preview.

Step Functions TestState verified that a manual date and a simulated Scheduler timestamp select the same manifest. Missing and mismatched manifests stopped before the child. In the live AWS test, the mock read the dated S3 object and passed its exact key and ETag to the child. The child completed preparation, detection, scoring with all five pinned estimators, evaluation and publication. The checksummed AWS output matched the local fixture, and the real TRACE app displayed the ranked case, source payments, dated alerts and evaluation coverage. [Prior child workflow verification](2026-11-09-2028Z-deshaun-fresh-bq2-aws-smoke.md)

Both executions and all five Glue jobs succeeded and are terminal. The isolated definitions and immutable results remain. The mock schedule was verified disabled, and the main workflow definition matched its original version. A live schedule invocation and integration into the shared main workflow require their own review. The private operator record retains exact resources, measurements, costs and output checksums. [Coordination PR](https://github.com/Kelvinpcw/is459-aml-project/pull/29) · [AWS handoff](../AWS_HANDOFF.md)
