# Completion review and six-member presentation plan

Reviewed 1 November 2026 (Singapore). Cleanup is excluded from this plan at the
user's request. These are proposed presentation/delivery responsibilities, not
claims about who originally implemented the system. Replace Member 1–6 with names
after the team agrees; record each person's actual contribution separately.

## Completion verdict

**The core batch pipeline is complete. Final submission readiness is not yet
established.** The remaining work is chiefly presentation, recording, evidence
selection and submission, rather than another pipeline implementation or run.

The [30 October full-run handoff](team-handoffs/2026-10-30-kelvin-full-pipeline.md)
records one successful execution through preparation, manifest creation, parallel
Q1/Q2, Catalog, evaluation and publication, with independent report/hash/population
checks. The [public dashboard handoff](team-handoffs/2026-10-30-kelvin-public-dashboard.md)
and [latest BQ1 update](team-handoffs/2026-10-30-1357Z-codex-bq1-live-update.md)
record deployed visualization and browser verification. This review examined
source and saved evidence; it did not freshly inspect AWS or the live dashboard.

GitHub's main commit and the local reviewed HEAD both resolved to
`0fa107f45f07ca8967426dbce093b93f9ceb67aa`. The only open PR when reviewed was
[#23](https://github.com/Kelvinpcw/is459-aml-project/pull/23), concerning Git repair
documentation, with no additional pipeline or submission artifacts. A local fetch
failed on a malformed Finder metadata reference; GitHub API verification and a
clean isolated clone established current shared source without repairing or
changing the original checkout.

## What is done, and what remains

| Item | Evidence-based status | Remaining action |
| --- | --- | --- |
| Two distinct business questions, beneficiaries and dataset | Documented in the [proposal](../Proposal/Project_Proposal.md) | Condense into the opening slides and connect the results to decisions. |
| Ingestion, preparation and full-data processing | Completed in the dated full-run evidence | Select readable existing inputs, schema and quality evidence for the demo. |
| Q1 summaries and monitoring visualization | Implemented, deployed and browser-verified in the dated records | Prepare supported monitoring findings with their selected date/currency population. |
| Distributed Q2, case graph and complete evidence | Completed batch path and verified dashboard | Choose a fan case and a short-cycle case from the same published release; rehearse evidence retrieval. |
| Separate evaluation and baseline comparison | Implemented and completed | Read final figures from the chosen release, explain denominators and limitations. |
| Orchestration, Catalog/Athena access and conditional publication | Implemented and completed | Show the successful history and explain failure retention and release pinning. |
| Architecture diagrams | Existing detailed/simplified packs | Reconcile the final slide diagram with the actual control job and public dashboard access. |
| Source code, setup and run documentation | Present in GitHub | Select a stable submission commit and test that the submitted links open. |
| Week 9 proposal slide submission | A written proposal and diagrams exist; submission not established | Confirm the submitted proposal deck/eLearn record with the team. Do not infer submission from source files. |
| Final presentation slides in PDF/PPTX | No finished final deck found in the reviewed workspace/shared tree | Assemble and export the final deck. A written proposal and architecture pack are not the final deck. |
| Setup video and run video | Guidance exists; finished clips/YouTube links not found | Record or assemble both required coverage areas with narration or annotations; upload and check playback. |
| Individual contribution slide | Requirement documented; completed named slide not found | Each member confirms actual work and evidence. Presentation assignments do not establish past authorship. |
| Six-member demo and Q&A rehearsal | No completed rehearsal evidence found | Every member speaks and operates or narrates a concrete component demo. |
| eLearn submission and appendix links | Not verified | Upload artifacts before the Week 13 lesson and verify receipts/access. |
| Proposed user scenarios and UI latency targets | Browser checks exist; formal scenario outcomes and initial/cached timings not established | Record the two scenarios and timings, or explicitly label those targets unverified. |

“Not found/not verified” leaves room for materials held elsewhere by teammates.
There is no evidence here that a finished artifact was submitted merely because
instructions for producing it exist.

Scheduled/incremental ingestion, streaming, extra ML, Neptune and additional
datasets are not needed to finish the agreed on-demand batch project. Do not
create new infrastructure to fill presentation time. The brief does not separately
require a written final report; add one only if later instructor guidance does.

## Course requirements checked

The local instructor deck, `[IS459] Project_G2.pptx`, was read directly. It is not
copied into this public plan. Relevant slide numbers:

- Slides 2 and 7: proposal 5%, final presentation 15%, final artifacts 15%.
- Slide 7: final slides in PDF/PPTX, video coverage of end-to-end setup and
  end-to-end execution with narration or annotations, YouTube video links in the
  slide appendix, and source code/other artifact access. Upload to eLearn and
  include the required links/info before the Week 13 lesson.
- Slide 9: the 20-minute slot is **15 minutes presentation/demo plus 5 minutes
  Q&A**. Include business questions, audience/objective, architecture,
  tools/packages/libraries, and an individual contribution slide. Every member
  must present/demo at least one component/feature and be ready for Q&A. All
  members must be present on time. Recorded clips with live narration are allowed.
- Slides 10–14: explain business value as well as correct, usable implementation.
  A meaningful X-factor is needed to qualify for the top presentation band.

The actual Week 13 calendar date was not established. Follow the class timetable
and any newer instructor announcement rather than inventing a date.

## Six parts, each with a component and demonstration

Each person prepares their own slide content, narration, demo segment and answers.
The artifact owner below assembles that deliverable from everyone's contributions.
No person is assigned only introduction, slide formatting or conclusion.

| Member / time | Component and explanation | Required demonstration | Final artifact responsibility |
| --- | --- | --- | --- |
| **1 — 0:00–2:00** | **Data ingestion and S3.** Briefly introduce the two business decisions, synthetic IBM inputs and why batch processing fits. Explain original-file checksum plus record ordinal, manifests and storage zones. | Show an existing ingestion manifest and stored input layout. Trace one source ID back to its original record identity and distinguish transactions, account mappings and annotations. | Assemble the **setup video** from all members' setup segments; own opening/business-context slides and source citations. |
| **2 — 2:00–4:30** | **Glue/Spark preparation and data quality.** Explain repeated Account headers, bank+account joins, exact decimal money, Parquet/date partitions and label separation. | Show the saved preparation quality report, input/accepted/quarantine reconciliation and curated schema. Demonstrate the label-free fact contract beside the separate label output. | Assemble the **source/reproducibility package**: stable code link, dependencies, setup/run guide and relevant test evidence; own preparation slides. |
| **3 — 4:30–7:00** | **Q1 analytics and Monitoring.** Explain additive counts, rate, matched-population baseline/lift, support and currency scope. | Change reporting dates and currency, compare payment-type traffic share with labelled share/rate, then inspect a supported bank or route. Explain why the result changes monitoring priorities. | Assemble the **final PDF/PPTX deck** from all members' sections; own Q1 findings and figures. |
| **4 — 7:00–10:00** | **Distributed Q2 and case exploration.** Explain fan aggregation, bounded 2–4-account cycle joins and overlapping seven-day snapshots without labels. | Select a fan case and briefly contrast a cycle, inspect account/entity details and rule/window, then retrieve complete evidence. Explain graph display caps versus complete stored evidence. | Assemble the **end-to-end run video** from all stage clips; own Q2 slides and the investigation scenario. |
| **5 — 10:00–12:30** | **Separate evaluation and validation.** Explain frozen development/holdout/tail periods, eligible populations, precision/recall, typed recovery and amount baselines. | Open Evaluation & coverage for the selected release and compare detector/baseline results. Point to actual denominators and explain why pattern recovery is different from transaction precision. | Assemble the **results/limitations evidence sheet**; collect actual user-scenario/latency observations or label them unverified; own evaluation slides. |
| **6 — 12:30–15:00** | **Step Functions, publication and serving.** Explain parallel Q1/Q2, stage gates, Catalog/Athena, EC2/Streamlit and a single pinned release. | Open the completed execution history, show the parallel branches and publication gate, then identify the matching release in Release & provenance. Demonstrate failure retention using an existing local synthetic test or clearly labelled saved test clip. | Own the **final appendix and submission checklist**, gather confirmed contribution entries from all six members, check YouTube/GitHub links, and coordinate eLearn submission/rehearsal. |

These timings include slide transitions and demo clips; Q&A starts at 15:00.
Use roughly two main slides per person, with concise contribution and appendix
material as needed. Rehearse to the clock rather than adding slides for their own
sake. If the presentation overruns, shorten explanations and preselect views.

Member 1's ingestion feature and Member 2's preparation feature must be shown as
actual artifact/console/schema demonstrations, not merely architecture boxes.
Member 6 must show the orchestration/publication feature, not only a conclusion.
This ensures that all six visibly meet the component/demo requirement.

## Recording, demo and evidence rules

1. Use one coherent completed release throughout the main results story. Display
   its identity and selected population. Do not mix one-day/minute pilot metrics
   with the completed full-data release or use the offline `Visulization/` fixtures.
2. Setup coverage must explain how the pipeline is configured from source through
   storage, job roles/dependencies, processing/orchestration, Catalog and dashboard
   serving. Execution coverage must show the ordered stages, completion evidence,
   evaluation, publication and resulting insights. Everyone supplies their stage.
3. Prefer two clearly named videos, **Setup** and **Execution**, so the two required
   coverage areas are easy to assess. Use concise excerpts during the 15-minute
   presentation and place full YouTube links in the appendix. Check instructor
   sharing requirements and actual viewer access; keep local backup clips.
4. Use existing completed histories/output artifacts and permitted recorded clips.
   Do not rerun paid processing just to create footage. If a walkthrough uses
   edited history or stills, label it accurately; it is not a continuous live run.
5. Keep credentials, private operational records, signed URLs and raw operator
   details off screen. Use selected, sanitised evidence rather than filming a
   private checkpoint. Publishing videos is a separate team action, not performed
   by this review.
6. Choose cases and filters before rehearsal. Prepare readable backup clips for
   the dashboard and the stage demonstrations. No current endpoint availability
   or console access is guaranteed by historical evidence.

## Presentation corrections and acceptance checks

- The current dashboard is payment-type first, then banks/routes. It defaults to
  All currencies with one payment-currency filter. All-currency views omit money
  totals. Older demo instructions referring to a currency-side selector need
  adapting when recording.
- Actual publication uses the separately permissioned **Control Glue job** under
  Step Functions, including physical output checks and a conditional pointer
  update. Some original proposal text describes direct Step Functions S3
  publication; use the implemented path in final slides.
- Distinguish the earlier private SSM dashboard design from the later explicitly
  authorised public HTTP dashboard. Present the actual demo arrangement; do not
  imply that public HTTP provides production authentication or HTTPS.
- State the actual tools/libraries used in the chosen code, including Spark,
  Streamlit and the chart/graph layer, rather than treating all proposal options
  as deployed services.
- Show the useful X-factor: parallel orchestration and publication safety, plus
  interactive evidence-linked investigation. Explain the benefit; service count
  alone is not the contribution.
- Q1 acceptance: a presenter/user explains three supported monitoring priorities
  using volume, rate and baseline, if the selected population supports three.
  Record an honest limitation otherwise.
- Q2 acceptance: a presenter/user explains a case and retrieves its complete
  evidence without SQL. Do not claim real bank-user interviews or formal user
  testing from team demonstrations.
- If claiming the proposed initial-summary/cached interaction targets, measure
  actual initial/cached and case-load times and state conditions. There is no
  fixed batch-runtime pass/fail target. Record operational observations only where
  they are available and approved for sharing.
- Prepare Q&A on distributed scale, batch choice, label separation, currency
  handling, graph bounds, evaluation denominators, low precision, failure
  retention and how each result supports its business question. All six rehearse.

## Final submission checklist

- [ ] Confirm the Week 9 proposal submission record and Week 13 lesson deadline.
- [ ] Agree named owners for the six parts; verify actual contributions separately.
- [ ] Final architecture, business questions, audience/objective and tool list agree
      with the deployed implementation and chosen release.
- [ ] Each member's feature demonstration works and has a usable backup.
- [ ] Final slides exported to PDF/PPTX with a confirmed contribution slide.
- [ ] Narrated/annotated end-to-end setup and execution coverage uploaded to YouTube.
- [ ] Appendix contains working video, source-code and supporting artifact links.
- [ ] Source/reproducibility package and chosen commit are accessible to assessors.
- [ ] Findings show actual populations, denominators, baselines and limitations.
- [ ] Fifteen-minute group rehearsal completed; all six ready for five-minute Q&A.
- [ ] eLearn artifacts/links submitted before the Week 13 lesson; receipts checked.

AWS: none for this review. No processing, queries, deployments or cleanup were
performed. Application tests were not rerun for this documentation-only review.
