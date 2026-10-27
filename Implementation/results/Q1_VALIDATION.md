# Q1 development validation — 1 September 2022

The saved Glue Q1 summaries are now registered in Athena and checked against the retained source input. This is the one-day development slice, not the full dataset, holdout result or complete dashboard.

## Population and precision

- All 4,465,985 transactions and 1,056 positive historical labels reconcile across all seven payment formats.
- Athena read 1,628,879 daily summary rows. Both amount columns read as decimal(38,8); no invalid count rows or missing amount totals. Fractional Bitcoin amounts remain represented.
- No cross-currency amount totals are combined.

## USD payment-currency population

USD baseline: 1,634,628 transactions, 382 positive labels; historical rate 0.02337%.

| Payment format | Transactions | Positive labels | Rate | Lift vs USD baseline | Support |
| --- | ---: | ---: | ---: | ---: | --- |
| ACH | 134,032 | 259 | 0.19324% | 8.269 | meets_demo_support |
| Cash | 99,382 | 24 | 0.02415% | 1.033 | meets_demo_support |
| Cheque | 378,885 | 60 | 0.01584% | 0.678 | meets_demo_support |
| Credit Card | 251,232 | 39 | 0.01552% | 0.664 | meets_demo_support |
| Reinvestment | 733,158 | 0 | 0.00000% | 0.000 | meets_demo_support |
| Wire | 37,927 | 0 | 0.00000% | 0.000 | meets_demo_support |
| Bitcoin | 12 | 0 | 0.00000% | 0.000 | low_support |

Counts, rates, lifts and support flags all match an independent streaming scan of the checksum-verified selected source file. ACH has the highest observed USD format exposure in this slice. These are descriptions of synthetic historical labels.

## Bank-pair support limitation

With the current demonstration minimum of 1,000 transactions, 57 bank-pair/format segments qualify, and they contain 0 positive labels. The top-20 query therefore returns zero observed lift for all displayed segments. This is not a meaningful positive-exposure priority list and must not be presented as one.

Keep support visible. Use the broader format view for this one-day demonstration; calibrate bank-pair support on the planned development period before the holdout. The SQL threshold was not lowered to manufacture a positive ranking. The USD Bitcoin format has only 12 transactions and is correctly flagged low_support.

## Execution and cost

Workgroup is459-aml-dev, Athena engine 3, enforced private SSE-S3 result output, 50 MB per-query cutoff, result reuse disabled for validation. Three metadata statements succeeded; one initial ordering expression was rejected before scanning; three corrected/read-only validation queries succeeded. Displayed scanned data: 26.36 MB, 11.14 MB and 3.56 MB. Applying the per-query billing minimum, the estimated scan charges remain below US$0.001 at the checked [US$5/TB example rate](https://aws.amazon.com/athena/pricing/); S3/logging charges are separate. No Glue job was rerun.

All query IDs, SQL and observed statuses are in ../aws/reviews/athena-query-executions-20261026.json. No query remains running.
