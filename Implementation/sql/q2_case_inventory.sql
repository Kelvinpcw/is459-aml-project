-- Run only after the cloud Q2 report passes, using is459-aml-dev (50 MB/query).
-- Read all 15 bounded prototype index rows; compare every field with the frozen
-- local case bundles, including S3 destinations, counts and time boundaries.
SELECT dataset_version, run_id, analysis_id, case_id, pattern_type, bundle_uri,
       participant_count, unique_edge_count, evidence_transaction_count,
       window_start, window_end, snapshot_cutoff, first_event_time, last_event_time,
       window_date
FROM is459_aml_dev.q2_case_index_dev20220901_m00_v1
WHERE window_date = DATE '2022-09-01'
ORDER BY case_id;
