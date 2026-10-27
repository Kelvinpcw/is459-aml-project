# How the AWS Data Pipeline Works

Think of **Q1 as a reporting job** and **Q2 as an investigation job**. They share the same data preparation, but perform different analyses.

**Design reference, updated 28 October 2026:** This describes the full target workflow, not a completed deployment. Preparation/Q1 are validated for one day; Q2 is validated for its first minute only. The evaluator cloud run and exact output verification are complete for that frozen first minute. Scalable wider-window detection, calibrated holdout evaluation, dashboard, shared publication and orchestration remain incomplete. See [implementation status](../../Implementation/STATUS.md) for evidence and scope. The IBM dataset is synthetic.

**Architecture diagrams:** [Simplified PDF](Simplified/AWS_Architecture_Pack.pdf) · [Detailed PDF](Detailed/AWS_Architecture_Pack.pdf)

## 1. Business Question 1: Where should we focus monitoring?

### What data does it need?

- **`HI-Medium_Trans.csv`:** Payments, banks, formats, amounts, dates and the existing `Is Laundering` label.
- **`HI-Medium_accounts.csv`:** Account/entity information for enrichment.
- **`HI-Medium_Patterns.txt` is not needed for this question.**

### How the pipeline works

#### Step 1 — Store the original files in S3

S3 holds the input files so AWS processing jobs can read them.

#### Step 2 — Glue cleans and prepares the transactions

It checks fields, normalises bank/account identifiers and joins the account information. It saves cleaned Parquet files in S3, with historical labels stored separately.

Parquet is a more efficient format for analytical processing than CSV.

#### Step 3 — A Q1 Glue job calculates exposure by segment

It joins the cleaned transactions with their labels, then groups them by:

- Payment format
- Sending-bank/receiving-bank pair
- Bank pair combined with payment format

For each group, it calculates:

- **Transaction count:** The number of transactions in the segment.
- **Laundering count:** The number of transactions with `Is Laundering = 1`.
- **Laundering rate:** Laundering count divided by transaction count.
- **Risk lift:** Segment rate divided by the overall rate for the same selected period and population.

Low-volume groups receive support warnings rather than confident rankings.

**Illustrative example — not actual project results:**

| Segment | Transactions | Labelled laundering | Rate |
| --- | ---: | ---: | ---: |
| A | 10,000 | 100 | 1% |
| B | 100,000 | 100 | 0.1% |

Both have 100 labelled transactions, but **A has higher exposure relative to its volume**. That is what a volume-only report would miss.

#### Step 4 — Store the summary tables in S3

These are much smaller than the original transaction dataset. Separate tables retain the different summary grains, counts, denominators and currency-specific totals.

The common daily count table retains **sending bank, receiving bank, format, payment currency, and receiving currency**, together with dataset/run IDs and N/L counts. Higher-level summaries are derived from those counts; overlapping summary tables are not added together.

#### Step 5 — Athena queries them, and Streamlit + Plotly displays them

Managers filter dates, banks and formats, compare volume with exposure, and identify monitoring priorities.

For a selected period, rates are recomputed from the summed counts — **not averaged across daily rates**. Transferred amounts are kept separate by currency rather than added into an unsupported cross-currency total.

The currency selector defaults to **Payment Currency** and explicitly allows switching to **Receiving Currency**. The selected filter applies to the transaction count, laundering count, support threshold, and baseline before calculating the displayed rate/lift. Storing currency-specific amount totals without currency-specific counts would not be enough.

**Q1's final result: a risk dashboard explaining where to concentrate monitoring.**

Diagram: [Simplified Q1](Simplified/02_BQ1_Monitoring.png) · [Detailed Q1](Detailed/02_BQ1_Monitoring.png)

---

## 2. Business Question 2: Which connected activity warrants investigation?

### What data does detection need?

- Cleaned transactions **without laundering labels**
- Account/entity mappings

**Patterns.txt is not an input to the detector.** It is used later for offline evaluation.

### How the pipeline works

#### Step 1 — Glue turns the transactions into an account graph

A graph is simply another way to organise the records:

- **Dot / node:** A bank/account pair.
- **Arrow / edge:** A payment between accounts.
- **Entity information:** Shows which accounts have the same owner in the supplied mapping.

The graph is built from the transaction records. It is not a separate external dataset.

#### Step 2 — Glue searches that graph for patterns

The proposed starting rules are:

- **Fan-in:** At least five different non-self senders transfer to one hub.
- **Fan-out:** One hub transfers to at least five different non-self receivers.
- **Cycles:** A closed transfer structure involving 2–4 distinct accounts.

These checks use configured time windows. Only events available at or before the snapshot cutoff enter its features.

