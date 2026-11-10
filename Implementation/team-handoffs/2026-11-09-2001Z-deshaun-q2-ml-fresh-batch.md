# Local Q2 ML scoring for a new prepared batch

- **Owner** Deshaun, with Codex.
- **Status** The local scoring step is implemented and tested. Workflow integration and cloud validation are pending.
- **AWS** None.

The local scorer consumes the prepared label-free facts and the case index from the same completed detection run. It uses the detector's dates, reconstructs the full case projection, keeps the training category codes, and reuses the five frozen models and shortlist policy. It emits ranked cases, alerts and original case evidence locators with input and model hashes. Scope is one complete prepared transaction corpus. [Input contract and command](../ml_replay/README.md#local-scoring-for-a-new-prepared-batch)

A synthetic three-day October 2024 corpus exercised 21 payments and eight graph snapshots with the saved models and policy. It produced one investigation and six unique alerts. Selected evidence resolved to the fixture's original transaction IDs. Mismatched run identity, a future payment in an earlier partition and a label column each failed before output. A case-free batch produced valid empty case and evidence tables. Thirty-eight existing workflow, release and graph-rule tests passed locally.

Next, package the scorer for Glue and pass the just-completed detector manifest and report from Step Functions. Gate release publication on the matching ML manifest and evidence. Verify a new batch reaches TRACE before scheduling or describing it as automated. GitHub sync is pending an explicit commit request.
