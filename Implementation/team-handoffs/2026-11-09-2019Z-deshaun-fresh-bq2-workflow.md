# Fresh BQ2 workflow

- **Owner** Deshaun, with Codex.
- **Status** Local integration passed. AWS smoke deployment is ready for scope review.
- **AWS** None.

The fresh path cleans multiple CSVs and earlier history, detects bounded graph patterns, applies the five saved estimators, validates evidence and publishes a versioned shortlist for TRACE. Transaction IDs retain the original file checksum and row ordinal. Evaluation uses label and annotation files only when provided. [Run contract](../ml_replay/README.md#fresh-bq2-workflow)

Two synthetic batches with successive cutoffs passed through all five stages and the actual TRACE release and case readers. The fixture checked both CSVs' row-1 identities, the exclusive cutoff, labelled metrics, unlabelled publication, duplicate handling and a validation failure that retained the earlier release. Existing graph, release and workflow regression checks passed.

The proposed stack uses a new Standard workflow and scoped roles for five Glue jobs. Start one approved manual execution against a new fixture and verify the published release in a TRACE preview. The event rule starts disabled. The bounded detector is for the fresh-batch demo. The compiled Linux extractors and managed Glue execution still require verification. [AWS stack definition](../deployment/build_fresh_bq2_stack.py)
