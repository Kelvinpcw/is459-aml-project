# TRACE layout for the connected dashboard

- **Owner:** Kelvinpcw, assisted by Codex.
- **Branch:** `feature/trace-connected-dashboard`.
- **Status:** IN_PROGRESS — source and synthetic checks complete; bounded connected preview next.
- **Date:** 29 October 2026, Asia/Singapore.
- **Evidence kind:** source inspection and local synthetic tests; no fresh AWS observations yet.

## Authorised scope and coordination

The user requested adapting the TRACE visual structure to the existing connected Streamlit dashboard, retaining published results, rolling reporting dates, daily trends and complete evidence downloads. This follows merged PRs #8 and #9; no other open PRs were found at task start. Based on main `0c039240ac0fa0002d64d387c2e8977ede428822`.

Only local dashboard source, synthetic tests and documentation will change. Planned preview uses the operator's existing private published release through the unchanged verified-profile launcher and bounded read-only dashboard queries (512 MB/query, 30-second cancellation). No shared cloud jobs, output prefixes, roles or publication pointers will be modified. Existing US$30 total ceiling remains; material new costs require discussion. No paid processing, deployment or recurring schedule is planned.

## Plan

1. Use TRACE-inspired navigation, summary cards, monitoring insight and case queue.
2. Keep denominators, support, exact money, label separation, snapshot bounds and pinned-release validation intact. Keep the offline prototype's invented fixtures separate.
3. Run synthetic UI/data/graph/release tests before browser verification. Reuse saved evidence where possible; do not rerun processing.
4. Record actual preview observations, query cost basis and cleanup without publishing raw results, screenshots or resource locators. Push the final source and ask for teammate review.

## Current state

AWS: none so far. Account/region, active cloud compute and current billing were not inspected. Local port 8501 had no listener at task start. Private operational records remain with the operator. GitHub sync: planned record published on the task branch; verify the remote head before preview.

## Local implementation progress

TRACE-inspired layout is implemented on this branch, with no SQL, detector, evaluator or frozen-release changes. Twenty-three focused trend/navigation/presentation/release checks passed; a further complete-source-evidence app check passed. The new explanation is tested against full supplied baseline counts and refuses low-support, zero-baseline or non-finite rankings. Supported zero-label segments stay visible in volume/rate comparisons. Provenance navigation makes no additional data reads. Browser verification is next; current cloud state and costs remain not verified.

PR: https://github.com/Kelvinpcw/is459-aml-project/pull/10 (draft). The exact pushed source commit is recorded in the PR history and final report, not self-referentially in this file.