A pattern is an investigation lead — **not proof of laundering**. Ordinary businesses can also collect and distribute payments. A structural cycle does not automatically prove that the same funds returned in chronological order.

#### Step 3 — Glue assembles cases and stores them in S3

A case contains:

- Participating accounts and entities
- The triggered rule and time window
- Supporting transactions and source IDs
- A graph bundle for display

#### Step 4 — Athena helps find cases; Streamlit + PyVis displays them

Athena filters the **case index**. The application then loads the selected case's graph and evidence **directly from S3**.

Investigators can inspect connections and export the supporting records. The browser does not need to load the entire transaction graph.

### Where does Patterns.txt enter?

**Only after cases have been generated.**

A separate Glue evaluator reads:

- **All eligible curated transaction facts**, not only transactions in detected cases
- The detected cases
- `HI-Medium_Patterns.txt`
- Historical transaction labels

The full facts supply amounts/currencies for the per-currency high-amount baseline and transaction fields/source IDs for reference matching. Labels are joined inside this separate evaluator. It compares the detected cases with eligible annotated attempts and produces evaluation metrics. Its role can read these inputs; the Q2 detector's role still cannot read labels, annotations, or evaluation artifacts.

For example: **the detector finds a cycle from the payments first; the evaluator then checks whether it matches an annotated attempt.**

Using the annotated participants or transactions to choose which cases to flag would leak the answers into detection. The annotations are also incomplete: a case missing from Patterns.txt is not automatically a false positive.

**Q2's final result: explainable connected cases, plus a separate assessment of detector performance.**

Diagram: [Simplified Q2](Simplified/03_BQ2_Investigation.png) · [Detailed Q2](Detailed/03_BQ2_Investigation.png)

---

## 3. How the Overall Pipeline Fits Together

The shared preparation happens **once**, not separately for each question.

```text
Three IBM files
      ↓
S3: original files
      ↓
Glue: clean, enrich and separate labels/references
      ↓
      ├── Q1: facts + labels
      │       → segment summaries → risk dashboard
      │
      └── Q2: label-free facts + account mappings
              → pattern detection → cases
                                      ↓
    Full eligible facts + Patterns.txt + labels → offline evaluation

Preparation / Q1 / Q2 quality reports + complete outputs + evaluation
      → shared release gate → S3 published-run manifest
      → dashboard: Athena summaries / case index + S3 case bundles
```

### Step Functions controls the sequence

1. Run preparation.
2. Wait for it to finish.
3. Run Q1 and Q2 in parallel.
4. Start and wait for the evaluator after Q2 completes, supplying cases, full eligible curated facts, labels, and annotations.
5. Require preparation/Q1/Q2 quality checks to pass, both branches' outputs to be complete, and evaluation reports to be valid before publishing. Each processing job writes its own quality report. A failed run must not replace the previous successful release.
6. Write the small published-run manifest directly to S3 with PutObject. The application pins its Athena queries and case-bundle reads to that one dataset/run. Evaluation does not retune frozen holdout rules.

This is an **on-demand batch pipeline**, not a live payment-monitoring stream. Step Functions can publish the small S3 run manifest directly; Lambda is not required for this design.

Step Functions receives **S3 locations, run IDs, and compact check summaries**, not the transaction graph or large result files. Its role needs explicit report-read and manifest-write permissions, and publication is restricted to one writer per dataset.

### Why are there several S3 and Glue boxes?

- **S3 boxes represent different stored data:** Originals, cleaned facts, references, summaries, cases and reports. They are logical storage zones, not different kinds of AWS service.
- **Glue boxes represent different jobs:** Preparation, Q1 aggregation, Q2 detection and evaluation.
- **Glue Data Catalog describes the tables and their locations.** It does not hold the transaction data.
- **Glue jobs register the explicit table schemas and run/date partitions.** A crawler is not required for these known schemas.
- **Athena runs SQL queries over the approved S3 tables.** It supplies summaries and case-index results to the application.
- **EC2 hosts Streamlit.** Plotly draws Q1's charts; PyVis draws Q2's graphs.

**Private demo access:** Session Manager port forwarding avoids public application ingress. EC2 still needs an SSM agent, suitable IAM permissions, and outbound HTTPS access to the required Systems Manager and application AWS APIs through VPC endpoints or an approved egress route. Athena query results are stored in a restricted S3 location.

Diagram: [Simplified shared pipeline](Simplified/01_Shared_AWS_Architecture.png) · [Detailed shared pipeline](Detailed/01_Shared_AWS_Architecture.png)

## The Key Distinction

**Q1 measures known historical exposure. Q2 discovers connected leads without looking at the answers, then evaluates them afterwards.**
