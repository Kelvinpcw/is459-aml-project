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
- Fourteen local cleanup/deployment/plan/isolation/dashboard checks passed. Both new templates passed AWS validation. Fresh ingestion and immutable software were uploaded/verified; the modification-only stack update reached UPDATE_COMPLETE and exact deployment verification passed. The fresh full workflow and publication SUCCEEDED. The EC2 dashboard has passed real browser/data verification; superseded output and Catalog cleanup are verified. Final dashboard teardown remains pending its bounded viewing window.
- Old generated outputs are inventoried privately. Deletion is deferred until the new release and EC2 dashboard are verified, retaining a working previous publication on failure. Preserve original/raw source, annotations, required software and current new outputs. Do not delete a bucket that is still used.

## AWS scope and cleanup

Read-only source and output inventory completed with the explicit verified project profile/region. At plan publication no mutations had started. Since then fresh ingestion/software verification and the reviewed existing-stack update completed; the one new full workflow has completed successfully. New compute will be monitored against the private cost reserve; stop requests require terminal verification. The private EC2 dashboard has no inbound ports, uses SSM and a one-hour terminate guard, with root disk deletion. No processing retries or automatic recovery are authorised. S3 cleanup must use the exact pre-run object inventory with fresh pointer and object-identity checks.

## Next teammate / agent

- Plan published, fresh ingestion/software verified, reviewed stack update applied and verified; one new execution started. Monitor it; never invoke start again. At the user's request, frequent local status readers are stopped and a current-chat continuation checks at 20-minute intervals, notifying only meaningful changes/problems. This is a local Codex continuation, not an AWS recurring schedule.
- Processing, publication, actual EC2 visualization and superseded S3/Catalog cleanup are verified. Preserve the bounded live viewing window; the remaining continuation only verifies instance/disk shutdown and removes the temporary dashboard stack. Keep operational identities and measurements private.
- Document the actual end-to-end setup, repeatable commands, access and shutdown steps. Do not claim success until directly verified.
- GitHub sync: source/progress pushed in PR #19; ready for review after this update. No other owner should start or update these shared jobs until this session is terminal.

## Scheduled continuation — 30 October 2026

Read-only execution/job status check with the explicit verified project profile found preparation, manifest creation and Q1 successful, with Q2 detection active. The stack is stable. No run/retry, query, deployment or deletion was started by this check. Previous publication and old-output retention remain in effect pending verified completion. Detailed timings/estimates stay private. Continue at the user-requested 20-minute interval.

The next scheduled observation found Q2 detection and Catalog registration successful, with evaluation active. No failures or extra starts were observed; the existing execution continues. Publication and EC2 remain pending. No outputs were deleted.

## Full workflow and publication verified — 30 October 2026

The single new full execution SUCCEEDED, including preparation, manifest creation, Q1/Q2, Catalog, evaluation and publication. All inspected new Glue runs are SUCCEEDED and no processing remains active. Independent readback verified the current manifest hash, four PASSED report hashes, declared population/identity/calibration gates and Catalog output locations. This is fresh cloud completion evidence for one full execution, distinct from the earlier recovery-based release. Detailed measurements and identities remain private.

Next authorised action: create and verify the planned temporary SSM-only EC2 visualization using the reviewed immutable dashboard package. Then remove only inventoried superseded S3 outputs and proven-stale Catalog entries; no processing rerun is needed. EC2 creation is still pending at this update.

## EC2 visualization and old-output cleanup verified — 30 October 2026

The temporary stack reached CREATE_COMPLETE; the service is active and its health endpoint passed. Browser verification loaded the new release's actual Monitoring charts/counts, connected case graph/accounts/rule, complete evidence preparation and Evaluation metrics/baselines. The instance uses SSM-only access. Actual no-inbound security groups, terminate-on-shutdown, root disk deletion and scheduled shutdown were verified, rather than assumed from a template.

The approved pre-run S3 inventory was dry-run checked and deleted in exact conditional ETag batches. Fresh listing confirms all inventoried old generated objects absent; the new publication remains valid. Raw inputs, annotations, software, new outputs and bucket remain. Four archived old Catalog definitions were retired only after checking unchanged definitions, empty old output locations and exclusion from the new publication; the new tables remain. No processing or queries were rerun for cleanup screenshots.

The maintained stack template now mirrors the verified deployed run configuration. Fourteen local guard/isolation/cleanup checks and documentation link/diff checks pass. Frozen processing/detector/evaluator settings are unchanged; there was no full local Spark-suite rerun for documentation/operator changes.

**Remaining active compute:** the explicitly requested EC2 visualization remains live for its bounded viewing window. It has a verified one-hour termination guard; exact deadline/instance/disk/session identities stay in the private checkpoint. Final termination, root-volume deletion, released public IP and temporary stack deletion are not yet observed and must not be claimed from the timer alone. A user-requested 20-minute local continuation now performs only that final cleanup verification and removes itself once complete. Processing is terminal; no additional run, redeployment, data deletion or recurring AWS schedule is authorised. Retained S3/log storage and normal requests remain chargeable; this is not an account-wide cost audit.
