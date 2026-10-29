# Task: remove obsolete AML definitions, preserve the published project

- **Owner:** Kelvinpcw, with Codex
- **Branch / PR:** `agent/codex-aws-resource-cleanup`; [PR #18](https://github.com/Kelvinpcw/is459-aml-project/pull/18)
- **Updated at:** 2026-10-30 (+08:00)
- **Status:** COMPLETED
- **Evidence kind:** fresh AWS inventory, deletion and post-cleanup verification

## Scope and coordination

The user requested deletion of unused Glue jobs, Step Functions workflows and S3 buckets. The verified project profile targets the expected account and region. No open PRs were present; relevant prior handoffs attribute these AML resources to this operator. No teammate-owned airline triggers, student instances or unrelated stacks are included.

Inventory found nine AML Glue jobs, five AML workflows and one bucket. All inspected job runs/workflow executions are terminal. The main workflow references five full-data jobs. Four standalone development jobs belong to the completed pilot. Four additional workflows served one-time recovery/evaluation attempts. The sole bucket contains the current publication and its supporting data/software and must remain.

## Changes and checks

- Deleted the four standalone pilot job definitions and four recovery workflow definitions. Five full-data jobs and the main full-pipeline workflow remain.
- `full-maintained-stack.json` derives from the deployed template (exactly equal to tracked `evaluation-lineage1-stack.json` before this change), removing only recovery workflows and their outputs. All retained resource definitions remain identical. Historical templates/releases are preserved.
- Executed a CloudFormation change set containing exactly four workflow removals, with no other resource changes. Stack reached UPDATE_COMPLETE; final deployed template equals the maintained template. No grants changed.
- Preserved job configurations, execution descriptions/histories and the pre-change stack privately before deletion. The main workflow has not succeeded end to end; cleanup does not validate a rerun or correct that historical limitation.
- Verified final inventory: exactly five Glue jobs (each full configuration identical to pre-cleanup) and one workflow; the publication pointer is byte-identical. All retained stack resources equal their pre-cleanup definitions. AWS validate-template and local JSON/resource invariant/diff checks passed. No processing, query or dashboard started.
- Step Functions deletion was asynchronous: initial checks saw DELETING resources; final inventory confirms all four absent. The successful execute-change-set returned no body, interrupting the local JSON reader; the request was verified in progress rather than resubmitted. No duplicate stack execution occurred. No Spark tests were run because processing source/contracts are unchanged.

## AWS scope and cleanup

Cleanup completed in the verified project account/region. Removed only eight obsolete definitions. No S3 objects/buckets, Catalog tables, IAM roles, logs, compute or unrelated resources were deleted. No compute was started or needed stopping; pre-cleanup inspected runs/executions were terminal. The sole bucket is in use and retained. Idle definitions do not represent running compute; storage/request/log charges remain and this is not an account-wide cost audit. Detailed evidence and resource identities remain private with the operator.

## Next teammate / agent

- Next safe step: use the retained published release for viewing. For any future stack maintenance, start from full-maintained-stack.json; historical templates can recreate obsolete definitions. Do not deploy or rerun automatically.
- The original checkout has a damaged Git reference; this task was published from a clean temporary clone based on current origin/main. No original local changes or Git references were altered.
- Completed outputs and consumed attempts must not be rerun. Any future processing/deployment requires fresh scoped permission.
- GitHub sync: pushed on this branch; [PR #18](https://github.com/Kelvinpcw/is459-aml-project/pull/18) contains the plan, maintained template and final outcome. PR merge is not authorised by this cleanup request.
