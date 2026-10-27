# Project checkpoint — full validation in progress

Updated 28 October 2026, Singapore. Continue the user's **whole-project completion** request on `codex/project-completion`. The latest ceiling is **US$30 total**, replacing US$80. Exact new roles/deployments were explicitly approved: **“Approve these exact roles and deployment.”** Do not ask again for the unchanged approved templates. Earlier prototype-only approvals/paused states are historical; [archived checkpoints](Implementation/aws/reviews/checkpoint-history-before-full-validation-20261028.md) preserve them.

## Original execution — failed, do not start again

- Account **160885259244**, region **us-east-1**, explicitly selected profile **IS-459-BDA**. The local default belongs to **372014757586** and is prohibited. Verify using `bash Implementation/scripts/check_aws_profile.sh IS-459-BDA` before cloud actions.
- Stack **is459-aml-full-v1** is CREATE_COMPLETE; exact role trusts/policies, five job definitions, frozen input/code and workgroup limits were verified before starting. [Verification](Implementation/aws/reviews/full-deployment-verification.json).
- Execution **arn:aws:states:us-east-1:160885259244:execution:is459-aml-full-pipeline:full-20261028-v1**, started **03:34:07 Singapore, 28 October**. It is FAILED. Start request/response are `Implementation/aws/reviews/full-workflow-request.json` and `full-workflow-start.json`. **Do not run the start phase again.**
- Full preparation SUCCEEDED: **31,898,238 accepted transactions, 35,230 positive labels**, zero quarantine and zero unmatched account joins. Execution 1,100 seconds, five G.1X workers. [Quality report](Implementation/aws/reviews/full-preparation-report.json).
- Sanitised-manifest control SUCCEEDED. Q2 failed at its export metadata join (Spark conflicting case_id references) after writing one snapshot's normalised Parquet; Q1 was cancelled by the failed parallel branch. All original full compute is terminal. Original full compute estimate US$1.052334. No evaluator/Catalog/full publication occurred.
- Use `Implementation/aws/reviews/full-monitor-latest.json` for latest observations. Run `/private/tmp/is459-spark-validation/bin/python Implementation/deployment/monitor.py --profile IS-459-BDA --enforce-budget` to inspect and enforce the reserve guard. This is an on-demand check, not a background scheduler.

## Recovery prepared — not started yet

Read [targeted recovery review](Implementation/aws/reviews/full-recovery1-review-20261028.md). New frozen **full-v2** fixes the export join and uses bounded schema3 ZIP shards to reduce storage PUTs. It preserves complete evidence. AST comparisons prove detection/aggregation/schedule unchanged; evaluator files are byte-identical. **68 tests PASSED47.870s**, both recovery templates pass cfn-lint. Manifest source SHA **03318a47e61487243680591a3a1b2f44b57307b2823803d815237eb637d2fb42**.

New immutable objects map to `scripts/full-v1/recovery1/` and `published/software/full-v2/dashboard.zip` under already approved grants. All six pipeline IAM resources and dashboard IAM resources are unchanged. Recovery uses original preparation/run, fresh Q1/Q2 `attempt=recovery1/`, starts at parallel branches, then Catalog/evaluate/publish. Review and driver: `Implementation/deployment/recover.py` phases upload/update/status/start. Do not run original start again. Remaining conservative total including reserves about **US$24.73**. Next: commit tested payload, upload, update/verify idle definitions, then start the once-only recovery within existing user authorisation. Verify actual fresh state before continuing.

## Immutable identities and cost limits

Original CodeVersion **full-v1**, RunId/ReleaseId **full-20261028-v1**, dataset **ibm-hi-medium-b1b99c68b765580f**. Deployed implementation commit **7aaa65c**; source-tree SHA **73eef6902a704b49b9b90957c068051b1e820f68e60409ab682b764039f2e4d7**. Never edit `Implementation/releases/full-v1/` or overwrite its outputs.

