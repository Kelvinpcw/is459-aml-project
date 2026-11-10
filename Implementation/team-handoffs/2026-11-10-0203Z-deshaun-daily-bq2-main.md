# Integrate on-demand daily BQ2 into the main workflow

- **Owner** Deshaun, with Codex.
- **Status** IN_PROGRESS. Approved to update the main route and verify one bounded manual AWS execution.
- **Scope** Add the tested daily route and scoped execution permissions to the main stack. Use a fresh synthetic day, the existing five-model child workflow, the separate BQ2 test pointer, and a TRACE preview.

The main route resolves a supplied batch date to its S3 ready manifest, validates it and waits for the child workflow. Existing inputs still enter the original preparation state. The update does not create a schedule or replace any Glue jobs. The isolated mock passed in AWS, and the new cutoff, original evidence and missing-label behavior passed locally. [Mock evidence](2026-11-10-0126Z-deshaun-daily-bq2-mock.md)

Review the CloudFormation change set before applying it, then verify the live main execution and the resulting TRACE release. Detailed cloud identifiers, measurements and costs stay in the private operator record. [Coordination PR](https://github.com/Kelvinpcw/is459-aml-project/pull/29) · [AWS handoff](../AWS_HANDOFF.md)
