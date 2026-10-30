# Run the project for your task

First read [status](STATUS.md), [verify progress](VERIFY_PROGRESS.md), the newest relevant [handoffs](team-handoffs/README.md) and [open PRs](https://github.com/Kelvinpcw/is459-aml-project/pulls). Existing outputs should be reused. This page does not authorise cloud processing or deployment.

## Choose a path

| Goal | Action |
| --- | --- |
| Understand the project / practise Q&A | [Walkthrough](../PIPELINE_WALKTHROUGH.md) → [Q&A](../Q_AND_A.md) |
| Read the formal requirements | [Proposal](../Proposal/Project_Proposal.md) → [pipeline explanation](../Proposal/Architecture/Pipeline_Explanation.md) → [source map](../README.md#where-files-belong) |
| View the offline TRACE concept | Open [Visulization/index.html](../Visulization/index.html); invented fixtures, no AWS |
| View the connected TRACE dashboard | Follow the local dashboard steps below; existing published results and authorised read access required |
| Change/test processing code | [Python/Spark setup](SETUP.md#2-local-pythonspark-environment); synthetic tests first |
| Check whether existing processing completed | [Verify progress](VERIFY_PROGRESS.md); no automatic reruns |
| Deploy/process/recover/clean up | Coordinate the owner and explicit scope first; [AWS handoff](AWS_HANDOFF.md) and [teardown](TEARDOWN.md) |

## Connected dashboard on your laptop

Use your own authorised project profile. [Setup](SETUP.md#visualization-without-restarting-cloud-compute) has dependencies and [onboarding](../TEAM_START_HERE.md#4-aws-login--only-for-an-approved-activity) has sign-in routes. From the intended source checkout:

```bash
bash Implementation/scripts/start_local_dashboard.sh YOUR_PROJECT_PROFILE
```

Replace the placeholder. Open `http://127.0.0.1:8501/`. The launcher checks account/region, binds only to localhost and selects the bounded dashboard workgroup. The app verifies the publication and pins all reads to that release. It starts no processing or EC2, but normal Athena/S3 read charges apply. Ctrl+C stops this local server; it does not clean up cloud resources from a different session.

The app offers Monitoring overview, Connected cases, Evaluation & coverage and Release & provenance. Monitoring uses rolling/custom dates anchored to the latest published date, with the same population filters for counts/rates/baselines. Low-volume warnings don't imply incomplete ingestion. Case displays are bounded; downloads preserve complete evidence. Evaluation is separate from label-free discovery.

Source edits/merges do not restart an existing server; restart it from the intended checkout to load the new version. If port 8501 already belongs to another process, identify its owner/version first. Don't kill an unrelated service or launch repeated cloud demos to fix a local port problem.

## Local checks

Install only your task's dependencies from [SETUP.md](SETUP.md). Offline prototype checks are in its own [README](../Visulization/README.md). Example focused dashboard checks, using the dashboard environment:

```bash
PYTHONPATH=Implementation:Implementation/tests .venv-dashboard/bin/python -m unittest test_dashboard_trends test_dashboard_navigation test_dashboard_presentation test_dashboard_app test_release_dashboard -q
```

This command is a Unix-shell example. Windows users should have their agent adapt interpreter paths and environment-variable syntax. Synthetic checks do not require AWS credentials or the original dataset.

## Full ingestion-to-EC2 operation

The [end-to-end guide](END_TO_END_GUIDE.md) explains source ingestion, each Glue
stage, Step Functions, publication, EC2/SSM access, exact phased commands and
authorised cleanup. Check its linked session handoff for the actual run outcome.
A fresh approval/run namespace is required; never reuse consumed start markers.

## Advanced deployment and recovery reference

The [archived deployment runbook](archive/2026-10-28-deployment-runbook.md) preserves the earlier full-run/recovery/package commands and their historical context. It is **not** the current task list, a live account inventory or fresh run approval. Preserve frozen packages, inspect completed outputs first and agree exact new code/output identities before any authorised change. Do not run its old start/retry/delete commands as onboarding.

Use the [demo guide](DEMO_GUIDE.md) to explain results and [teardown](TEARDOWN.md) to close an authorised session. Update/push the [shared handoff](AWS_HANDOFF.md); keep detailed operational evidence private.
