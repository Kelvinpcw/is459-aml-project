# IS459 AML data pipeline

Shared implementation and design context for a six-person team using the synthetic IBM HI-Medium anti-money-laundering dataset.

**This is a development prototype, not a finished pipeline.** Architecture diagrams describe the target design, not proof that every service is deployed.

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

## What actually exists? — saved AWS evidence, 27 October 2026

| Component | Verified scope / remaining gap |
| --- | --- |
| Preparation | One day, **1 September 2022**: 4,465,985 accepted transactions; no quarantine |
| Q1 | Glue aggregation and Athena validation for that one day; not the full dataset or a dashboard |
| Q2 | **00:00 inclusive–00:01 exclusive** on 1 September: 43,681 transactions, 15 fan-out cases, 840 supporting transactions |
| Evaluator | Local code/tests/results exist; role and input files deployed; last checkpoint records an unsaved Glue job and no cloud evaluator run |
| Dashboard, Step Functions, shared publication | Not implemented |
| Full input | 31,898,238 transactions; not yet processed in full |

Q2's data window is **one minute, not one second**. Its recorded execution took 145 seconds. Its graph core collects at most 50,000 window rows into one process; it is not scalable full-day detection. Do not merely widen the dates or remove the guard. Independently processing non-overlapping minutes would miss patterns across boundaries.

The pilot minute contains zero positive labels and zero eligible annotated attempts. Its evaluation cannot establish useful recall/recovery. Wider-window development, calibration and frozen holdout evaluation remain necessary.

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

Kelvin's named project profile is **`IS-459-BDA`**, account **`160885259244`**, region **`us-east-1`**. His `default` profile is a different account. Teammates must independently authenticate and verify their own profile; profile names/credentials are not shared by GitHub.
