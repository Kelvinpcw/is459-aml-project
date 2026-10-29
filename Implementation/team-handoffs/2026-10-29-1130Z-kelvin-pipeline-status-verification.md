# Session: read-only pipeline completion verification

- **Owner / GitHub handle:** Kelvinpcw (session run with an OpenCode agent)
- **Branch / PR:** `agent/opencode-pipeline-verification`; PR link added in a follow-up commit.
- **Updated at / observation interval:** 2026-10-29T11:20Z–11:35Z (19:20–19:35 +08:00).
- **Status:** COMPLETED
- **Evidence kind:** fresh AWS observations (read-only control-plane calls and S3 reads)

## Scope and coordination

- **Current user-authorised actions and budget bounds:** the user asked how much of the big-data pipeline (ingestion → visualisation) is complete and whether it can be verified on AWS. This session performed read-only inspection of existing project resources only: no S3 writes, no Athena query execution, no Glue job start, no Step Functions start, no EC2 start, no IAM change, no publication change and no deletion. No new spending was authorised or incurred; the existing US$30 historical ceiling is not extended or re-authorised.
- **Shared resource owner / coordination confirmation:** no open GitHub PRs at start. `main` was at `b3daca3`; remote branches `agent/pipeline-completion` and `agent/batch-runtime-requirement` had no commits ahead of `main` and no handoffs. This was a read-only account check, not a shared-resource write.
- **AWS account / region verification:** `Implementation/scripts/check_aws_profile.sh IS-459-BDA` returned account `160885259244`, region `us-east-1` at 2026-10-29T11:26Z. The local `default` profile resolves to a different account (`372014757586`) and was not used for any project call.
- **Affected components, logical resources and owned output namespace:** preparation, Q1, distributed Q2, evaluator, publication pointer, Step Functions orchestration and the temporary dashboard. No resource was changed.
- **Code commit / immutable release:** current publication is release `full-20261028-v1` (manifest created 2026-10-28T10:09:50Z). The deployed CloudFormation stack `is459-aml-full-v1` uses `CodeVersion=full-v1`. Frozen software packages `full-v5` (evaluator corrections) and `dashboard-v1` are present in S3. Repository `main` is `b3daca3`.
- **Dataset / run / analysis IDs and time window:** `dataset_version=ibm-hi-medium-b1b99c68b765580f`, `run_id=full-20261028-v1`; Q1 `q1-full-v1`; Q2 `q2-full-v2`; evaluation `eval-full-v2` (attempt `evaluation-lineage1`). Event dates 2022-09-01 to 2022-09-28; Q2 snapshot cutoff 2022-09-29T00:00:00; evaluation holdout `[2022-09-09T00:00:00, 2022-09-17T00:00:00)`.

## Actions and observed outcome

Read-only call types actually run: `sts get-caller-identity`; `aws configure get`; S3 `list-buckets`, `ls`, `cp` (manifest, current pointer, quality reports and evaluation metrics only); Glue `get-jobs`, `get-job-runs`, `get-tables`, `get-partitions`; Step Functions `list-state-machines`, `list-executions`, `describe-execution`; CloudFormation `list-stacks`, `describe-stacks`, `describe-stack-resources`; EC2 `describe-instances`; SSM `describe-instance-information`; Athena `list-work-groups`, `list-query-executions`, `get-query-execution`; CloudWatch Logs `describe-log-groups`. No query text was executed and no raw transaction data was downloaded.

