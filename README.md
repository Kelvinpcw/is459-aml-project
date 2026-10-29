# IS459 AML project — team workspace

**Start with [TEAM_START_HERE.md](TEAM_START_HERE.md).** It explains what to install, how to run the dashboard or tests, and what to paste into your AI assistant.

This repository is the team's shared source and handoff record. **GitHub updates when someone commits and pushes.** Local edits, AWS console changes and AI chat history are not automatically synchronised. Pull requests show work not yet merged; `main` contains merged work. Contributors can merge their own PRs after checks; a separate reviewer is optional.

## What the project does

Using the synthetic IBM HI-Medium dataset, the pipeline answers two questions:

- **Q1 — monitoring allocation:** Which payment formats and bank-pair segments have disproportionate historical labelled exposure after accounting for volume?
- **Q2 — connected investigation:** Which groups show fan-in, fan-out or bounded cycles that warrant investigation, with retrievable transaction evidence?

```text
S3 inputs → preparation → Q1 summaries + label-free Q2 cases
    → separate evaluation → validated published release → TRACE dashboard
```

The software path is implemented. Scheduled/incremental daily ingestion is not implemented. Code, local tests and actual cloud observations are different evidence; use the guides below before claiming that something ran or remains running.

Start with the [plain-language walkthrough](PIPELINE_WALKTHROUGH.md), then practise using [Q&A](Q_AND_A.md). No assigned task or formal role is needed to explore the project.

## Find what you need

| Need | Read |
| --- | --- |
| Join the team / use an AI agent | [Start here](TEAM_START_HERE.md) |
| Pick up work, push changes and hand over | [Contribution workflow](CONTRIBUTING.md) |
| Understand the full pipeline / prepare for questions | [Walkthrough](PIPELINE_WALKTHROUGH.md), [Q&A](Q_AND_A.md) |
| Understand current implementation | [Status](Implementation/STATUS.md) |
| Check what actually exists or ran | [Verify progress](Implementation/VERIFY_PROGRESS.md), [handoffs](Implementation/team-handoffs/README.md), [open PRs](https://github.com/Kelvinpcw/is459-aml-project/pulls) |
| Install dependencies / run locally | [Setup](Implementation/SETUP.md) |
| View published results / operate an approved task | [Runbook](Implementation/RUNBOOK.md) |
| Requirements and architecture | [Business questions](Proposal/Project_Proposal.md), [pipeline explanation](Proposal/Architecture/Pipeline_Explanation.md) |
| Authorised AWS work and cleanup | [AWS handoff](Implementation/AWS_HANDOFF.md), [teardown](Implementation/TEARDOWN.md) |
| Detailed private operator evidence | [Checkpoint pointer](PROJECT_CHECKPOINT.md) |

## Where files belong

| Folder | Purpose |
| --- | --- |
| `Implementation/jobs/` | Editable processing/detection/evaluation code |
| `Implementation/dashboard/` | Connected TRACE Streamlit dashboard; published results |
| `Implementation/scripts/`, `sql/`, `tests/` | Local helpers, analytical queries and synthetic tests |
| `Implementation/deployment/` | Explicit on-demand deployment tools; never run just to onboard |
| `Implementation/team-handoffs/` | Short, public-safe changes, checks, blockers and next steps |
| `Implementation/releases/` | Frozen packages; preserve unchanged |
| `Implementation/results/`, `evidence/`, `aws/` | Scoped historical validation/configuration; not a live account inventory |
| `Implementation/archive/` | Older plans and deployment/recovery instructions |
| `Proposal/` | Requirements and architecture diagrams/source |
| `Visulization/` | Independent offline TRACE concept with invented fixtures |

Original datasets, generated data, credentials and detailed operational records are deliberately absent from a fresh clone. The [offline concept](Visulization/README.md) works without AWS; the connected dashboard requires each member's own authorised login and can make chargeable reads. Merging code does not deploy it to AWS or restart a teammate's dashboard.

AI assistants must read [AGENTS.md](AGENTS.md). Work on a task branch, stage explicit paths, push and open a PR; contributors may self-merge after checks and checking for overlapping work. Never use another member's credentials or silently resume a historical cloud run.
