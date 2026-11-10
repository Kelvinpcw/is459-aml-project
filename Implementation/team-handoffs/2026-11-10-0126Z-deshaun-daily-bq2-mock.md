# Verify dated batch pickup through the BQ2 mock

- **Owner** Deshaun, with Codex.
- **Status** IN_PROGRESS. Approved for one manual AWS run through the isolated mock parent.
- **Scope** The mock reads a dated S3 ready manifest and waits for the previously verified five-stage BQ2 child workflow. The mock schedule is disabled. This run advances the fresh BQ2 test pointer and is verified in a separate TRACE preview. The shared main workflow and live TRACE are outside scope.

Step Functions TestState verified that a manual date and a simulated Scheduler timestamp select the same manifest and that a missing or mismatched manifest cannot start the child. Its S3 and child responses were mocked. The exact local handoff passed through preparation, detection, the five pinned estimators, evaluation, publication and the real TRACE app. The approved AWS run checks that the services work together with a fresh synthetic batch. [Prior child workflow verification](2026-11-09-2028Z-deshaun-fresh-bq2-aws-smoke.md)

The isolated draft stack is prepared for review. Keep exact resources, measurements, costs and output checksums private. [Coordination PR](https://github.com/Kelvinpcw/is459-aml-project/pull/29) · [AWS handoff](../AWS_HANDOFF.md)
