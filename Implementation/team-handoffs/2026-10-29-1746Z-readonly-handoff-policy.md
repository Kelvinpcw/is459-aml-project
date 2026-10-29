# Session: read-only AWS handoff policy

- **Owner / GitHub handle:** Kelvinpcw (session run with an OpenCode agent)
- **Branch / PR:** `agent/opencode-readonly-policy`; PR link added after creation.
- **Updated at:** 2026-10-29T17:46Z (2026-10-30 01:46 +08:00)
- **Status:** COMPLETED
- **Evidence kind:** local documentation change; **AWS: none**

## Scope and change

The user clarified that a purely read-only AWS check does not need a team handoff or PR. Only work that changes tracked state needs one. This change updates the written policy consistently; it does not alter AWS resources, code or data.

- `AGENTS.md`: handoffs are required for state-changing AWS work, failed/aborted mutation attempts and cleanup; pure read-only checks are exempt and may be summarised in chat.
- `CONTRIBUTING.md`, `Implementation/team-handoffs/README.md`, `TEAM_START_HERE.md`, `README.md`: same exemption.
- `Implementation/AWS_HANDOFF.md`: read-only checks need no handoff/PR; the end-of-session record applies to changes, failures and cleanup.
- `Implementation/SETUP.md`, `Implementation/VERIFY_PROGRESS.md`: read-only verification ends with a chat/private summary, not a pushed handoff.
- `Implementation/STATUS.md`: policy statement updated; the 30 October exemption is explicit.
- `.github/PULL_REQUEST_TEMPLATE.md`: AWS handoff link is required for state changes, not read-only checks.

## Checks actually run

- `git diff --check` — passed.
- Repository-wide search for stale phrases such as “every AWS work session”, “including read-only” and “even for read-only” — no remaining matches outside archived/historical records.
- No AWS calls, tests, deployments or data changes were made for this policy edit.

## Handoff

- **Next safe step:** state-changing AWS work still follows `AWS_HANDOFF.md`; read-only checks can be reported in chat. No cloud action is needed to apply this policy.
- **Blockers:** none. Archived historical records retain the rules in force at their date and are not rewritten.
- **GitHub sync:** pushed on the task branch; PR opened for review.
