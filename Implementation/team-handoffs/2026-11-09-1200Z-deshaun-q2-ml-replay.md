# Q2 ML replay findings and proposed TRACE workflow

- **Owner** Deshaun, with Codex.
- **Review branch** `agent/codex-q2-ml-findings`.
- **Updated** 9 November 2026, 12:00 UTC.
- **Status** COMPLETED for the local replay and evidence checks. TRACE integration is proposed.
- **Scope** Q2 case prioritization and payment screening on the published full HI-Medium synthetic dataset. `AWS: none` for this experiment and handoff.

## Results on the 9–16 September 2022 holdout

The proposed workflow keeps Q2's connected cases searchable, ranks the first 50 case reviews per day, and screens individual payments with a separate score. The local replay preserved all **122 eligible IBM patterns** while reducing alerts on IBM-zero payments by **98.98%** relative to published Q2.

| Policy | Unique alerted payments | IBM-positive alerts | IBM-zero alerts | Payment precision | Payment recall | Eligible patterns recovered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Published Q2 rules | 5,891,196 | 11,626 | 5,879,570 | 0.197% | 65.94% | 122/122 |
| First ML pilot with graph score cutoff | 74,767 | 12,666 | 62,101 | 16.94% | 71.84% | 122/122 |
| Proposed shortlist and blended payment cutoff | **72,442** | **12,688** | **59,754** | **17.51%** | **71.96%** | **122/122** |

Payment precision is the share of alerts with an IBM-positive payment label. Payment recall uses all **17,632** IBM-positive payments in the holdout as its denominator. Pattern recovery requires the correct fan hub or directed cycle and at least **80%** of an attempt's annotated payments in a single retained case. The 122 comprise 42 fan-in, 24 fan-out, 39 two-account cycles, 11 three-account cycles, and six four-account cycles. [Q2 benchmark definition](../../Proposal/Project_Proposal.md#71-business-evaluation)

### Case review workload

| Policy at 50 case reviews per day | Total review slots | Patterns surfaced | Distinct payments shown | IBM-positive payments shown |
| --- | ---: | ---: | ---: | ---: |
| Rules ranking | 400 | 11 | 3,951 | 423 |
| First ML pilot | 400 | 15 | 2,649 | 2,382 |
| Proposed case ranking | 400 | **27** | **2,026** | 1,873 |

The proposed queue surfaces more complete patterns than the first ML queue while showing fewer payments. Its lower count of IBM-positive payments reflects that trade-off. The searchable archive preserves all 122 patterns. Grouping case versions by investigation and hiding duplicates or versions contained in another version reduced the completed archive from **12,087 to 4,203 visible snapshots**. The original versions remain available for evidence lookup.

## Tested policy

1. **Score payments at the daily cutoff.** Fit two scikit-learn histogram gradient boosting models on 1–5 September. Both use all 7,172 IBM-positive training payments and 600,000 sampled IBM-zero training payments, with sample weights of 3 and 1 respectively and random seed 459. Use amounts, currencies, payment format, account activity and counterparty history. The graph model also uses same-day Q2 graph features available at the daily cutoff. The history model computes rolling activity using events strictly before the payment minute. Use IBM labels as training targets and evaluation data. [IBM graph feature research](https://research.ibm.com/publications/graph-feature-preprocessor-real-time-subgraph-based-feature-extraction-for-financial-crime-detection)
2. **Build the connected shortlist.** Use the graph model to rank payments within each day. Two payments in the top **0.25%** in an existing Q2 case can activate related evidence from the top **2%**. Retain highlighted case evidence available by the case cutoff when it still forms a fan with at least five distinct counterparties or contains every leg of the original two- to four-account directed cycle. For identical highlighted evidence within an investigation, keep the earliest snapshot visible. In the completed archive, hide a snapshot only if one other snapshot of the same investigation contains all its highlighted payments.
3. **Rank the daily queue.** Fit two histogram gradient boosting models on development snapshots through 6 September. The first scores how much a case resembles the known graph patterns. The second scores the completeness of the highlighted evidence using distinct links, timing and growth across snapshots. Take the geometric mean of the two scores. Reserve up to five of 50 slots for each available motif type and fill unused slots by rank. Keep eligible snapshots in the backlog. Review an investigation again when its snapshot contains highlighted payments the reviewer has yet to see. Select the queue policy using 7–8 September.
4. **Screen individual payments.** Average the graph and account history model scores with equal weights. Alert at a mean score of **0.6400573253631592** or higher for the fitted pilot models. This cutoff matched the previous pilot's count of IBM-positive alerts on 8 September. Count each source payment ID once across both screens. The more complex stacked models produced 153,585–190,218 holdout alerts at their calibrated cutoffs, compared with 72,442 for the equal-weight blend.


The pilot used scikit-learn 1.7.1 with `HistGradientBoostingClassifier` and early stopping disabled.

| Model | Iterations | Learning rate | Maximum leaves | Maximum depth | Minimum samples per leaf | L2 regularization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Payment graph | 115 | 0.09 | 31 | 6 | 35 | 1.5 |
| Payment history | 150 | 0.075 | 31 | 7 | 30 | 1.5 |
| Case and evidence progress | 85 each | 0.065 | 12 | 4 | 12 | 4.0 |

Calibrate the payment cutoff again after retraining, since the score scale can change.

## Dates, evidence and next step

The local models scored all **31,898,238** cleaned payments dated **1–28 September**. The final snapshot closes at **00:00 on 29 September**. Development and calibration use **1–8 September**. The main test uses all **15,025,129** payments on **9–16 September**. The separate 17–28 September test contains 6,987 payments, of which 4,084 carry IBM-positive labels. The blend caught 4,003 of those. The 35 annotated attempts wholly within the late period are bipartite or stack patterns. The current Q2 benchmark counts fan-in, fan-out and bounded cycles contained within the evaluation period, so the late period has zero eligible attempts. The date split tests the model in the order that TRACE would receive the payments. [IBM temporal benchmark](https://arxiv.org/html/2306.16424v3#S4)

The local replay reproduced the published Q2 baseline and rechecked the original case bundles for all 122 recovered attempts. Readback of the local pilot tables confirmed the alert totals, 50 reviews per day, and joins back to case and payment evidence. The 9–16 September benchmark has been reused across experiments, and the payment blend was chosen after comparing those results. Treat the figures as a retrospective comparison.

Connect the local pilot outputs to **Review First**, the searchable **Connected cases** archive, and a separate **Payment Alerts** view. Run ML as a separate consumer of the published Q2 evidence. Pin its case and payment tables to a release and model version, join evidence by source payment ID, and restrict IBM labels and annotations to training and evaluation. Use **122/122** recovery as a regression check and validate the selected policy on a fresh chronological batch at the same review budget before considering release. [Dashboard implementation](../dashboard/app.py) · [Publication and data contracts](../../AGENTS.md)
