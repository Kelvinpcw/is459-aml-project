# IS459 final project artefacts

**TRACE | AML monitoring and connected-account investigation**

This package accompanies the final presentation. It covers BQ1 monitoring, rules-based BQ2 investigation, and the current on-demand AWS batch route that scores BQ2 cases with five saved models and publishes them to TRACE.

- [Download the source ZIP](IS459-AML-source.zip). It snapshots [the reviewed source at `ef54874`](https://github.com/Kelvinpcw/is459-aml-project/tree/ef548747df7ac1fb47da1be2faaa09c9bc1899ee), including ingestion, Spark jobs, ML training and batch scoring, Step Functions and Glue deployment code, evaluation, TRACE, and tests.
- [Download the architecture PDF](architecture/AWS_Architecture_Pack.pdf) or open the [editable Draw.io diagrams](../Proposal/Architecture/Simplified/AWS_Architecture.drawio). The pack shows the shared AWS pipeline, BQ1 monitoring, and the five-model BQ2 batch flow.
- [Training steps and fitted parameters](../Implementation/ml_replay/README.md#training-steps-and-fitted-parameters) document the training splits and frozen scoring policy. The [model manifest](../Implementation/ml_replay/model-bundle-manifest.json) identifies the exact fitted assets. The original datasets and the private fitted model bundle are supplied separately by the project owner.
- The original [shared pipeline](architecture/01_Shared_AWS_Architecture.png), [BQ1](architecture/02_BQ1_Monitoring.png), and [BQ2](architecture/03_BQ2_Investigation.png) images are retained as design references.

## Presentation materials

Use the [submission checklist](../SUBMISSION.md) for the final slides, setup and execution videos, fitted model bundle, and evaluation evidence. Add the source and video links to the presentation appendix.
