"""Run complete overlapping daily lookbacks, preserving cross-boundary motifs.

This is an alternative entry point for structural-v2. Every snapshot reads the
full required history. Snapshot membership overlaps; evaluation counts unique
source IDs within a separately declared, non-overlapping scoring period.
"""
from datetime import datetime,timedelta
from dataclasses import replace
from functools import reduce
import json
from q2_distributed import DistributedConfig,detect,export_partition
from q2_detect import validate_manifest


def schedule(first_end,last_end,lookback_days=7):
    first,last=(datetime.fromisoformat(x) for x in (first_end,last_end))
    if not 1<=lookback_days<=7 or first>last or first.time()!=datetime.min.time() or last.time()!=datetime.min.time():
        raise ValueError('Require daily snapshot cutoffs and a 1-7 day lookback')
    if (last-first).days>28:raise ValueError('Snapshot schedule exceeds this dataset contract')
    return [(end-timedelta(days=lookback_days),end) for end in (first+timedelta(days=i) for i in range((last-first).days+1))]


def run_snapshots(facts,manifest,config,windows,write_snapshot):
    """One immutable attempt per schedule; any failure prevents PASSED publication."""
    from pyspark.sql import functions as F
    stats=[]
    available_from=facts.agg(F.min('event_time')).first()[0]
    for number,(start,end) in enumerate(windows):
        snapshot=replace(config,window_start=start.isoformat(),window_end=end.isoformat(),snapshot_cutoff=end.isoformat())
        index,pairs,evidence,observed=detect(facts,manifest,snapshot,inputs_validated=number>0)
        observed['history_complete']=available_from is not None and start>=available_from
        observed['history_available_from']=available_from.isoformat() if available_from else None
        write_snapshot(snapshot,index,pairs,evidence,observed)
        stats.append({'window_start':start.isoformat(),'window_end':end.isoformat(),'snapshot_cutoff':end.isoformat(),**observed})
        # Checkpointed intermediate blocks are no longer needed after durable writes.
        facts.sparkSession.catalog.clearCache()
        persisted=facts.sparkSession.sparkContext._jsc.sc().getPersistentRDDs().values().iterator()
        while persisted.hasNext():persisted.next().unpersist(False)
    return stats



def output_cost_estimate(index,evidence):
    """Conservative 30-day S3 storage/PUT estimate, checked before each export."""
    from pyspark.sql import functions as F
    from q2_detect import DETECTOR_COLUMNS
    raw_size=F.length(F.encode(F.to_json(F.struct(*DETECTOR_COLUMNS)),'UTF-8'))+256
    row_bytes=evidence.agg(F.max(raw_size)).first()[0] or 1
    if row_bytes>=1000000:raise ValueError('Evidence record exceeds export size guard')
    header=F.least(F.col('participant_count'),F.lit(100))*row_bytes+F.least(F.col('unique_edge_count'),F.lit(500))*row_bytes+F.least(F.col('evidence_transaction_count'),F.lit(200))*row_bytes+2048
    r=index.agg(F.count('*').alias('cases'),F.sum('evidence_transaction_count').alias('memberships'),F.sum(header).alias('headers')).first()
    cases=r['cases'];bytes_data=(r['memberships'] or 0)*row_bytes
    chunks=cases+bytes_data/(1000000-row_bytes)
    total_bytes=2*bytes_data+(r['headers'] or 0)+chunks*512+cases*1024
    return {'estimated_30day_storage_bytes_upper_bound':int(total_bytes),'estimated_put_requests_upper_bound':int(cases+chunks+1),
            'estimated_output_cost_usd':total_bytes/1_000_000_000*.023+(cases+chunks)*.000005}

