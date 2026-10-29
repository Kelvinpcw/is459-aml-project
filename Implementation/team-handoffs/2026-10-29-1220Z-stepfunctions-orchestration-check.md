# Session: read-only Step Functions orchestration check

- **Owner / GitHub handle:** Kelvinpcw (session run with an OpenCode agent)
- **Branch / PR:** `agent/opencode-stepfunctions-check`; [PR #14](https://github.com/Kelvinpcw/is459-aml-project/pull/14).
- **Updated at / observation interval:** 2026-10-29T12:16Z–12:20Z (20:16–20:20 +08:00)
- **Status:** COMPLETED
- **Evidence kind:** fresh AWS observations (read-only control-plane and one small S3 read)

## Scope and coordination

- **Current user-authorised actions and budget bounds:** the user asked what the on-demand Step Function does and whether it was actually created and executed. This session performed read-only inspection only: no Step Functions start/stop, no Glue job start, no S3 write, no Athena query, no EC2 change, no IAM or publication change, and no deletion. No new spending was authorised or incurred.
- **Shared resource owner / coordination confirmation:** [PR #13](https://github.com/Kelvinpcw/is459-aml-project/pull/13) (`feature/full-rerun-20261029`) is open and `IN_PROGRESS`, preparing an isolated full rerun; its record states no cloud write had occurred at 12:15Z. This read-only check does not touch that attempt. No other open PR was present.
- **AWS account / region verification:** `Implementation/scripts/check_aws_profile.sh IS-459-BDA` returned account `160885259244`, region `us-east-1` at 2026-10-29T12:16Z. The local `default` profile is a different account and was not used.
- **Affected components, logical resources and owned output namespace:** Step Functions state machines, Glue job history and the read-only publication pointer. No resource was changed.
- **Code commit / immutable release context:** current publication remains unchanged; repository `main` observed at `35ea1a8`.
- **Detailed identities:** detailed execution/run identities, per-stage timings and cost records remain private with the operator.

## Actions and observed outcome

- **Actions/commands actually run:** `sts get-caller-identity` via the profile guard; Step Functions `list-state-machines`, `describe-state-machine`, `list-executions`, `describe-execution`, `get-execution-history`; Glue `get-job-runs`; CloudFormation `describe-stack-resources`; S3 read of the small `published/current.json`.
- **Created:** five `STANDARD` state machines exist as resources of the prior full-run stack: one main full pipeline plus four versioned recovery/retry definitions (a Q1/Q2/Catalog recovery and three evaluator/publisher-only attempts). The main definition matches the reviewed full template; the recovery definitions deliberately contain only the stages that had not completed. Failures end the execution without replacing the previous release. The workflow has a bounded timeout, no retries and no recurring schedule.
- **Executed:** yes, the workflows really ran. Outcome categories:
  - the original full-pipeline execution **failed** in the parallel detection stage (Spark join internal error) and cancelled the Q1 branch;
  - a targeted recovery completed Q1, Q2 and Catalog, then was **deliberately aborted** for a cost pause;
  - two evaluator-only attempts were **aborted/failed**;
  - a final evaluator+publish recovery **succeeded** and produced the current published pointer.
- **Important qualification:** no single execution completed the whole chain end to end. The successful release reused completed upstream outputs and a targeted recovery machine, not a clean single-pass run of the main workflow. This should be stated accurately in reports/demos.
- **Publication pointer / consumers affected:** unchanged; the current release and manifest hash remain as previously verified.
- **Contracts/source/config changed:** none.
- **Checks actually run:** the read-only AWS calls above. No local test suite, Glue start, Athena query or browser UI check was run.
- **Private evidence custodian:** operator Kelvinpcw holds the detailed checkpoint, execution identities and cost records; they were not read or republished here.

## Cost and cleanup

- **Cost / basis:** no paid action was started. Only free control-plane calls and one small S3 GET; no material charge.
- **Active compute/jobs/queries:** at the observation time, no running Step Functions execution and no running full-detect Glue run were observed. EC2 was not re-inspected in this session; the prior handoff recorded no project dashboard instance.
- **Cleanup verification:** no resource was created or deleted in this session. The earlier temporary dashboard stack remains deleted per the prior handoff.
- **Remaining chargeable resources / uncertainty:** published S3 data, curated facts, evidence shards, CloudWatch logs and Glue Catalog metadata remain at rest and chargeable. Idle job/workflow definitions are retained for reproducibility. No account-wide billing audit was performed.

## Handoff

- **Next safe step and responsible owner:** the PR #13 owner should deploy its own isolated workflow and verify the deployed definition before starting the approved rerun. Do not restart the old terminal executions.
- **Blockers / do not repeat:** the old single-pass workflow has never completed end to end in one execution; the evaluator join failure must remain documented. PR #13 was still preparing a new attempt and had no new state machine at this observation.
- **Supersedes/follows:** follows the [11:30Z pipeline verification](2026-10-29-1130Z-kelvin-pipeline-status-verification.md), adding orchestration-definition and execution-outcome context. Complements, but does not change, the [PR #13 rerun record](2026-10-29-1215Z-kelvin-fresh-full-rerun.md).
- **GitHub sync:** pushed on the task branch; PR opened for review.

<!-- Sanitised summary only. Raw operational checkpoints, query logs, screenshots, detailed timings and billing records remain private. -->