- **Publication integrity:** `published/current.json` names `full-20261028-v1` and records SHA256 `666e126421cd09dde73bc48da04a0d9f380f1759d26a9197de43c27d08c5176e`. The downloaded manifest bytes hash to exactly that value; the compare-and-swap pointer and manifest agree.
- **Quality gates:** the preparation, Q1, Q2 and evaluation quality reports under the release all report `PASSED`.
- **Preparation:** 31,898,238 input transactions accepted (0 quarantined); 35,230 labelled laundering transactions; raw input is 759.6 MiB gzipped transactions plus 42.6 MiB accounts; curated output is 3.0 GiB over 28 date partitions.
- **Q1:** 28 daily-count partitions (2022-09-01 to 2022-09-28); totals reconcile to the prepared population and labels; report `PASSED`.
- **Q2:** 28 daily snapshot partitions; manifest sums 2,251,155 case instances and 81,321,105 evidence rows including case overlap. No snapshot is marked truncated; the first snapshot correctly reports incomplete history, and cycle exclusions above the degree threshold are declared per snapshot.
- **Evaluation:** holdout population 15,025,129 transactions with 17,632 positive labels. Detector precision 0.1973%, recall 65.94%, lift 1.68. The matched-volume amount baseline reports precision 0.2418%, recall 80.80%, lift 2.06. Typed eligible-attempt recovery is 122/122 (100%) versus 91.80% amount-baseline coverage, a gain of 8.20 percentage points, so the frozen improvement target is met. This is a low-precision, high-volume alert set, not proof that individual alerts are laundering.
- **Orchestration history:** `is459-aml-full-pipeline` FAILED on 2026-10-28T04:00 SGT; `is459-aml-full-recovery1` ABORTED; `is459-aml-evaluation-resume1` ABORTED; `is459-aml-evaluation-keyed1` FAILED; `is459-aml-evaluation-lineage1` SUCCEEDED at 2026-10-28T18:11:49 SGT. The `is459-aml-full-v1` stack is `UPDATE_COMPLETE`.
- **Visualisation:** `published/software/dashboard-v1/dashboard.zip` is present (14,886 bytes, 2026-10-28T18:17:50 SGT). The temporary CloudFormation stack `is459-aml-dashboard-v1` is `DELETE_COMPLETE`. There are no running or pending EC2 instances and no SSM-managed instances. The `is459-aml-dashboard` Athena workgroup is idle with recent successful queries, consistent with the bounded local preview recorded in the 29 October dashboard handoff.
- **Current live state:** three stopped EC2 instances remain (`is459-jingkai-tailin`, `IS459-Week1`, `is459-kelvin-joanne`), all t2/t3.micro student instances, not the dashboard. All inspected Glue runs are terminal, the inspected Athena executions are terminal, and no Step Functions execution is running.
- **Publication pointer / consumers affected:** unchanged; `full-20261028-v1` remains current.
- **Contracts/source/config changed:** none in this session.
- **Checks actually run:** read-only AWS calls above. The local test suite, Spark jobs, browser UI and latency measurements were not run.
- **Private evidence custodian:** operator Kelvinpcw holds the private checkpoint and detailed cost records. This checkout has no `Implementation/data/` directory, so those private records were not read or republished.

## Cost and cleanup

- **Cost / basis:** no paid action was started in this session; only free control-plane calls and small S3 LIST/GET requests. Historical Glue compute is estimated, not measured: summing observed run seconds × configured workers gives about US$8.0 for the full-v1 attempts, plus about US$0.28 for the earlier pilot, at the previously checked US$0.44/DPU-hour. This excludes S3, Athena, logs, dashboard EC2 and failed-attempt billing minimums. The stack's worst-case configured estimate was US$14.19; actual invoiced cost is unknown.
- **Active compute/jobs/queries:** at 2026-10-29T11:30Z, no running Glue job, running Athena query, active Step Functions execution or running EC2 instance was observed among project resources.
- **Cleanup verification:** the dashboard stack and its instance were already deleted; no SSM-managed instance remains. Published S3 data, Glue Catalog tables, job definitions, state machines, workgroups and log groups are retained deliberately for reproducibility.
- **Remaining chargeable resources / uncertainty:** S3 storage (raw, curated, gold, evidence shards, logs), CloudWatch log storage and Catalog metadata remain chargeable at rest. Stopped student EC2 instances may retain EBS volumes outside the dashboard scope. This was a scoped project check, not an account-wide billing audit.

## Handoff

- **Next safe step and responsible owner:** reuse the published release and its outputs; do not rerun preparation, Q1, Q2 or evaluation. If a live visual demo is required, the operator can either run the local pinned dashboard against the published release (normal Athena/S3 read charges) or deploy the temporary private dashboard stack under a fresh, explicit approval. A separate decision is needed for scheduled/incremental ingestion; it is not implemented.
- **Blockers / do not repeat:** there is no continuously hosted dashboard right now. UI latency targets (10 s initial / 3 s cached) and formal user-acceptance scenarios were not re-measured in this session. The detector precision (0.197%) should be reported as a substantive limitation. Consumed run approvals must not be reused.
- **Supersedes/follows:** follows the [29 October connected-dashboard handoff](2026-10-29-trace-connected-dashboard.md), which covers the local UI preview. This record adds the first shared, sanitised observation of the full-data cloud release and its current compute state.
- **GitHub sync:** branch and this record pushed in this session; the PR link is added in a follow-up commit.

<!-- Sanitised summary only. Raw operational checkpoints, query logs, screenshots and billing records remain private. -->
