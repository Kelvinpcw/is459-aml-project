# Shared AWS handoff — required for humans and AI agents

Effective **29 October 2026**. GitHub is the team's shared context. Every AWS session needs a short, public-safe record, committed and pushed on a task branch with a PR. A chat response or ignored local checkpoint alone is not enough.

This adds sanitised collaboration summaries to the earlier source-only policy. **Raw reports, detailed checkpoints, new ledger entries, secrets and datasets remain private/local.** No past private run is automatically approved for publication. No AWS run or live-state check was performed to establish this policy.

## Read before starting

1. Read [STATUS.md](STATUS.md), [AGENTS.md](../AGENTS.md), and the newest relevant dated records in [team-handoffs/](team-handoffs/). Each record describes its stated scope/time, not the entire AWS account. A newer session for a different component does not supersede every older record.
2. Fetch GitHub and check open PRs, including draft PRs, for unmerged work/handoffs. For example, `gh pr list --state open` and `gh pr view NUMBER --comments`; inspect relevant changed handoff files too. Do not merge someone else's branch merely to read it. If GitHub is unavailable, state that coordination is blocked; do not silently assume `main` is current.
3. Confirm the current user-authorised scope, budget, resource owner and unique job/output/run namespace. Branches and draft PRs are **not cloud locks**. Get the relevant owner's confirmation before touching shared resources. Old approvals, an unanswered PR, and another teammate's records are not permission.
4. Verify your own explicit profile/account/region as described in [SETUP.md](SETUP.md#4-aws-identity--verify-before-cloud-work). Record the read-only observation; do not expose credentials/profile configuration. Where private operational evidence is needed, request it from the operator rather than reconstructing it by rerunning jobs.

## Record and publish

Copy [_TEMPLATE.md](team-handoffs/_TEMPLATE.md) to `Implementation/team-handoffs/YYYY-MM-DD-HHMMZ-owner-task.md` (UTC filename; use the actual observation timestamp/timezone in the content). Use one file per task/session to reduce conflicts. Do not overwrite another person's record. For corrections after completion, add a dated correction/follow-up preserving the original claim.

**Before mutations or paid processing:** push a sanitised `PLANNED` record and open a draft PR describing the intended scope, ownership and approved bounds. Move it to `IN_PROGRESS` when starting and publish meaningful progress/changes of ownership. Do not run if the plan cannot be shared or shared-resource ownership is unresolved. Never delay necessary authorised stop/cleanup for a Git update.

**After every AWS session:** update the record even for read-only checks, failed/aborted runs, no-op deployments or cleanup. Related API calls can be grouped; a commit per API call is unnecessary. Required information:

- Owner, branch, UTC/offset timestamp, session status and observed account/region.
- What the user authorised for this session (without private conversation dumps); no inherited approval.
- Exact code commit/release and relevant dataset/run/analysis identities; date/window scope and non-sensitive output namespace or logical alias. Say `not applicable` where appropriate.
- Commands/action types and observed outcome: distinguish a plan, local test, saved evidence and fresh AWS observation. Do not turn an estimate or old screenshot into a successful run.
- Resource/job/publication changes; logical resource ownership and affected component/contracts. Give public-safe identifiers only; privately retain exact sensitive locators and name the teammate who holds them.
- Cost with basis (`estimated`, `measured`, or `unknown`), bounded queries/compute still running, cleanup actually verified and what remains chargeable. Idle definitions do not establish that all compute/storage charges ended.
- Tests/checks actually run, failures, blockers, next safe step and who must act. Use `unknown`/`not verified`, never invent missing results.

Update [STATUS.md](STATUS.md) if implementation/completion state changed; keep raw evidence and detailed ledger/checkpoint updates local. Review the exact diff before committing. Never attach tokens/keys, credentials, signed URLs, `.env`/AWS config, original transaction data, raw logs/screenshots or unreviewed operational JSON. Account IDs/ARNs are not credentials, but publish only identifiers needed for coordination and approved as public-safe. Use logical aliases when uncertain; coordinate exact locators privately.

Stage only your explicit files, commit, push your branch and create/update its PR. Verify the pushed head:

```bash
git diff --check
git diff --cached  # inspect after staging explicit paths; check for private data
git commit -m "Record scoped AWS session outcome and handoff"
git push -u origin YOUR_TASK_BRANCH
git rev-parse HEAD
git ls-remote origin refs/heads/YOUR_TASK_BRANCH
# The two commit hashes must match. If there is no PR yet:
gh pr create --base main --head YOUR_TASK_BRANCH --title "Scoped task and handoff" --body-file YOUR_REVIEWED_PR_BODY
```

Replace placeholders; do not copy these as a cloud execution plan. Never force-push or commit to `main`. Ask a teammate to review/merge; agents must not merge their own PR. While it is unmerged, other agents must read its handoff on the PR branch. A merged historical record is still not proof of live state.

End the user-facing task report with the commit, PR URL, tests actually run, AWS effects/costs, compute/cleanup state and remaining blockers. If a push/PR is blocked, clearly report **NOT SYNCED TO GITHUB**, the exact blocker and where the local handoff is saved. Make authorised compute safe, but do not start additional paid work while the previous handoff remains unpublished.

## Current shared baseline

- Software implementation and previously published pilot limits are in [STATUS.md](STATUS.md) and [AGENTS.md](../AGENTS.md).
- Newer detailed operational records were historically local-only; see the [checkpoint pointer](../PROJECT_CHECKPOINT.md). **This policy does not verify their contents, current cloud state, cleanup or remaining budget.** Ask the relevant operator for a sanitised handoff before relying on private results or continuing their work.
- The initial [collaboration/prototype handoff](team-handoffs/2026-10-29-collaboration-and-prototype.md) records a local-only publication task, not an AWS observation.
- These instructions guide agents; they are not an automated synchronisation service, an account-wide inventory, a lock or spending authorisation.
