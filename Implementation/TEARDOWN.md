# Project cost control and final teardown

User instruction on 25 October 2026: tear down project-created services that incur substantial expenses after the project work/demo is finished. S3 data may remain. The user subsequently selected **prepare everything, but wait before paid runs** for the first prototype.

## Current operating rule

Read [VERIFY_PROGRESS.md](VERIFY_PROGRESS.md), the relevant owner's latest handoff and [AWS_HANDOFF.md](AWS_HANDOFF.md) first. This document's dated observations are historical; this repository cleanup performed no cloud inventory or teardown. Establish the currently requested resources/scope before acting. Never use an old single-run approval, saved definition or old cleanup result as fresh permission. Do not introduce recurring schedules.

Keep exact resource inventory, observed states, measurements and costs in the private operator ledger/checkpoint. Push a sanitised activity/cleanup summary in [team-handoffs](team-handoffs/README.md); the old tracked resource ledger is historical and should not receive new private records.

## After an authorized demo or processing run

1. Verify all project Glue job runs and interactive sessions have ended. A saved batch job definition does not mean a job is running. Stop stuck runs and disable project triggers/schedules.
2. If EC2 is introduced later, preserve source, configuration, results and required demo evidence in S3/local files. Stop it when temporarily idle. At final teardown, review the exact instance, EBS volumes, snapshots and public IPs; obtain any action-time confirmation required for irreversible deletion, then terminate/delete the approved project resources. Stopping alone can leave billable storage/IP resources.
3. If project NAT gateways, VPC interface endpoints, load balancers, graph databases or other continuously billed resources are introduced, record and tear them down explicitly after they are no longer needed. None are required for the first S3/Glue prototype.
4. Confirm project Athena queries have finished. Preserve needed query results in S3.
5. Apply finite retention to project log groups when they are introduced. Preserve the logs needed for assessment before any irreversible deletion.
6. Keep the approved S3 data/results/code. Retain IAM roles and saved batch definitions if useful for reproducing the project; neither means compute is running.
7. Record observed final statuses and remaining storage in the ledger. Check resource state directly; billing dashboards can lag and are not proof that compute has stopped.

Do not delete or modify unrelated resources in the shared AWS account. Do not claim the entire AWS account is free of charges based on this project's teardown.

## Historical observations — 26 October 2026

### Cleanup observed then

Both preparation runs finished Succeeded; no project compute remains active. Corrected v2 report/manifest checks passed. At the user's request, deleted only superseded v1 synthetic test outputs under curated, references/labels, quarantine/preparation and quality/preparation: 35 objects, approximately 414 MB, zero failures. Retained raw inputs, scripts, all v2 output, local v1 review evidence and small static CloudWatch logs. See `aws/reviews/v1-output-cleanup-results.json`. No log retention setting changed.

### Pause observed then

Q1 also finished Succeeded at 16:29:25 Singapore. All three approved Glue runs are terminal. No Athena queries were started. Retain idle Athena workgroup is459-aml-dev (engine 3, enforced private SSE-S3 results, 50 MB/query scan limit), Q1 role/policy/job, raw/prepared/Q1 S3 data and static logs. No ongoing project compute to stop. User requested checkpoint/pause; wait for resume.

### Athena validation observed then

Three metadata statements and three data validations succeeded; one initial ordering check failed before scanning and was corrected. All seven SQL executions are terminal; no query or other project compute is active. Retain idle workgroup/Catalog table/partition and S3 query results. No Glue rerun, new role grant, crawler or continuously billed service was introduced.
