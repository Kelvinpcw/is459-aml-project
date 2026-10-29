# Task: remove obsolete AML definitions, preserve the published project

- **Owner:** Kelvinpcw, with Codex
- **Branch / PR:** `agent/codex-aws-resource-cleanup`; [PR #18](https://github.com/Kelvinpcw/is459-aml-project/pull/18)
- **Updated at:** 2026-10-30 (+08:00)
- **Status:** IN_PROGRESS
- **Evidence kind:** fresh AWS inventory and cleanup plan

## Scope and coordination

The user requested deletion of unused Glue jobs, Step Functions workflows and S3 buckets. The verified project profile targets the expected account and region. No open PRs were present; relevant prior handoffs attribute these AML resources to this operator. No teammate-owned airline triggers, student instances or unrelated stacks are included.

Inventory found nine AML Glue jobs, five AML workflows and one bucket. All inspected job runs/workflow executions are terminal. The main workflow references five full-data jobs. Four standalone development jobs belong to the completed pilot. Four additional workflows served one-time recovery/evaluation attempts. The sole bucket contains the current publication and its supporting data/software and must remain.

## Changes and checks

- Planned: remove the four standalone pilot job definitions and four recovery workflow definitions; retain five full-data jobs and the main full-pipeline workflow.
- `full-maintained-stack.json` derives from the deployed template (exactly equal to tracked `evaluation-lineage1-stack.json` before this change), removing only recovery workflows and their outputs. All retained resource definitions remain identical. Historical templates/releases are preserved.
- Apply workflow removal through CloudFormation, after checking the change set contains only those four removals. Do not directly delete managed resources or change grants.
- Preserve job configurations, execution histories and the pre-change stack privately before deletion. The main workflow has not succeeded end to end; cleanup does not validate a rerun or correct that historical limitation.
- Verify deleted definitions are absent, retained definitions are unchanged, and the publication pointer remains unchanged. No processing, query, dashboard or other service is to be started.

## AWS scope and cleanup

Read-only inventory completed. No AWS mutation yet. Only obsolete definitions are candidates; no S3 objects/buckets, Catalog tables, IAM roles, logs, compute or unrelated resources are to be deleted. Idle definitions do not represent running compute. Storage remains chargeable; this is not an account-wide cost audit.

## Next teammate / agent

- Next safe step: publish this plan, mark IN_PROGRESS, archive history privately, inspect and execute the deletion-only change set, remove terminal standalone pilot definitions, then verify and publish the outcome.
- Completed outputs and consumed attempts must not be rerun. Any future processing/deployment requires fresh scoped permission.
- GitHub sync: plan pushed; draft PR #18 opened.
