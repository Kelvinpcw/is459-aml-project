# Task: fresh ingestion-to-EC2 run and removal of old generated outputs

- **Owner:** Kelvinpcw with Codex
- **Branch / PR:** `agent/codex-full-run-20261030`; [PR #19](https://github.com/Kelvinpcw/is459-aml-project/pull/19)
- **Updated at:** 2026-10-30 (+08:00)
- **Status:** IN_PROGRESS
- **Evidence kind:** source checks, fresh inventory and explicit current run authorisation

## Scope and coordination

The user explicitly requested one new whole pipeline run from ingestion through visualization on EC2, removal of past S3 run outputs, and detailed setup/run instructions. The existing planning ceiling remains unchanged; the current request grants this new attempt, not reuse of a revoked attempt. The operator's private plan records the estimate, reserves, exact identities and approval evidence. Estimates/timeouts are not billing caps.

Only the operator's maintained AML stack, source staging and generated output paths are included. Open PR #18 is this operator's completed definition cleanup, not another owner's work. No other open PR was observed. The new run updates the maintained five jobs rather than adding duplicates; shared Catalog database/workgroup are reused. No recurring schedule or unrelated shared-account resource changes.

## Changes and checks

- New `build_run30.py` / `run30.py` define a fresh ingestion namespace/run on the maintained stack. Deployment uses an inspected change set and rejects resource additions/removals/replacements. Exact deployment verification and one-start private markers are required.
- Reuse immutable full-v6 processing software; frozen detector/evaluator settings stay unchanged. The stopped prior attempt remains consumed and revoked.
- `upload_input.py` supports an explicit scoped new raw prefix and private observation path. Complete stable-ID input artifacts are uploaded with conditional completion and streaming/server-part checksum verification. Original source records/checksums/ordinals remain unchanged.
- Fourteen local cleanup/deployment/plan/isolation/dashboard checks passed. Both new templates passed AWS validation. Fresh ingestion and immutable software were uploaded/verified; the modification-only stack update reached UPDATE_COMPLETE and exact deployment verification passed. One fresh full workflow is RUNNING. The scheduled 30 October (+08:00) observation found Preparation, manifest control and Q1 SUCCEEDED; Q2 detection is RUNNING. Evaluation/publication/EC2 are not yet started; no completed new release is claimed.
- Old generated outputs are inventoried privately. Deletion is deferred until the new release and EC2 dashboard are verified, retaining a working previous publication on failure. Preserve original/raw source, annotations, required software and current new outputs. Do not delete a bucket that is still used.

## AWS scope and cleanup

Read-only source and output inventory completed with the explicit verified project profile/region. At plan publication no mutations had started. Since then fresh ingestion/software verification and the reviewed existing-stack update completed; one new full workflow is now RUNNING. New compute will be monitored against the private cost reserve; stop requests require terminal verification. The private EC2 dashboard has no inbound ports, uses SSM and a one-hour terminate guard, with root disk deletion. No processing retries or automatic recovery are authorised. S3 cleanup must use the exact pre-run object inventory with fresh pointer and object-identity checks.

## Next teammate / agent

- Plan published, fresh ingestion/software verified, reviewed stack update applied and verified; one new execution started. Monitor it; never invoke start again. At the user's request, frequent local status readers are stopped and a current-chat continuation checks at 20-minute intervals, notifying only meaningful changes/problems. This is a local Codex continuation, not an AWS recurring schedule.
- After successful publication, launch/verify EC2 visualization; delete old generated S3 outputs and stale Catalog tables only when proven superseded, then verify and publish outcome. Keep operational identities and measurements private.
- Document the actual end-to-end setup, repeatable commands, access and shutdown steps. Do not claim success until directly verified.
- GitHub sync: plan pushed; draft PR #19 opened. No other owner should start or update these shared jobs until this session is terminal.

## Scheduled continuation — 30 October 2026

Read-only execution/job status check with the explicit verified project profile found preparation, manifest creation and Q1 successful, with Q2 detection active. The stack is stable. No run/retry, query, deployment or deletion was started by this check. Previous publication and old-output retention remain in effect pending verified completion. Detailed timings/estimates stay private. Continue at the user-requested 20-minute interval.
