# IS459 AML data pipeline

Shared implementation and design context for a six-person team using the synthetic IBM HI-Medium anti-money-laundering dataset.

**Full-data validation is in progress.** The complete implementation is on `codex/project-completion`; the approved on-demand AWS workflow is running. Architecture diagrams describe the design; the checkpoint and dated validation records identify what has actually passed.

## Start here — humans and AI assistants

| Read | Purpose |
| --- | --- |
| [AGENTS.md](AGENTS.md) | AI working rules: safety, data contracts, testing and collaboration |
| [Implementation/STATUS.md](Implementation/STATUS.md) | Current implementation scope and remaining work |
| [Implementation/SETUP.md](Implementation/SETUP.md) | Local setup, data access and AWS profile checks |
| [Confirmed proposal](Proposal/Project_Proposal.md) | Business questions, requirements, analysis rules and evaluation protocol |
| [Pipeline explanation](Proposal/Architecture/Pipeline_Explanation.md) | How the target components connect |
| [Detailed architecture](Proposal/Architecture/Detailed/AWS_Architecture_Pack.pdf) | Technical diagrams; editable source is in the same folder |
| [PROJECT_CHECKPOINT.md](PROJECT_CHECKPOINT.md) | Historical deployment handoff, exact resource IDs and evidence |

The newest scoped evidence wins over older status sentences. Read the checkpoint when resuming deployment, but **reading it is not an instruction to resume paid work**.

## What are we building?

- **Q1 — monitoring allocation:** Which payment formats and bank-pair segments have unusually high historical labelled laundering exposure relative to transaction volume?
- **Q2 — connected investigation:** Which account groups exhibit fan-in, fan-out or bounded cycles worth investigating? Generate leads without reading labels or pattern annotations.

Target workflow:

```text
S3 inputs → Glue preparation → label-free enriched facts
                                 ├─ Q1 + separate labels → risk summaries
                                 └─ Q2 without labels → cases + evidence
                                                          ↓
                         facts + cases + labels/annotations → evaluator

Complete outputs + quality reports + evaluation → shared release gate
    → one published-run manifest → dashboard using Athena + S3 case bundles

Step Functions coordinates the target workflow; EC2 hosts the target dashboard.
```

## Current evidence — 28 October 2026

| Component | Observed scope / remaining validation |
| --- | --- |
| Full preparation | **PASSED**: all 31,898,238 transactions and 35,230 positive labels reconciled; no quarantine or unmatched account joins |
| Full Q1 / distributed Q2 | Running in parallel in the approved workflow; full outputs and evaluation are pending |
| Evaluator | Frozen first-minute pilot succeeded; zero positives/eligible annotations in that pilot. New development, holdout and sparse-tail evaluation is pending |
| Publication | Pilot release published through the tested gate; full release replaces it only after every quality check passes |
| Dashboard | Implemented and locally tested against the live pilot; temporary private EC2 validation is pending |
| Orchestration | Dedicated on-demand Step Functions workflow deployed and running; no recurring schedule |

The full implementation uses distributed fan aggregation and bounded, degree-eligible 2–4-cycle joins over overlapping seven-day daily snapshots. The frozen first-minute detector remains unchanged and is not the full-data implementation. Complete case evidence is retained beyond display caps. See [runbook](Implementation/RUNBOOK.md) and [checkpoint](PROJECT_CHECKPOINT.md).

The user's latest total ceiling is **US$30**, including prior development charges and final validation. Estimates and timeouts are not a hard billing cap. Expensive project compute is removed/stopped after validation; retained S3 storage still has a cost.

## Code map

| Location | Contents |
| --- | --- |
| `Implementation/jobs/` | Editable preparation, Q1, Q2 and evaluator source |
| `Implementation/scripts/` | Input builders, manifest helpers, audits and verifiers |
| `Implementation/sql/` | Athena schemas, validation and analytical queries |
| `Implementation/tests/` | Local synthetic regression tests, including Spark tests |
| `Implementation/releases/` | Frozen code used/reviewed for specific cloud attempts; preserve unchanged |
| `Implementation/aws/` | Resource configuration, manifests, run records and review evidence |
| `Implementation/results/` | Human-readable validation findings and limitations |
| `Implementation/evidence/` | Retained console screenshots; historical, not a live inventory |
| `Proposal/` | Confirmed requirements and target architecture, not old question-selection drafts |

## Working together

Use one feature branch per task and a pull request reviewed by a teammate. A Git branch **does not isolate AWS**: use distinct development jobs/script paths/output namespaces when cloud testing is authorised. Never overwrite another person's run.

Suggested workstreams (assign actual owners as a team):

1. Ingestion/preparation and wider input scope.
2. Q1 multi-day analytics and dashboard query contracts.
3. Scalable Q2 fan-in/fan-out.
4. Scalable bounded cycles and shared case/evidence contracts.
5. Dashboard and graph explorer.
6. Evaluation/orchestration/release integration, supported by component owners.

```bash
git pull --ff-only
git switch -c feature/your-task
# Edit and test locally, then stage only your task's files.
git add path/to/your/files
git commit -m "Describe your change"
git push -u origin feature/your-task
```

Include changed contracts, tests actually run, and any AWS effects/costs in the pull request. Record the deployed Git commit and job arguments when deploying. Review schema changes with downstream owners before merging.

## Give your AI assistant this starting prompt

> Read AGENTS.md, README.md and Implementation/STATUS.md, then the files relevant to my task. My assigned task is: [describe it]. Distinguish the target architecture from the current prototype. Start with local work; do not run, deploy, change IAM, overwrite outputs or delete AWS resources unless I explicitly request that scoped action. Explain missing data or blockers instead of inventing results. Use a feature branch and report the tests you actually run.

AI tools that do not automatically load `AGENTS.md` should be explicitly asked to read it.

## Data and credentials

The large source dataset and generated `Implementation/data/` artifacts are intentionally not in Git. Cloning does not download them. See [SETUP.md](Implementation/SETUP.md) before requesting data or attempting a replay. Never commit credentials, signed S3 URLs or environment secrets; this repository is public.

The shared project account is **`160885259244`**, Region **`us-east-1`**. Each member must independently authenticate and verify their own AWS console login or CLI profile. Local profile names and credentials are not shared by GitHub; do not assume your default account is correct.
