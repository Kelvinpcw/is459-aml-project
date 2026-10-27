-- Development ranking over the verified immutable Q1 output.
-- Requires the explicit Q1 table and date partition.
-- Keep dataset/run predicates even when a table points at one immutable release.
-- This example filters PAYMENT currency; use receiving_currency explicitly for the other selector.
WITH selected_population AS (
    SELECT *
    FROM is459_aml_dev.q1_daily_counts_dev20220901_v2
    WHERE dataset_version = 'ibm-hi-medium-b1b99c68b765580f'
      AND run_id = 'dev-20220901-v2'
      AND event_date BETWEEN DATE '2022-09-01' AND DATE '2022-09-01'
      AND payment_currency = 'US Dollar'
), segments AS (
    SELECT sender_bank, receiver_bank, payment_format,
           SUM(transaction_count) AS n,
           SUM(laundering_count) AS l
    FROM selected_population
    GROUP BY sender_bank, receiver_bank, payment_format
), baseline AS (
    SELECT SUM(transaction_count) AS n, SUM(laundering_count) AS l
    FROM selected_population
)
SELECT s.sender_bank, s.receiver_bank, s.payment_format, s.n, s.l,
       b.n AS baseline_n, b.l AS baseline_l,
       CAST(s.l AS DOUBLE) / NULLIF(s.n, 0) AS laundering_rate,
       (CAST(s.l AS DOUBLE) / NULLIF(s.n, 0)) /
           NULLIF(CAST(b.l AS DOUBLE) / NULLIF(b.n, 0), 0) AS risk_lift
FROM segments s CROSS JOIN baseline b
WHERE s.n >= 1000
ORDER BY risk_lift DESC, s.n DESC, s.sender_bank, s.receiver_bank, s.payment_format
LIMIT 20;
