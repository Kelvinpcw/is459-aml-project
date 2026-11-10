# Current architecture and ML training notes for submission

- **Owner** Deshaun with Codex
- **Branch** `agent/codex-architecture-submission`
- **Status** COMPLETED

The approved [presentation PDF](../../Proposal/Architecture/Simplified/AWS_Architecture_Pack.pdf) and [editable diagrams](../../Proposal/Architecture/Simplified/AWS_Architecture.drawio) show the current on-demand BQ2 workflow and five-model scoring stage. The existing BQ1 page and architecture PNGs are preserved. The original design pack and historical replay diagram remain available for context.

The [training guide](../ml_replay/README.md#training-steps-and-fitted-parameters) records the dataset splits, fitted settings checked against the approved bundle, and the frozen ranking policy. It distinguishes the historical policy replay from the earlier chronological holdout. The [submission index](../../SUBMISSION.md) links the current documents.

AWS changes: none. Read-only AWS checks confirmed the live workflow stages, model bundle digest, release pointer, and disabled triggers. The PDF and editable sources were checked locally. The separate submission packaging PR retains its own copy of the architecture.
