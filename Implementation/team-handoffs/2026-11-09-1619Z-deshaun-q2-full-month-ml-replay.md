# Q2 full-month ML replay and case shortlist

- **Owner** Deshaun, with Codex.
- **Review branch** [agent/codex-q2-ml-findings](https://github.com/Kelvinpcw/is459-aml-project/tree/agent/codex-q2-ml-findings).
- **Updated** 9 November 2026, 16:19 UTC.
- **Status** COMPLETED for the local analysis. Integration is proposed. AWS: none.

The full historical replay used 31,898,238 synthetic HI-Medium payments from 1–28 September 2022, including 35,230 IBM-positive payments. The 539 eligible patterns comprise fan-in, fan-out, and directed cycles of two to four accounts. Recovery requires the correct shape and at least 80% of the annotated payments in one retained snapshot. [Q2 evaluation contract](../../Proposal/Project_Proposal.md#71-business-evaluation)

| Replay | Patterns recovered | Distinct payment alerts | IBM-positive alerts | Payment precision | Payment recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Published rules archive | 539/539 | 12,329,796 | 23,671 | 0.1920% | 67.1899% |
| Original ML shortlist | 401/539 | 130,037 | 25,147 | 19.3383% | 71.3795% |
| Regroup existing alerts by case | 532/539 | 130,037 | 25,147 | 19.3383% | 71.3795% |
| Complete cases with HI-Small scores | 539/539 | 129,787 | 25,162 | 19.3871% | 71.4221% |
| **Smallest qualifying ranked list tested** | **539/539** | **130,415** | **25,252** | **19.3628%** | **71.6775%** |

1. **Regroup alerted payments.** The original daily top-2% support gate accounted for 132 of the 138 misses. Rejoin existing alerts to their matching seven-day Q2 snapshots using payment IDs and require complete directed shapes. This recovered 131 of the misses with the same payment alert list.
2. **Fill missing links.** Score supporting payments from the same snapshot with the existing model trained on HI-Small. Require a score of at least 0.85, allow up to two missing links, and propose at most four additional payments per snapshot. Use a standalone cutoff of 0.657 for the expanded shortlist and count every highlighted case payment in the payment metrics.
3. **Reduce duplicate views and rank files.** Group overlapping snapshots with the same directed shape and shared payments into 19,999 investigation files. Hiding identical or contained versions reduced 88,029 snapshots to 22,895 with the exact same payment IDs. Ranking files by their best snapshot's average case-shape and evidence-completeness scores reduced the list to 9,493 files with 12,075 retained snapshots. The ranked list used a standalone payment cutoff of 0.636 and cleared the exact floors of 19.34% precision and 71.38% recall.

The case selection logic uses payment scores, directed links and evidence available by each snapshot cutoff. Candidate identities and ranks come from the input data. The replay uses saved scores and fixed model versions, cutoffs and windows. The final ranking method, list size and cutoff were selected using this same historical month, so the results describe that replay. The separate chronological test at 50 reviews per day surfaced 249 of the 539 eligible patterns by month end. The 539/539 figure measures coverage in the searchable list.

The local replay rebuilt the retained evidence, checked all 539 typed matches, reconciled the distinct payment IDs and checked both payment floors before rounding. The first integration step is an on-demand Glue scoring job after Q2, tested against the saved release with versioned model and feature definitions. A daily queue would rank evidence available at that day's cutoff. Validate thresholds and capacity on a fresh chronological batch before promotion. [Earlier ML replay](2026-11-09-1200Z-deshaun-q2-ml-replay.md) · [Release flow](../../PIPELINE_WALKTHROUGH.md#7-publish-one-coherent-release)
