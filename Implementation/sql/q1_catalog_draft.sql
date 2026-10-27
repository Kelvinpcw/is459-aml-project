-- Applied on 26 October 2026 after Q1 PASSED; historical draft filename retained.
-- Query IDs and execution evidence: ../aws/reviews/athena-query-executions-20261026.json.
-- Known schema and explicit partition; no crawler is required.
CREATE DATABASE IF NOT EXISTS is459_aml_dev;

CREATE EXTERNAL TABLE is459_aml_dev.q1_daily_counts_dev20220901_v2 (
    dataset_version STRING,
    run_id STRING,
    sender_bank STRING,
    receiver_bank STRING,
    payment_format STRING,
    payment_currency STRING,
    receiving_currency STRING,
    transaction_count BIGINT,
    laundering_count BIGINT,
    amount_paid_total DECIMAL(38,8),
    amount_received_total DECIMAL(38,8)
)
PARTITIONED BY (event_date DATE)
STORED AS PARQUET
LOCATION 's3://is459-aml-g2team7-160885259244-us-east-1/gold/risk/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q1-dev-20220901-v1/daily_counts/'
TBLPROPERTIES ('classification'='parquet');

ALTER TABLE is459_aml_dev.q1_daily_counts_dev20220901_v2
ADD PARTITION (event_date='2022-09-01')
LOCATION 's3://is459-aml-g2team7-160885259244-us-east-1/gold/risk/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q1-dev-20220901-v1/daily_counts/event_date=2022-09-01/';
