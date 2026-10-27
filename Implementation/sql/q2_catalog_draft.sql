-- LOCAL DRAFT; execute statements separately only after Q2 cloud report PASSED.
-- Use existing is459-aml-dev workgroup (50 MB/query), never provision capacity.
CREATE EXTERNAL TABLE IF NOT EXISTS is459_aml_dev.q2_case_index_dev20220901_m00_v1 (
  dataset_version string,
  run_id string,
  analysis_id string,
  case_id string,
  pattern_type string,
  bundle_uri string,
  participant_count int,
  unique_edge_count int,
  evidence_transaction_count int,
  window_start timestamp,
  window_end timestamp,
  snapshot_cutoff timestamp,
  first_event_time timestamp,
  last_event_time timestamp
)
PARTITIONED BY (window_date date)
STORED AS PARQUET
LOCATION 's3://is459-aml-g2team7-160885259244-us-east-1/gold/cases/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q2-dev-20220901-m00-v1/case_index/';

ALTER TABLE is459_aml_dev.q2_case_index_dev20220901_m00_v1
ADD IF NOT EXISTS PARTITION (window_date='2022-09-01')
LOCATION 's3://is459-aml-g2team7-160885259244-us-east-1/gold/cases/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q2-dev-20220901-m00-v1/case_index/window_date=2022-09-01/';
