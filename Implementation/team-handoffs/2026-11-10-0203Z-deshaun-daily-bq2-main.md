# Verified on-demand Daily BQ2 from the main workflow

- **Owner** Deshaun, with Codex.
- **Status** COMPLETED. The main workflow now supports an on-demand Daily BQ2 run.
- **Scope** The existing main state machine and its scoped execution role, one synthetic AWS batch, the fresh BQ2 release and a TRACE preview.

The main workflow accepts a batch date, reads and validates its dated S3 ready manifest, and waits for the existing child workflow. The reviewed change set updated only the main state machine and its role in place. TestState verified that existing input still enters the original preparation state. [Route and input contract](../ml_replay/README.md#fresh-bq2-workflow)

One manual main execution and all five child Glue stages succeeded. The batch cutoff excluded the out-of-window row. The published output matched the local fixture and all five approved model fingerprints. TRACE showed the ranked case, original payments, dated alerts and evaluation coverage. The historical release pointer and child definition matched their previous versions. The mock schedule remained disabled. [Mock evidence](2026-11-10-0126Z-deshaun-daily-bq2-mock.md)

The main route remains active and no compute from this test is running. The private operator record retains exact execution and resource IDs, cost and output checksums. [Review PR](https://github.com/Kelvinpcw/is459-aml-project/pull/29) · [AWS handoff](../AWS_HANDOFF.md)
