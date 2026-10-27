-- LOCAL DRAFT; expected local replay: 15 fan_out cases / 840 evidence rows.
-- No labels/evaluation tables are referenced. Empty output is valid only if the
-- passed Q2 report and independently reconciled inventory both declare zero.
SELECT pattern_type, count(*) AS cases, count(DISTINCT case_id) AS unique_cases,
       sum(evidence_transaction_count) AS supporting_rows_including_overlap,
       sum(CASE WHEN first_event_time < window_start OR last_event_time >= window_end
                     OR last_event_time > snapshot_cutoff
                     OR dataset_version <> 'ibm-hi-medium-b1b99c68b765580f'
                     OR run_id <> 'dev-20220901-v2'
                     OR analysis_id <> 'q2-dev-20220901-m00-v1'
                     OR participant_count < 2 OR unique_edge_count < 1
                     OR evidence_transaction_count < unique_edge_count
                THEN 1 ELSE 0 END) AS invalid_rows
FROM is459_aml_dev.q2_case_index_dev20220901_m00_v1
WHERE window_date = DATE '2022-09-01'
GROUP BY pattern_type
ORDER BY pattern_type;
