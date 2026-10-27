# Project checkpoint

The user requested that new AWS operational records remain local while source is published to the project PR.

**On the operator's machine, resume from `Implementation/data/aws-operations-20261028/PROJECT_CHECKPOINT.md`.** That ignored file contains the latest execution, costs, output identities, approval and cleanup state. Also read the ignored `Implementation/aws/reviews/full-monitor-latest.json` and local resource ledger beside the detailed checkpoint before any cloud action. Do not infer live state from this public source checkout or restart processing from a historical command.

This branch implements publication, the dashboard, distributed detection/evaluation, on-demand workflow and diagnosed recovery. The recovery passed68synthetic tests; frozen full-v1 and full-v2 payloads are preserved. Source and setup: [README](README.md), [status](Implementation/STATUS.md), [runbook](Implementation/RUNBOOK.md). Actual new cloud results and the private handoff are deliberately excluded from Git by the user's instruction.

A fresh clone has no source data, credentials or private operational checkpoint. Each member must authenticate to the intended project account using their own explicitly chosen profile, agree an authorised scope/budget, and inspect actual cloud state before acting. Existing tracked AWS records are historical and do not establish current state or authorisation.
