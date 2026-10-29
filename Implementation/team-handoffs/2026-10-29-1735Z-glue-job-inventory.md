# Session: read-only Glue job inventory

- **Owner / GitHub handle:** Kelvinpcw (session run with an OpenCode agent)
- **Branch / PR:** `agent/opencode-glue-inventory`; PR link added after creation.
- **Updated at / observation interval:** 2026-10-29T17:33Z–17:36Z (2026-10-30 01:33–01:36 +08:00)
- **Status:** COMPLETED
- **Evidence kind:** fresh AWS observations (read-only `get-jobs` / `get-job-runs`)

## Scope and coordination

- **Current user-authorised actions and budget bounds:** the user asked whether all Glue job definitions are in use. This session performed read-only inspection only: no job start, no definition change, no deletion, no S3 write, no Step Functions change. No new spending was authorised or incurred. The US$90 planning ceiling is not execution permission; the user explicitly asked that the rerun be saved to GitHub without running or deploying it now.
- **Shared resource owner / coordination confirmation:** [PR #14](https://github.com/Kelvinpcw/is459-aml-project/pull/14) (the related Step Functions check) and [PR #13](https://github.com/Kelvinpcw/is459-aml-project/pull/13) (the isolated rerun plan) were both merged before this record was published. The merged rerun plan states no cloud write had occurred and remains unexecuted. This check does not touch it. No open PR was present at the start.
- **AWS account / region verification:** `Implementation/scripts/check_aws_profile.sh IS-459-BDA` returned account `160885259244`, region `us-east-1`. The local `default` profile is a different account and was not used.
- **Affected components, logical resources and owned output namespace:** Glue job definitions and their run history only. No resource changed.
- **Code commit / immutable release context:** current publication remains unchanged. Detailed per-job run identities, timings and costs remain private with the operator.

## Actions and observed outcome

- **Actions/commands actually run:** `sts get-caller-identity` via the profile guard; Glue `get-jobs` and `get-job-runs` for every defined job.
- **Inventory:** nine Glue job definitions were observed, and **none was running**. Five are wired into the current full-data workflow (preparation, Q1 risk, Q2 detection, evaluator and control). Four are historical pilot/development definitions that are not referenced by the current workflow. No new rerun definitions were present at the observation time; merging the rerun plan does not deploy AWS resources.
- **Observed run history:** every observed run was terminal. The historical jobs produced earlier pilot behaviour; the current workflow jobs cover the failed, paused and successful full-run attempts described in the prior handoff.
- **Idle definitions:** a Glue job definition does not run compute by existing. Cost arises only when a run executes, plus retained logs and S3 outputs.
- **Publication pointer / consumers affected:** unchanged.
- **Contracts/source/config changed:** none.
- **Checks actually run:** the read-only AWS calls above. No local tests, job starts, Athena queries or browser checks were run.
- **Private evidence custodian:** operator Kelvinpcw holds detailed job/run identities, timings and cost records; they were not read or republished here.

## Cost and cleanup

- **Cost / basis:** no paid action was started. Glue control-plane reads are free; no material charge.
- **Active compute/jobs/queries:** no running Glue job was observed. No project Step Functions execution was started in this session.
- **Cleanup verification:** nothing was created or deleted. Historical definitions and their evidence are retained deliberately.
- **Remaining chargeable resources / uncertainty:** CloudWatch logs and S3 outputs from prior runs remain at rest and chargeable. Idle definitions are not a compute cost. No account-wide billing audit was performed.

## Handoff

- **Next safe step and responsible owner:** reuse the published release; no Glue change is needed for the current demo. The merged rerun plan remains unexecuted and needs fresh, scoped authorisation before any deployment or paid run. If the team wants a tidier account, decide which historical definitions are still needed for evidence and delete only after explicit approval and after the rerun/demo. Do not remove definitions while their run evidence is still being cited.
- **Blockers / do not repeat:** the four historical jobs are not part of the current workflow; do not start them for validation. The five current jobs should only be started through the reviewed workflow or a new isolated rerun, not directly.
- **Supersedes/follows:** follows the [Step Functions orchestration check](2026-10-29-1220Z-stepfunctions-orchestration-check.md). Complements, but does not change, the [PR #13 rerun record](2026-10-29-1215Z-kelvin-fresh-full-rerun.md).
- **GitHub sync:** pushed on the task branch; PR opened for review.

<!-- Sanitised summary only. Raw operational checkpoints, per-run identities, timings and billing records remain private. -->
