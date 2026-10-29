# Task: <short outcome>

- **Owner:** <human accountable; agent/tool if relevant>
- **Branch / PR / issue:** <links or pending>
- **Updated at:** <ISO 8601 with timezone>
- **Status:** <PLANNED | IN_PROGRESS | BLOCKED | COMPLETED | FAILED | ABORTED>
- **Evidence kind:** <plan | source inspection | local checks | dated cloud observation>

## Scope and coordination

<Requested task, affected component/consumers and owner agreement. Identify relevant prior handoffs/PRs. For local-only work, state AWS: none. A branch or PR is not a shared-resource lock or cloud approval.>

## Changes and checks

- Changed behavior/files/contracts: <what and why>
- Source commit/release checked: <existing exact identity or PR head; don't embed this commit's own hash>
- Checks actually run: <command and result; unrun checks/missing inputs>
- Outcome/unknowns: <distinguish implemented, locally tested, saved evidence and fresh observations>

## AWS scope and cleanup

<None, or short public-safe activity/outcome category. State whether compute was started/stopped, what cleanup was actually observed and what was not checked. Detailed resource locators, raw outputs/screenshots, query/run measurements, costs and credentials stay private with the operator. No account-wide claim from a scoped check.>

## Next teammate / agent

- Next safe step and owner: <specific action; approval if needed; do not invent assignments>
- Blockers / don't repeat: <missing access/evidence, consumed run approval or completed outputs to reuse>
- GitHub sync: <pending push | pushed and PR linked | NOT SYNCED TO GITHUB — exact blocker>
