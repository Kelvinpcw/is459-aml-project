# Retire isolated BQ2 test infrastructure

- **Owner** Deshaun, with Codex.
- **Status** COMPLETED.
- **Review** [PR #35](https://github.com/Kelvinpcw/is459-aml-project/pull/35).

Deshaun approved retiring three isolated CloudFormation stacks. Live definitions showed that the daily mock depended on the smoke child, while the main workflow used the production child. Both test triggers were disabled and the workflows and six Glue jobs were idle. CloudFormation reached `DELETE_COMPLETE` for the daily mock, smoke child and historical replay stacks, in that order. Readback confirmed that all six test job definitions, both test workflows and both test triggers were removed. No processing was started or stopped.

The main and production child workflow definitions and all ten production Glue jobs matched their pre-cleanup state. Both published release pointers and the saved production model objects in S3 also matched. Public TRACE passed its health check and opened Q1 Monitoring, Q2 Published rules, the ML shortlist and the same published ML evaluation. No S3 objects were deleted. The earlier [daily mock](2026-11-10-0126Z-deshaun-daily-bq2-mock.md) and [historical replay](2026-11-09-1658Z-deshaun-q2-ml-glue-shadow.md) remain documented for reproducibility.
