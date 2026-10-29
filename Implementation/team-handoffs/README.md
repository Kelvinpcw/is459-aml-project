# Shared task handoffs

This folder is the team's durable update feed for humans and AI agents. Read it with [STATUS.md](../STATUS.md) and [open/draft PRs](https://github.com/Kelvinpcw/is459-aml-project/pulls). A record on a PR branch can be newer than `main`; inspect that PR's files before picking up related work.

**Current collaboration policy:** no assigned task/formal role or separate reviewer is required. Older handoffs preserve the rules in force at their date; use [CONTRIBUTING.md](../../CONTRIBUTING.md) for today’s self-merge/change-tracking workflow. Their scoped technical observations remain historical evidence.

## When to write one

Write/update one record for a meaningful change, plan, blocker or completion. Group related actions; don't create a file per command. State-changing, failed/aborted mutation attempts and cleanup sessions need a record; **a purely read-only AWS check does not need one or a PR** unless the user asks. See [AWS_HANDOFF.md](../AWS_HANDOFF.md). Local-only tasks say **AWS: none**.

Copy [_TEMPLATE.md](_TEMPLATE.md) to `YYYY-MM-DD-HHMMZ-owner-task.md` using the actual UTC time and a unique owner/task name. Add a PR link when available. Existing older naming is retained for stable links. Don't overwrite another person's record or fabricate ownership.

## What the next agent needs

- Owner, branch/PR, date/time and status: PLANNED, IN_PROGRESS, BLOCKED, COMPLETED, FAILED or ABORTED.
- Requested scope and consumers/files/contracts affected.
- What changed and why; what was actually checked and what remains unverified.
- AWS scope or none; cleanup observed versus unknown. Keep detailed records/measurements/costs private.
- Next safe step, responsible teammate and blockers.
- Verified pushed commit and PR in the final report. Avoid writing a commit's own hash into itself.

A pushed handoff means the note is visible, not that its claims were independently verified or the work was deployed. A COMPLETED change may still have an unmerged PR; contributors can merge their own after checks. The latest relevant scoped observation wins; a newer unrelated record does not replace earlier evidence.

Follow [CONTRIBUTING.md](../../CONTRIBUTING.md) to commit/push explicit paths and verify the remote head. No automatic GitHub sync or AWS monitoring is provided by these instructions.
