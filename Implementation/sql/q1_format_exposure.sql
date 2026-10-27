-- The broader format view retains a single explicitly selected currency population.
WITH selected_population AS (
    SELECT * FROM is459_aml_dev.q1_daily_counts_dev20220901_v2
    WHERE dataset_version = 'ibm-hi-medium-b1b99c68b765580f'
      AND run_id = 'dev-20220901-v2'
      AND event_date = DATE '2022-09-01'
      AND payment_currency = 'US Dollar'
), formats AS (
    SELECT payment_format, SUM(transaction_count) AS n, SUM(laundering_count) AS l
    FROM selected_population
    GROUP BY payment_format
), baseline AS (
    SELECT SUM(transaction_count) AS n, SUM(laundering_count) AS l
    FROM selected_population
)
SELECT f.payment_format, f.n, f.l, b.n AS baseline_n, b.l AS baseline_l,
       CAST(f.l AS DOUBLE) / NULLIF(f.n, 0) AS laundering_rate,
       (CAST(f.l AS DOUBLE) / NULLIF(f.n, 0)) /
           NULLIF(CAST(b.l AS DOUBLE) / NULLIF(b.n, 0), 0) AS risk_lift,
       CASE WHEN f.n >= 1000 THEN 'meets_demo_support' ELSE 'low_support' END AS support_status
FROM formats f CROSS JOIN baseline b
ORDER BY risk_lift DESC, f.n DESC, f.payment_format;
