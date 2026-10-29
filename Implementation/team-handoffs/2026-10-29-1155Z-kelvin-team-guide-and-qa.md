# Team guides, pipeline learning and change tracking

- **Owner:** Kelvinpcw, assisted by Codex.
- **Branch:** `feature/team-workspace-guide`; PR linked in final report/history.
- **Updated at:** 2026-10-29T11:55:50.112207+00:00.
- **Status:** COMPLETED — documentation/helper cleanup; commit/push/merge state is reported in the linked PR.
- **Evidence kind:** source inspection and local checks only.

## Requested outcome and policy clarification

The user wants GitHub to explain the mostly completed pipeline, support teammates learning with AI and preparing for Q&A, and record changes so others can follow them. The user explicitly removed assigned-task/formal-role requirements and mandatory separate teammate review. Contributors can self-merge after checks and checking for overlapping work; agents can merge when requested/authorised. Existing repository rules still apply. This supersedes those administrative restrictions in older onboarding/handoff notes; it does not grant cloud spending/access or change data contracts.

## Changes

- Short root navigation, beginner AI prompt, plain-language full-pipeline walkthrough and 26-question Q&A/rehearsal guide with source references.
- One contribution/push/merge workflow, optional change/question issue template, PR template and shared handoff index/template. Local edits and AI chats don't automatically update GitHub; explicit commits/pushes and merge state are required.
- Clear console-login versus SSO routes, individual verified AWS profiles, scoped read-only completion checks and task-specific local setup. New version-only tool checker installs/logs into nothing and makes no API calls.
- Profile guard now requires an explicit profile, checks configured region before STS and passes the workload region explicitly. All callers inspected already supply a profile.
- Older deployment/recovery and completion instructions preserved in a labelled archive, with stable entry-point wrappers. Pilot readiness/cleanup notes labelled historical. Frozen releases, original outputs and prior handoff contents preserved.
- Based on main after the TRACE layout merge. Pipeline-verification PR #11 was read while open; another contributor then merged it into main. This branch incorporates that current main without changing their observation record. Changes to STATUS.md are introductory reading guidance, preserving its existing timeline.

## Checks actually run

- Eight new offline unit tests passed, exercising version-only/no-shell tool probes, missing/failed/timeout cases, explicit-profile requirements, region/account rejection and no default fallback. AWS commands were stubbed; no real AWS API calls.
- Local tool checker ran in docs mode (Git and optional GitHub CLI versions only), plain and JSON output.
- Local Markdown target/anchor and Bash-block syntax checks passed; 27 Markdown files, 177 local targets and nine heading anchors; 24 Bash blocks syntax-checked. Shell examples were syntax-checked, not executed as installations/logins/deployments.
- Bash syntax checks passed for the profile guard and existing dashboard launcher. Diff check passed.
- No new-user installation, real interactive login, Windows setup, full Spark/data replay or cloud validation was performed.

## AWS scope and cleanup

**AWS: none.** No AWS account/resource/billing checks, queries, processing, deployment, IAM changes or cleanup. No cloud costs were incurred by this task; existing resources/billing were not audited. Existing local dashboard/server state was not changed. Detailed operator evidence stays private.

## Next teammate / agent

Start with TEAM_START_HERE.md, PIPELINE_WALKTHROUGH.md and Q_AND_A.md. Ask the AI to explain/quiz before making changes. Follow CONTRIBUTING.md to check/push/merge a requested change and leave a short update; no assigned role or separate reviewer required. AWS work remains a separately scoped activity. Exact pushed/merged commits and PR are reported after publication; never claim a local-only edit is already shared.

A later user request authorises a separate full-pipeline rerun/deployment phase under the revised project ceiling. Only its high-level source instruction is updated here. Fresh cloud inspection/planning will be a separate session/handoff; this cleanup itself made no AWS calls.