Full input lives at `raw/full-v1/` in bucket **is459-aml-g2team7-160885259244-us-east-1**. Both gzip inputs and manifest were uploaded conditionally and checksum-verified. Raw source files were unchanged. Local complete copy is ignored `Implementation/data/full-20220901-29-v1/`; do not regenerate it.

Jobs `is459-aml-full-{prepare,risk,detect,evaluate,control}` have concurrency1, retries0, no recurring triggers. Timeouts/workers: prepare5/45min, risk5/45min, detect10/120min, evaluate5/45min, control2/10min×3. Nominal maximum compute **US$14.19**, Q2 conservative30day storage/PUT estimate guard **US$10**, prior compute **US$0.280623**, other overhead separate. The monitor requests cancellation if compute plus prior/output/overhead reserves reaches **US$28**. Estimates are not a billing cap or invoice. Track actual states/costs; do not silently raise limits.

## Publication and dashboard

The existing published pilot **pilot-20220901-m00-v1** remains readable. Full publication requires all PASSED stage reports, physical Parquet counts/identities, complete schedule, calibration/holdout artifacts and hashes, then a conditional pointer update using the captured pre-run ETag. No partial full output is a published release.

The dashboard/SSM role and exact `dashboard-stack.json` are already approved but **no EC2 has been launched**. Only launch for final validation after processing is ready; remove the temporary stack afterward and verify EC2 termination, root disk deletion and public IPv4 release. Instance t3.small official base rate checked at **US$0.0208/hour**, disk/IP separate. No public application ingress.

Local application may still run in exec session **69287** at127.0.0.1:8501 (no cloud server cost). CUA `projectTab` in IAB may survive; call `cua.rewriteDocumentation()` when resuming computer use. For recovery EC2 use `deploy.py --phase dashboard --dashboard-template dashboard-recovery1-stack.json` so it loads schema3-capable frozen full-v2 software; unchanged IAM is already approved. Temporary SSM plugin is installed at `/private/tmp/is459-ssm-plugin/session-manager-plugin` version1.2.896.0 for future private port forwarding to local8502. Do not expose SSM tokens/URLs.

## Remaining work

1. Monitor the existing execution. If a stage fails, inspect its actual error/report/logs. Preserve completed preparation/Q1 and frozen attempts; changed code needs a new immutable release/output identity. No blind full rerun and no holdout-based tuning.
2. Verify all28 daily overlapping seven-day Q2 snapshots, complete evidence, explicit history/degree exclusions and evaluation populations. Report actual holdout metrics and the frozen five-percentage-point target honestly.
3. Verify full release/artifacts and previous-release retention on failed gates. Validate the private EC2 dashboard and both user scenarios; measure response/query costs and save actual full-data screenshots.
4. Remove costly compute/disk/IP, verify every known project job/query terminal, retain S3 and idle metadata. Update ledger, validation findings, STATUS/checkpoint and PR with actual evidence.
5. Human team owners/contributions/narration are not known; do not fabricate them. Runbook covers setup/demo/cleanup.

## Source, tests and pull request

Draft **PR5**: https://github.com/Kelvinpcw/is459-aml-project/pull/5 (already attached). Push actual validation/cleanup records to this feature branch; do not merge/remove old PR3/4 or change the shared Q1 GitHub connection.

The **67-test local suite passed**, plus additional cycle oracle, complete export, temporal evaluation and application smoke checks. Both templates pass cfn-lint. Runtime is `/private/tmp/is459-spark-validation/bin/python`, Python3.11/PySpark3.5.6/Java21. UTC is fixed internal parsing only; source timezone unspecified. No cloud/full effectiveness claim follows from local tests.

Read [README](README.md), [STATUS](Implementation/STATUS.md), [completion plan](Implementation/COMPLETION_PLAN.md), [runbook](Implementation/RUNBOOK.md), relevant source/tests and dated review records. Approval hashes are in `full-access-grant-authorization-20261028.json`; the initial auto-review rejection was resolved by that explicit approval. No subagents or automations were created.
