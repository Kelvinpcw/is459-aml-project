# Session: <owner / task>

<!-- Copy to a dated, uniquely owned file. Replace placeholders; do not claim unobserved results. -->

- **Owner / GitHub handle:** <teammate accountable for this session>
- **Branch / PR:** <task branch; add PR link once created>
- **Updated at / observation interval:** <ISO 8601 with Z or explicit offset>
- **Status:** <PLANNED | IN_PROGRESS | COMPLETED | FAILED | ABORTED | BLOCKED>
- **Evidence kind:** <planned only | local tests | saved evidence | fresh AWS observations>

## Scope and coordination

- Current user-authorised actions and budget bounds: <scope, not inherited approval>
- Shared resource owner / coordination confirmation: <owner, confirmation or blocker>
- AWS account / region verification: <observed account/region and time, or not verified>
- Affected components, logical resources and owned output namespace: <public-safe names/aliases>
- Code commit / immutable release: <exact identities or not applicable>
- Dataset / run / analysis IDs and time window: <public-safe identities or not applicable>

## Actions and observed outcome

- Actions/commands actually run: <no credentials, signed URLs, raw data or private logs>
- Outcome / failures: <observed result and timestamp; distinguish local vs cloud>
- Publication pointer / consumers affected: <changed, unchanged, unknown or not applicable>
- Contracts/source/config changed: <what and why, or none>
- Checks actually run: <commands/results; unrun checks and blockers>
- Private evidence custodian: <teammate holding detailed checkpoint/ledger; no sensitive links>

## Cost and cleanup

- Cost / basis: <amount and scope; estimated vs measured, or unknown>
- Active compute/jobs/queries: <observed state and time, or not verified>
- Cleanup verification: <what was observed stopped/deleted/retained, or not verified>
- Remaining chargeable resources / uncertainty: <storage/logs/idle resources etc.>

## Handoff

- Next safe step and responsible owner: <specific step; approval required if applicable>
- Blockers / do not repeat: <completed outputs to reuse, consumed approvals, unresolved ownership>
- Supersedes/follows: <relevant prior handoff links and scope, or none>
- GitHub sync: <pending push | pushed; if blocked say NOT SYNCED TO GITHUB and why>

<!-- Final chat/PR must name the verified pushed commit and PR URL. Do not add a
commit's own hash to itself; identify source/deployed commits above instead. -->
