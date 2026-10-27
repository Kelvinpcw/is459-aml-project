-- Validate saved Q1 Parquet through Athena; no cross-currency amount summation.
SELECT COALESCE(payment_format, 'ALL') AS payment_format,
       COUNT(*) AS summary_rows,
       SUM(transaction_count) AS n,
       SUM(laundering_count) AS l,
       COUNT_IF(transaction_count <= 0 OR laundering_count < 0 OR
                laundering_count > transaction_count) AS invalid_count_rows,
       COUNT_IF(amount_paid_total IS NULL OR amount_received_total IS NULL) AS missing_amount_rows,
       MIN(typeof(amount_paid_total)) AS paid_type,
       MIN(typeof(amount_received_total)) AS received_type,
       COUNT_IF(payment_currency = 'Bitcoin' AND
                amount_paid_total <> ROUND(amount_paid_total, 2)) AS fractional_bitcoin_groups
FROM is459_aml_dev.q1_daily_counts_dev20220901_v2
WHERE dataset_version = 'ibm-hi-medium-b1b99c68b765580f'
  AND run_id = 'dev-20220901-v2'
  AND event_date = DATE '2022-09-01'
GROUP BY ROLLUP(payment_format)
ORDER BY payment_format;
