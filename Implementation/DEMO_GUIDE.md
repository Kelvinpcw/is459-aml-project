# Setup and demonstration recording guide

Use a real successful published release and the operator's current cleanup record. Do not show credentials, login tokens, signed URLs or personal AWS configuration. New recordings and AWS observations remain local under `Implementation/data/` unless the team explicitly authorises publication.

## Setup walkthrough — suggested three minutes

1. Introduce the two decisions: monitoring allocation from historical labels, and connected investigation leads generated without those labels. Identify the synthetic IBM source and its limitations.
2. Show the repository structure and `SETUP.md`. Explain that a clone deliberately excludes source/generated data and credentials. Show the pinned Python dependencies and synthetic test command; use actual output from a completed test run.
3. Verify the member's explicitly chosen project profile with `check_aws_profile.sh PROFILE`. Keep credentials off screen. Explain the account/region guard and why a default profile is unsafe.
4. Show the immutable release manifest and on-demand deployment definitions. Explain the separated preparation/Q1/Q2/evaluator/control roles, Q2 input restrictions and no recurring schedules.
5. Explain how to inspect actual job state and costs before any run. A recorded demonstration does not require rerunning completed cloud processing. Show the private handoff, request markers and finite timeouts without publishing that file.

## End-to-end results walkthrough — suggested five minutes

1. Show actual saved orchestration history and quality reports. Explain preparation once, parallel Q1/Q2, separate evaluation, then conditional publication. State the measured scope/runtime and any failed attempt or unmet target honestly.
2. Open the dashboard locally with the verified-profile launcher (or use an already authorised private SSM session). Identify the pinned release in the header and Release & provenance page. Confirm that the Q1 date/currency population differs from a Q2 snapshot/lookback where applicable.
3. Management scenario: open Monitoring overview. Start with the volume/rate chart, explanatory monitoring lead and supported ranking; inspect a segment’s exact amount/denominator. Select a rolling or custom reporting period and one currency side. Explain transaction count, labelled count, common-population rate, supported lift and descriptive interval. Compare three genuinely supported priorities if available; otherwise show why the evidence cannot support three. Change currency side and a format filter and explain that the baseline changes consistently. Inspect the daily label-count/rate/traffic panels and volume/coverage flags. Explain the supplied dataset’s uneven late traffic as a data caveat; the reporting interface has no fixed September split. Frozen evaluation periods are still separate.
4. Investigator scenario: open Connected cases, select a daily cutoff and pattern, then pick a lead from the case queue. Explain bank/account keys, entity mappings, directed edges, timestamps, rule/window and stable source IDs. Explain early missing history, cycle degree exclusions and graph display caps. Download complete evidence and verify its source count/hash. For large cases use the CLI; no evidence is truncated.
5. Open Evaluation & coverage. Explain development versus holdout versus sparse tail, eligible annotation denominators, typed recovery, type-agnostic coverage, matched-volume and development-frozen amount baselines. State whether the frozen improvement target was met; null/unmet results are valid findings. An unannotated case is not automatically false.
6. Explain failure retention and deterministic retry: a failed gate cannot replace the prior release; corrected processing uses new immutable outputs and no blind rerun. Distinguish tested local failure injection from actual cloud observations.
7. Finish with the real cleanup record: all owned jobs/queries terminal, temporary EC2 terminated, root disk removed and no retained paid public IPv4. Retain S3/idle metadata and state residual storage costs. Do not relaunch or rerun services merely to improve the recording.

## Contribution record

Each teammate should enter their actual name, owned task, commits/PRs, tests or review evidence and recording/presentation contribution. Separate implementation, review and operation; do not attribute AI-generated work or another member's changes to a person without their confirmation. The repository does not establish human ownership automatically.

## Recording and delivery

Use the team's approved recording tool and actual observed screens. Narration may follow this guide, with final measured values read from the pinned release/operator report. Label narrated slides or edited stills as a walkthrough rather than a continuous live run. Review the finished recording for readable labels and accidental credentials before sharing. This guide is not a claim that a human user test, final presentation or narrated recording has already occurred.
