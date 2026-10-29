# Beginner teammate onboarding guide

- **Owner:** Kelvinpcw, assisted by AI.
- **Date:** 29 October 2026; documentation task, not a cloud observation.
- **Branch / PR:** `feature/team-ai-handoff-and-visualization`, [PR #9](https://github.com/Kelvinpcw/is459-aml-project/pull/9).
- **Status:** COMPLETED — documentation and local verification complete; teammate review/merge required.
- **Evidence kind:** local repository/documentation checks only.

## Scope and outcome

The user asked to put the beginner setup instructions in GitHub so friends can clone the project and let their AI assistant guide onboarding.

- Added root [TEAM_START_HERE.md](../../TEAM_START_HERE.md), linked prominently from README, setup, status and agent instructions.
- Includes clone/open-folder steps, a self-contained AI onboarding prompt, task-specific dependency choices, GitHub collaborator/login guidance, conditional AWS CLI/SSO instructions and explicit profile/account/region checks.
- Does not assume the team's SSO is configured or grant AWS approval. AWS access requires the administrator; the prompt defaults to local setup and asks for task/scope instead of selecting backlog work.
- Reuses the existing branch/PR for this related collaboration follow-up. No dashboard source, frozen releases, private evidence or existing local ledger changed.

## Checks actually run

- Local Markdown links: **51 targets checked, zero missing**; **3 fragment anchors checked**, all valid.
- Bash examples in the six follow-up documents: **10 blocks syntax-checked with `bash -n`**, all passed. Example commands were not executed.
- `git diff --check`: passed. Follow-up diff reviewed for private records/credentials; only onboarding documentation and links changed.
- External URLs, actual new-user installations/authentication, AWS configuration/login, Python/Spark and prototype tests were **not run** for this docs-only follow-up. Prior prototype results remain in the preceding handoff.

## AWS effects / cost / cleanup

**AWS: none.** No AWS API calls, login/profile configuration, IAM changes, queries, deployments, paid processing or cleanup. No cloud costs incurred by this task. Existing AWS resources, remaining budget and ongoing charges are not verified. No server or compute started for this follow-up.

## Next step / blockers

- Teammate review/merge of PR #9 is still required before a normal `main` clone gets these instructions.
- Team coordinator must invite GitHub collaborators and assign tasks; the AWS administrator supplies individual access only if the assigned task requires it. Agents cannot do these by assuming access.
- Follows the [collaboration/prototype handoff](2026-10-29-collaboration-and-prototype.md); does not supersede its test history or assert new cloud results.
- **GitHub delivery:** the PR/branch above carries this follow-up. The final task report must identify its verified pushed commit; a local copy alone is not proof of publication. If publication fails, report NOT SYNCED TO GITHUB with the exact blocker.
