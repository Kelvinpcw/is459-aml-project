# US$90 planning ceiling and future rerun configuration

- **Owner:** Kelvinpcw, assisted by Codex.
- **Branch:** `feature/full-rerun-20261029`; [PR #13](https://github.com/Kelvinpcw/is459-aml-project/pull/13).
- **Updated at:** 30 October 2026 (Asia/Singapore; continuation after token interruption).
- **Status:** STOPPED — user clarified GitHub configuration only; no full run or service deployment is authorised now. Cleanup verified after refreshing the operator login; no compute from this attempt remains active.
- **Evidence kind:** local source checks plus private cloud stop/cleanup observations. Detailed operational records stay private.

## Current scope and permission

Save US$90 as the planning ceiling for future work. **Do not start or resume processing or deploy services from this record.** Future paid work needs fresh, scoped user authorisation, ownership checks and a new unused attempt identity. The earlier requirement to stop expensive compute remains.

Codex initially interpreted the budget change as an immediate rerun request, uploaded the frozen package, created isolated definitions and started preparation. The user corrected that interpretation. The workflow was cancelled and preparation was directly verified stopped; Q1, Q2, evaluation, publication and the dashboard did not start. The previous published release was verified unchanged. Deletion of only the new idle stack was directly verified complete: its jobs, roles and workflow definition are absent, and no temporary dashboard instance exists. S3 and prior resources are preserved. This interrupted attempt must not be reused.

## Source retained for future review

- New isolated definitions/driver and immutable full-v6 package use the revised ceiling. Core Q1/Q2/snapshot/evaluator/control files match full-v5; the updated connected TRACE dashboard and stylesheet are included. No detector/evaluator thresholds or chronological rules changed.
- Deliberate upload/create/verify/start/status/stop phases require an exact private approval/plan and template hash. Start has one-time request markers, fresh output checks and publication compare-and-swap. No retries or recurring schedule are introduced. Estimates are not billing caps.
- Q2 retains label/annotation/Q1/evaluation denies. The proposed temporary dashboard has no inbound access, SSM-only access, a one-hour termination timer and delete-on-termination root disk. It was not launched.
- `AGENTS.md` explicitly distinguishes the saved ceiling from permission to execute. Private approval/plan flags are revoked; existing one-time markers also prevent reuse.

## Checks

- Full existing synthetic suite: 115 tests passed after correcting a local Python driver/worker mismatch. The initial run failed because workers used system Python 3.13 with a 3.11 driver; pipeline code was unchanged by that environment fix.
- Six focused rerun checks passed again during this continuation, including isolation/label denies, complete workflow/CAS, dashboard safeguards and rejection of wrong/unapproved plans before identity/cloud calls.
- Both new templates passed cfn-lint and Python compilation during preparation. Continuation checks verified 27 local Markdown link targets across the four corrected documents; diff checks pass. No previous frozen package changed.
- Cloud observations are scoped to stopping/removing this interrupted attempt. They do not establish a completed new pipeline run or deployment.

## Cleanup outcome

The refreshed-login check verified deletion of the isolated definitions and retention of the prior published release. Saved predeletion evidence verified the cancelled workflow and stopped preparation; execution history is now absent with the deleted workflow. This was a scoped cleanup check, not a whole-account audit. No additional run, role grant or dashboard launch is authorised.

## Next safe step

Review the source/configuration in GitHub or continue local work. Do not start AWS work automatically. Consult this record and the private checkpoint before any separately authorised future session; the interrupted namespace and markers are consumed.
