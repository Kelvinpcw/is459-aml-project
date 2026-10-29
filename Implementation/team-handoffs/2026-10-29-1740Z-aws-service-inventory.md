# Session: read-only AWS service inventory

- **Owner / GitHub handle:** Kelvinpcw (session run with an OpenCode agent)
- **Branch / PR:** `agent/opencode-glue-inventory`; [PR #16](https://github.com/Kelvinpcw/is459-aml-project/pull/16).
- **Updated at / observation interval:** 2026-10-29T17:36Z–17:40Z (2026-10-30 01:36–01:40 +08:00)
- **Status:** COMPLETED
- **Evidence kind:** fresh AWS observations (read-only control-plane, configuration and inventory calls)

## Scope and coordination

- **Current user-authorised actions and budget bounds:** the user asked which AWS services the project uses and asked for verification inside AWS. This session performed read-only inspection only: no job or execution start, no deployment, no definition or IAM change, no Athena query, no S3 write and no deletion. The US$90 planning ceiling is not execution permission; the user explicitly asked that the rerun be saved to GitHub without running or deploying it now.
- **Shared resource owner / coordination confirmation:** no open PR was present at the start; PRs #13 (rerun plan) and #14 (Step Functions check) were merged. This record is a companion to the read-only Glue inventory on the same branch. Nothing was changed.
- **AWS account / region verification:** `Implementation/scripts/check_aws_profile.sh IS-459-BDA` returned account `160885259244`, region `us-east-1`. The local `default` profile is a different account and was not used.
- **Affected components, logical resources and owned output namespace:** project-scoped S3, Glue, Step Functions, Athena, CloudFormation, IAM, CloudWatch, EC2/SSM history and publication pointer. No resource changed.
- **Code commit / immutable release context:** current publication remains unchanged. Detailed resource identities, object locators, run measurements and cost records remain private with the operator.

## Actions and observed outcome

- **Actions/commands actually run:** CloudFormation list/describe; S3 bucket configuration and prefix listings; Glue jobs, databases and tables; Step Functions list; Athena workgroups; IAM roles, policies and instance profiles; EC2 instances, volumes, addresses, NAT gateways, VPC endpoints and snapshots; SSM managed instances; CloudWatch log groups, alarms and dashboards; EventBridge rules, Scheduler, Lambda, SNS and Budgets. All calls were read-only.
- **Services currently carrying project resources:** S3 (one private project bucket), Glue (jobs plus Data Catalog databases/tables), Step Functions (five Standard machines), Athena (two project workgroups), CloudFormation (the full-data stack), IAM (project roles and policies) and CloudWatch Logs (project log groups). The current full-data stack contains six IAM roles, five Glue jobs, one Glue database, five state machines and one Athena workgroup.
- **S3 configuration observed:** one project bucket, SSE-S3 encryption, all four public-access blocks enabled, no bucket policy, no versioning and no lifecycle configuration. Retained zones include raw, curated, references, gold, evaluation, quality, manifests, scripts, published and query-results.
- **Historical services:** EC2 and Systems Manager were used for the temporary dashboard. The dashboard CloudFormation stack is deleted; no project-tagged instance, volume, Elastic IP, NAT gateway, VPC endpoint, snapshot or SSM-managed node was observed.
- **Not observed in the project scope:** Lambda, SNS, EventBridge rules or Scheduler, project KMS CMK, RDS, Redshift, QuickSight, EMR, Kinesis or Neptune. This is a project-scoped inventory, not an account-wide absence claim.
- **Trial deployment found:** an isolated rerun stack was created and deleted during the observation window, and a short preparation-stage Spark run occurred. No curated or quality output and no new published release were produced; the current pointer is unchanged. An orphan log group from that trial remains, and the full-v6 script package is present in S3. This corrects any assumption that no deployment had been attempted.
- **Retention observation:** several project log groups have no retention setting, and the bucket has no lifecycle policy. These are cost-hygiene items, not current compute.
- **Publication pointer / consumers affected:** unchanged; the current release remains readable.
- **Contracts/source/config changed:** none.
- **Checks actually run:** the read-only AWS calls above. No local tests, Glue starts, Athena queries or browser checks were run.
- **Private evidence custodian:** operator Kelvinpcw holds detailed resource identities, object sizes, timings and cost records; they were not read or republished here.

## Cost and cleanup

- **Cost / basis:** no paid action was started in this session. A short historical preparation-stage Glue run from the trial stack occurred before this record; exact cost was not assessed. The account has a generic budget, not a project-specific one.
- **Active compute/jobs/queries:** no running Glue job, Step Functions execution, EC2 instance or SSM-managed node was observed.
- **Cleanup verification:** nothing was created or deleted. The trial stack was already deleted; its orphan log group remains. Published S3 data, job/workflow definitions, catalog metadata and project logs are retained deliberately.
- **Remaining chargeable resources / uncertainty:** S3 storage, CloudWatch log storage and Catalog metadata remain at rest and chargeable. Log retention is inconsistent and the bucket has no lifecycle policy. No account-wide billing audit was performed.

## Handoff

- **Next safe step and responsible owner:** review the retention/orphan-log findings and decide whether any cleanup is worth doing after the report/demo. The merged rerun plan remains unexecuted and needs fresh, scoped authorisation before any deployment or paid run. Do not start historical jobs or the old workflow.
- **Blockers / do not repeat:** the trial stack is gone and must not be recreated merely to inspect it. The current release is complete; reuse it. The rerun plan being merged does not mean it was run.
- **Supersedes/follows:** follows the [Glue job inventory](2026-10-29-1735Z-glue-job-inventory.md) and the [Step Functions orchestration check](2026-10-29-1220Z-stepfunctions-orchestration-check.md). Corrects the assumption that no deployment had been attempted around the earlier Step Functions check.
- **GitHub sync:** pushed on the task branch; PR updated for review.

<!-- Sanitised summary only. Raw operational checkpoints, resource identities, object locators, timings and billing records remain private. -->
