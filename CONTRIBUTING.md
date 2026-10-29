# Team contribution workflow

This applies to humans and AI agents. Start with [onboarding](TEAM_START_HERE.md) and [AGENTS.md](AGENTS.md). Use PRs to show changes and merge history, optional issues for questions/ideas, and [handoffs](Implementation/team-handoffs/README.md) for what the next teammate needs.

## Before starting

1. Understand the requested change and which files/contracts it affects. No assigned task, formal role or issue is required. For learning, start with the walkthrough/Q&A; don't invent implementation work.
2. Inspect local work, fetch current branches and read relevant open **and draft** PRs and handoffs. A task can be in progress without being on `main`.
3. If someone is changing the same files or owns a shared cloud resource, coordinate first. A branch isolates code, not AWS jobs, roles or outputs. An unanswered PR is not consent.

```bash
git status --short --branch
git fetch origin
gh pr list --state open
gh pr view PR_NUMBER --comments
```

Replace `PR_NUMBER` with the relevant number. Without `gh`, use the [PR page](https://github.com/Kelvinpcw/is459-aml-project/pulls). Don't print auth tokens to troubleshoot access.

## Start an isolated branch

For a clean checkout starting a new task:

```bash
git switch -c feature/your-task origin/main
```

Replace the branch name. Use `agent/tool-task` if preferred. If the working tree has edits, first identify who owns them; do not reset, stash someone else's work or silently carry it into your task. An already published task branch can incorporate `origin/main` with a normal merge; resolve conflicts with the relevant owner and rerun affected checks. Avoid rewriting shared history.

## Change and verify

- Work on editable source, not frozen release packages or generated data. See [README's folder map](README.md#where-files-belong).
- Run checks appropriate to the change using [SETUP.md](Implementation/SETUP.md). Docs require link/command checks; don't start AWS to validate Markdown. Test processing code locally with synthetic fixtures first.
- Update affected usage instructions. Update [STATUS.md](Implementation/STATUS.md) when implementation/completion state changes, identifying the evidence and scope. Historical findings are not overwritten to fit newer code.
- Add one short [task handoff](Implementation/team-handoffs/README.md) for meaningful progress, blockers and completion. Local task: `AWS: none`. AWS task that changes resources or starts paid work: follow [AWS_HANDOFF.md](Implementation/AWS_HANDOFF.md). **A purely read-only AWS check does not need a handoff or PR** unless the user asks for a shared record.
- Keep credentials, raw data, detailed AWS records/measurements/costs, local config and new screenshots private. Public notes describe changed behavior, checks, activity scope, cleanup/unknowns and next owner. Review every proposed attachment.

## Commit, push and open a PR

```bash
git diff --check
git diff
git add path/to/changed-source path/to/relevant-test path/to/task-handoff.md
git diff --cached
git commit -m "Explain the resulting change"
git push -u origin feature/your-task
```

Replace the explicit paths and branch. **Do not use `git add .` or `git add -A`.** Ignored/private files and another person's edits may coexist in the checkout.

Open a PR through GitHub's page, or use the CLI below after writing a reviewed description to a local file. The [PR template](.github/PULL_REQUEST_TEMPLATE.md) lists the expected information.

```bash
gh pr create --base main --head feature/your-task --title "Describe the change" --body-file /path/to/reviewed-description.md
```

Use a draft PR for work in progress. Update its handoff/description when scope changes; the final description should explain the final implementation, not abandoned plans. Code on a pushed branch is visible to teammates; `main` changes when the PR is merged. **Contributors may merge their own PRs** after the relevant checks pass and they inspect overlapping work. A separate teammate review is optional, though useful for changes to shared schemas/security/deployment behavior. Agents may merge when the human asks or clearly authorises it; no additional reviewer gate is imposed by this guide. Repository-enforced branch rules, if any, still apply.

## Verify it reached GitHub

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/feature/your-task
gh pr view --json url,state,headRefOid
```

The local commit, remote branch head and PR head must agree. Give the user the commit, PR link, checks actually run, AWS scope/cleanup and next step. If authentication/network/policy prevents publication, say **NOT SYNCED TO GITHUB**, preserve the local handoff and name the blocker. Never claim a local checkpoint is shared.

Necessary authorised stop/cleanup comes before Git troubleshooting; never leave paid compute active just to finish a commit. Do not start additional cloud work while a prior required handoff remains unpublished.

## Merge and let teammates pick it up

After checks, inspect the PR diff/conflicts and merge it through GitHub (or ask your agent to merge). Don't bypass repository checks or rules. Update the PR/handoff if there are unresolved limitations.

On a clean checkout when ready to leave the branch:

```bash
git switch main
git pull --ff-only origin main
```

If a branch is checked out in another worktree, use that checkout or ask the agent to create a clean task worktree; don't force-switch or remove it. Don't delete a branch that a shared Glue integration still references. A code merge **does not** deploy AWS code, publish new data, restart an app or add a schedule. Those are separate, explicitly authorised operations.

## What is shared and what is private?

| Shared on GitHub | Kept local/private |
| --- | --- |
| Source, configuration templates, synthetic tests and usage docs | Credentials, tokens, `.env`, AWS config, signed URLs |
| PR review, task ownership, changed contracts and next steps | Original/generated datasets and transaction exports |
| Sanitised session scope, outcome category, blockers and cleanup uncertainty | Raw cloud reports/logs/screenshots, detailed measurements/costs and operator checkpoint |

No hooks or background auto-push are installed. Publishing is a deliberate checked step, and instructions are not an automated cloud lock or monitoring service.