def main():
    import argparse,boto3
    from urllib.parse import urlparse
    from datetime import timezone
    from dataclasses import asdict
    from pyspark.sql import SparkSession,functions as F
    p=argparse.ArgumentParser()
    for arg in ('input-manifest','output-root','analysis-id','first-snapshot-end','last-snapshot-end'):p.add_argument('--'+arg,required=True)
    p.add_argument('--max-cycle-degree',type=int,default=64)
    p.add_argument('--max-cycle-path-rows',type=int,default=2000000)
    p.add_argument('--max-output-cost-usd',type=float,default=10)
    args,_=p.parse_known_args();s3=boto3.client('s3',region_name='us-east-1')
    src=urlparse(args.input_manifest);out=urlparse(args.output_root)
    if src.scheme!='s3' or out.scheme!='s3':raise ValueError('Explicit S3 paths required')
    manifest=json.loads(s3.get_object(Bucket=src.netloc,Key=src.path.lstrip('/'))['Body'].read());validate_manifest(manifest)
    windows=schedule(args.first_snapshot_end,args.last_snapshot_end)
    config=DistributedConfig(manifest['dataset_version'],manifest['run_id'],args.analysis_id,windows[0][0].isoformat(),windows[-1][1].isoformat(),windows[-1][1].isoformat(),max_cycle_degree=args.max_cycle_degree,max_cycle_path_rows=args.max_cycle_path_rows)
    config.times();suffix=f'dataset_version={config.dataset_version}/run_id={config.run_id}/analysis_id={config.analysis_id}/'
    base=out.path.strip('/');base=base+'/' if base else ''
    prefix=base+'gold/cases/'+suffix;qualitykey=base+'quality/q2/'+suffix+'report.json';root=f's3://{out.netloc}/{prefix}'
    for key in (prefix,base+'quality/q2/'+suffix):
        if s3.list_objects_v2(Bucket=out.netloc,Prefix=key,MaxKeys=1).get('KeyCount',0):raise ValueError('Fresh snapshot attempt required')
    report={'schema_version':2,'stage':'q2','status':'FAILED','config':asdict(config),'rule_version':'structural-v2','distributed_processing':True,
      'detector_received_labels':False,'input_manifest':args.input_manifest,'full_prepared_rows':manifest['accepted_rows']}
    spark=SparkSession.builder.appName('is459-q2-snapshots').config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','64').getOrCreate()
    facts=spark.read.parquet(manifest['inputs']['transactions'])
    try:
        estimated_output_cost=0
        index_schema=None
        def write_snapshot(cfg,index,pairs,evidence,stats):
            nonlocal estimated_output_cost,index_schema
            estimate=output_cost_estimate(index,evidence)
            if estimated_output_cost+estimate['estimated_output_cost_usd']>args.max_output_cost_usd:raise ValueError('Projected output cost exceeds the declared budget guard before this snapshot export')
            estimated_output_cost+=estimate['estimated_output_cost_usd'];stats.update(estimate)
            index=index.withColumn('bundle_uri',F.concat(F.lit(root+'bundles/'),F.col('case_id'),F.lit('.json')))
            index_schema=index.schema.jsonValue()
            index.write.mode('append').partitionBy('window_date').parquet(root+'case_index/')
            pairs.write.mode('append').parquet(root+'case_edges/')
            evidence.write.mode('append').parquet(root+'case_evidence/')
            metadata=[c for c in index.columns if c not in evidence.columns or c=='case_id']
            export=evidence.join(index.select(*metadata),'case_id').repartition(64,'case_id').sortWithinPartitions('case_id','event_time','source_id')
            totals=export.rdd.mapPartitions(lambda rows:export_partition(rows,out.netloc,prefix)).collect()
            if sum(x[0] for x in totals)!=stats['case_count'] or sum(x[1] for x in totals)!=stats['case_evidence_rows_including_case_overlap']:
                raise ValueError('Snapshot exports incomplete')
        snapshots=run_snapshots(facts,manifest,config,windows,write_snapshot)
        scope_count=facts.filter((F.col('event_time')>=F.lit(windows[0][0]))&(F.col('event_time')<F.lit(windows[-1][1]))).count()
        report.update(status='PASSED',snapshots=snapshots,statistics={'scoped_rows':scope_count,'case_count':sum(x['case_count'] for x in snapshots),
          'case_evidence_rows_including_case_overlap':sum(x['case_evidence_rows_including_case_overlap'] for x in snapshots),'complete_for_declared_window':True,'truncated':False,'estimated_output_cost_usd':estimated_output_cost},
          outputs={'case_index':root+'case_index/','bundles':root+'bundles/','case_edges':root+'case_edges/','case_evidence':root+'case_evidence/'},
          case_index_schema=index_schema)
    except Exception as error:report.update(error_type=type(error).__name__,error=str(error)[:2000]);raise
    finally:
        report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        s3.put_object(Bucket=out.netloc,Key=qualitykey,Body=(json.dumps(report,indent=2)+'\n').encode(),IfNoneMatch='*',ContentType='application/json');spark.stop()

if __name__=='__main__':main()
