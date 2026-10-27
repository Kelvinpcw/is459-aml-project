"""Distributed structural-v2 detector. No driver graph or independent minute slicing.

Fan topology uses all non-self edges in a declared lookback. Cycles use an
explicit degree-eligible induced graph; exclusions and every expansion guard are
reported. Output relations retain complete source evidence without display caps.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime
import json,hashlib
from q2_detect import DETECTOR_COLUMNS,assert_label_free_columns,validate_manifest


@dataclass(frozen=True)
class DistributedConfig:
    dataset_version:str
    run_id:str
    analysis_id:str
    window_start:str
    window_end:str
    snapshot_cutoff:str
    min_counterparties:int=5
    max_cycle_degree:int=64
    max_cycle_path_rows:int=2000000
    max_cases:int=2000000
    max_evidence_memberships:int=100000000

    def times(self):
        from q2_detect import Config
        values=Config(self.dataset_version,self.run_id,self.analysis_id,self.window_start,self.window_end,self.snapshot_cutoff).times()
        if self.min_counterparties<5 or min(self.max_cycle_degree,self.max_cycle_path_rows,self.max_cases,self.max_evidence_memberships)<1:
            raise ValueError('Invalid distributed limits')
        return values


def detect(facts,manifest,config,inputs_validated=False):
    from pyspark.sql import functions as F,types as T
    from pyspark import StorageLevel
    validate_manifest(manifest);start,end,cutoff=config.times()
    assert_label_free_columns(facts.columns)
    if set(facts.columns)!=set(manifest['fact_columns']):raise ValueError('Fact allowlist differs from approved manifest')
    for c in ('amount_paid','amount_received'):
        if facts.schema[c].dataType!=T.DecimalType(38,8):raise ValueError('Exact decimal(38,8) required')
    if not inputs_validated:
        if facts.count()!=manifest['accepted_rows']:raise ValueError('Full input population differs')
        invalid=F.col('source_id').isNull() | F.col('event_time').isNull()
        invalid=invalid | ~F.coalesce((F.col('dataset_version')==config.dataset_version)&(F.col('run_id')==config.run_id),F.lit(False))
        for c in ('sender_bank','sender_account','receiver_bank','receiver_account'):
            invalid=invalid | F.col(c).isNull() | (F.length(F.col(c))==0)
        if facts.filter(invalid).limit(1).count():raise ValueError('Invalid source/identity/time/endpoint')
        if facts.groupBy('source_id').count().filter('count>1').limit(1).count():raise ValueError('Duplicate source IDs')
    if 'event_date' in facts.columns:
        from datetime import timedelta
        facts=facts.filter((F.col('event_date')>=F.lit(start.date()))&(F.col('event_date')<=F.lit((end-timedelta(microseconds=1)).date())))
    scoped=(facts.filter((F.col('event_time')>=F.lit(start))&(F.col('event_time')<F.lit(end))&(F.col('event_time')<=F.lit(cutoff)))
            .select(*DETECTOR_COLUMNS).withColumn('src',F.to_json(F.array('sender_bank','sender_account')))
            .withColumn('dst',F.to_json(F.array('receiver_bank','receiver_account'))).persist(StorageLevel.DISK_ONLY))
    scoped_n=scoped.count();nonself=scoped.filter('src<>dst').persist(StorageLevel.DISK_ONLY)
    edges=nonself.select('src','dst').distinct().localCheckpoint(eager=True)
    edge_n=edges.count()
    indegree=edges.groupBy('dst').count().withColumnRenamed('count','indegree').withColumnRenamed('dst','node')
    outdegree=edges.groupBy('src').count().withColumnRenamed('count','outdegree').withColumnRenamed('src','node')
    degrees=indegree.join(outdegree,'node','full').na.fill(0).persist(StorageLevel.DISK_ONLY)
    excluded=degrees.filter((F.col('indegree')>config.max_cycle_degree)|(F.col('outdegree')>config.max_cycle_degree)).select('node')
    excluded_n=excluded.count()
    eligible=degrees.filter((F.col('indegree')<=config.max_cycle_degree)&(F.col('outdegree')<=config.max_cycle_degree)&(F.col('indegree')>0)&(F.col('outdegree')>0)).select('node')
    cycle_edges=(edges.join(eligible.withColumnRenamed('node','src'),'src')
                 .join(eligible.withColumnRenamed('node','dst'),'dst').localCheckpoint(eager=True))
    cycle_edges_n=cycle_edges.count()
    # Case identity is rule + immutable input identity + snapshot + motif/hub;
    # fan peers/evidence are separate distributed relations, never driver lists.
    prefix=json.dumps({'rule_version':'structural-v2','dataset_version':config.dataset_version,'run_id':config.run_id,
          'window_start':config.window_start,'window_end':config.window_end,'snapshot_cutoff':config.snapshot_cutoff,
          'min_counterparties':config.min_counterparties,'max_cycle_degree':config.max_cycle_degree},sort_keys=True,separators=(',',':'))
    def identify(frame):
        return frame.withColumn('case_id',F.sha2(F.concat(F.lit(prefix),F.to_json(F.struct('pattern_type','ordered_nodes'))),256))
    def fans(column,kind):
        hubs=edges.groupBy(column).count().filter(F.col('count')>=config.min_counterparties).select(F.col(column).alias('hub'))
        return identify(hubs.withColumn('pattern_type',F.lit(kind)).withColumn('ordered_nodes',F.array('hub')))
    fan_in=fans('dst','fan_in');fan_out=fans('src','fan_out')
    topologies=[fan_in,fan_out]
    # Meet in the middle: enumerate only two-hop paths, then close triangles
    # or join opposite two-hop paths. Avoid materialising every open 3-hop path.
    # Minimum root removes rotation duplicates; reverse orientations survive.
    a,b=cycle_edges.alias('a'),cycle_edges.alias('b')
    reciprocal=a.filter(F.col('a.src')<F.col('a.dst')).join(b,(F.col('a.src')==F.col('b.dst'))&(F.col('a.dst')==F.col('b.src')))
    c2=reciprocal.select(F.lit('cycle_2').alias('pattern_type'),F.array(F.col('a.src'),F.col('a.dst')).alias('ordered_nodes')).withColumn('hub',F.lit(None).cast('string'))
    topologies.append(identify(c2).select('hub','pattern_type','ordered_nodes','case_id'))
    incoming=cycle_edges.groupBy('dst').count().withColumnRenamed('count','incoming').withColumnRenamed('dst','node')
    outgoing=cycle_edges.groupBy('src').count().withColumnRenamed('count','outgoing').withColumnRenamed('src','node')
    predicted=incoming.join(outgoing,'node').agg(F.sum(F.col('incoming')*F.col('outgoing'))).first()[0] or 0
    if predicted>config.max_cycle_path_rows:raise ValueError('Predicted two-hop expansion exceeds declared guard')
    paths=(a.join(b,F.col('a.dst')==F.col('b.src')).filter(F.col('a.src')!=F.col('b.dst'))
      .select(F.col('a.src').alias('n0'),F.col('a.dst').alias('n1'),F.col('b.dst').alias('n2')).localCheckpoint(eager=True))
    first=paths.filter((F.col('n0')<F.col('n1'))&(F.col('n0')<F.col('n2'))).localCheckpoint(eager=True)
    p,e=first.alias('p'),cycle_edges.alias('e')
    triangles=p.join(e,(F.col('p.n2')==F.col('e.src'))&(F.col('p.n0')==F.col('e.dst')))
    c3=triangles.select(F.lit('cycle_3').alias('pattern_type'),F.array(F.col('p.n0'),F.col('p.n1'),F.col('p.n2')).alias('ordered_nodes')).withColumn('hub',F.lit(None).cast('string'))
    topologies.append(identify(c3).select('hub','pattern_type','ordered_nodes','case_id'))
    left_counts=first.groupBy('n0','n2').count().withColumnRenamed('count','left_count')
    right_counts=paths.groupBy('n0','n2').count().select(F.col('n0').alias('n2'),F.col('n2').alias('n0'),F.col('count').alias('right_count'))
    upper=left_counts.join(right_counts,['n0','n2']).agg(F.sum(F.col('left_count')*F.col('right_count'))).first()[0] or 0
    if upper>config.max_cycle_path_rows:raise ValueError('Predicted four-cycle join exceeds declared guard')
    q=paths.alias('q')
    squares=p.join(q,(F.col('p.n2')==F.col('q.n0'))&(F.col('p.n0')==F.col('q.n2'))&(F.col('q.n1')>F.col('p.n0'))&(F.col('q.n1')!=F.col('p.n1')))
    c4=squares.select(F.lit('cycle_4').alias('pattern_type'),F.array(F.col('p.n0'),F.col('p.n1'),F.col('p.n2'),F.col('q.n1')).alias('ordered_nodes')).withColumn('hub',F.lit(None).cast('string'))
    topologies.append(identify(c4).select('hub','pattern_type','ordered_nodes','case_id'))
    path_counts={'two_hop_upper_bound':predicted,'four_cycle_candidate_upper_bound':upper}
    cases=topologies[0]
    for frame in topologies[1:]:cases=cases.unionByName(frame)
    cases=cases.localCheckpoint(eager=True);case_n=cases.count()
    if case_n>config.max_cases:raise ValueError('Case output guard exceeded')
    fan_pairs=(fan_in.select('case_id','hub').join(edges,F.col('hub')==F.col('dst')).select('case_id','src','dst')
               .unionByName(fan_out.select('case_id','hub').join(edges,F.col('hub')==F.col('src')).select('case_id','src','dst')))
    cycles=cases.filter("pattern_type LIKE 'cycle_%'")
    cycle_pairs=(cycles.select('case_id','ordered_nodes',F.posexplode('ordered_nodes').alias('pos','src'))
        .withColumn('dst',F.element_at('ordered_nodes',((F.col('pos')+1)%F.size('ordered_nodes'))+1)).select('case_id','src','dst'))
    pairs=fan_pairs.unionByName(cycle_pairs).localCheckpoint(eager=True)
    evidence=pairs.join(nonself,['src','dst']).localCheckpoint(eager=True)
    evidence_n=evidence.count()
    if evidence_n>config.max_evidence_memberships:raise ValueError('Evidence output guard exceeded; no partial success')
    counts=evidence.groupBy('case_id').agg(F.count('*').alias('evidence_transaction_count'),F.min('event_time').alias('first_event_time'),F.max('event_time').alias('last_event_time'))
    edge_counts=pairs.groupBy('case_id').count().withColumnRenamed('count','unique_edge_count')
    members=pairs.select('case_id',F.col('src').alias('node')).union(pairs.select('case_id',F.col('dst').alias('node'))).distinct()
    member_counts=members.groupBy('case_id').count().withColumnRenamed('count','participant_count')
    index=cases.join(counts,'case_id').join(edge_counts,'case_id').join(member_counts,'case_id')
    for name,value in (('dataset_version',config.dataset_version),('run_id',config.run_id),('analysis_id',config.analysis_id),('rule_version','structural-v2')):
        index=index.withColumn(name,F.lit(value))
    for name,value in (('window_start',start),('window_end',end),('snapshot_cutoff',cutoff)):
        index=index.withColumn(name,F.lit(value))
    index=index.withColumn('window_date',F.to_date('window_start'))
    stats={'scoped_rows':scoped_n,'self_transaction_rows':scoped_n-nonself.count(),'distinct_nonself_edges':edge_n,
           'case_count':case_n,'case_evidence_rows_including_case_overlap':evidence_n,
           'cycle_excluded_nodes_above_degree':excluded_n,'cycle_eligible_edges':cycle_edges_n,
           'cycle_edges_outside_eligible_induced_graph':edge_n-cycle_edges_n,'cycle_path_rows':path_counts,
           'complete_for_declared_window':True,'truncated':False,
           'cycle_coverage':'All 2-4 simple directed cycles in the declared degree-eligible induced graph; not all original graph cycles.'}
    return index,pairs,evidence,stats


def export_rows(index,evidence):
    """Give metadata fresh expression IDs before joining shared checkpoint lineage.

    Glue's Spark analyzer can otherwise retain the same case_id attribute on
    both sides, even though the relations have different projection lineages.
    """
    from pyspark.sql import functions as F
    metadata=[c for c in index.columns if c not in evidence.columns or c=='case_id']
    right=index.select(*(F.col(c).alias(c) for c in metadata))
    return evidence.join(right,'case_id')


def export_partition(rows,bucket,prefix,profile=None,region='us-east-1'):
    """Bounded-memory complete evidence chunks; deterministic executor retries."""
    import boto3,itertools
    from botocore.exceptions import ClientError
    from q2_detect import _json_default
    session=boto3.Session(profile_name=profile,region_name=region) if profile else boto3.Session(region_name=region)
    s3=session.client('s3');done=0;total=0
    def put(key,body):
        digest=hashlib.sha256(body).hexdigest()
        try:s3.put_object(Bucket=bucket,Key=key,Body=body,IfNoneMatch='*',ContentType='application/json',Metadata={'sha256':digest})
        except ClientError as error:
            if error.response['Error']['Code'] not in ('PreconditionFailed','412'):raise
            existing=s3.get_object(Bucket=bucket,Key=key)['Body'].read()
            if hashlib.sha256(existing).hexdigest()!=digest:raise ValueError('Conflicting executor retry output')
        return {'uri':f's3://{bucket}/{key}','sha256':digest,'bytes':len(body)}
    for case_id,group in itertools.groupby(rows,key=lambda r:r['case_id']):
        parts=[];chunk=[];chunk_bytes=0;count=0;nodes={};edges={};preview=[];first=None
        def flush():
            nonlocal chunk,chunk_bytes
            if not chunk:return
            body=('\n'.join(chunk)+'\n').encode()
            ref=put(prefix+'evidence/'+case_id+f'/part-{len(parts):06d}.jsonl',body)
            ref['rows']=len(chunk);parts.append(ref);chunk=[];chunk_bytes=0
        for row in group:
            data=row.asDict(recursive=True)
            if first is None:first=data
            tx={k:data[k] for k in DETECTOR_COLUMNS if k not in ('dataset_version','run_id')}
            line=json.dumps(tx,default=_json_default,sort_keys=True)
            if len(line.encode())>1000000:raise ValueError('One evidence record exceeds the chunk bound')
            if chunk_bytes+len(line.encode())>1000000:flush()
            chunk.append(line);chunk_bytes+=len(line.encode())+1;count+=1
            if len(preview)<200:preview.append(tx)
            for side in ('sender','receiver'):
                nid=data['src' if side=='sender' else 'dst']
                if nid in nodes or len(nodes)<100:
                    nodes[nid]={'node_id':nid,'bank':data[side+'_bank'],'account':data[side+'_account'],
                       'entity_id':data[side+'_entity_id'],'entity_name':data[side+'_entity_name'],'entity_unknown':data[side+'_entity_unknown']}
            pair=(data['src'],data['dst'])
            if pair in edges:edges[pair]+=1
            elif len(edges)<500 and all(n in nodes for n in pair):edges[pair]=1
        flush()
        if count!=first['evidence_transaction_count']:raise ValueError('Case evidence count differs from distributed index')
        header={k:first[k] for k in ('case_id','pattern_type','hub','ordered_nodes','participant_count','unique_edge_count',
                 'evidence_transaction_count','first_event_time','last_event_time','dataset_version','run_id','analysis_id','rule_version',
                 'window_start','window_end','snapshot_cutoff')}
        header.update(schema_version=2,nodes=list(nodes.values()),edges=[{'source':a,'target':b,'transaction_count':n} for (a,b),n in sorted(edges.items())],
          transactions=preview,evidence_parts=parts,display_capped=len(nodes)<first['participant_count'] or len(edges)<first['unique_edge_count'] or count>200,
          interpretation='Structural investigation lead; cycles are limited to the declared degree-eligible graph. No claim of laundering or chronological return of identical funds.')
        put(prefix+'bundles/'+case_id+'.json',(json.dumps(header,default=_json_default,sort_keys=True)+'\n').encode())
        done+=1;total+=count
    yield (done,total)


def main():
    import argparse,boto3
    from datetime import timezone
    from urllib.parse import urlparse
    from pyspark.sql import SparkSession,functions as F
    p=argparse.ArgumentParser()
    for name in ('input-manifest','output-root','analysis-id','window-start','window-end','snapshot-cutoff'):p.add_argument('--'+name,required=True)
    p.add_argument('--max-cycle-degree',type=int,default=64)
    args,_=p.parse_known_args();s3=boto3.client('s3',region_name='us-east-1')
    src=urlparse(args.input_manifest);out=urlparse(args.output_root)
    if src.scheme!='s3' or out.scheme!='s3':raise ValueError('Explicit S3 paths required')
    manifest=json.loads(s3.get_object(Bucket=src.netloc,Key=src.path.lstrip('/'))['Body'].read());validate_manifest(manifest)
    cfg=DistributedConfig(manifest['dataset_version'],manifest['run_id'],args.analysis_id,args.window_start,args.window_end,args.snapshot_cutoff,max_cycle_degree=args.max_cycle_degree);cfg.times()
    suffix=f'dataset_version={cfg.dataset_version}/run_id={cfg.run_id}/analysis_id={cfg.analysis_id}/'
    base=out.path.strip('/');base=(base+'/') if base else ''
    caseprefix=base+'gold/cases/'+suffix;qualitykey=base+'quality/q2/'+suffix+'report.json'
    for prefix in (caseprefix,base+'quality/q2/'+suffix):
        if s3.list_objects_v2(Bucket=out.netloc,Prefix=prefix,MaxKeys=1).get('KeyCount',0):raise ValueError('Attempt namespace already exists')
    report={'schema_version':2,'stage':'q2','status':'FAILED','config':asdict(cfg),'rule_version':'structural-v2','distributed_processing':True,
       'input_manifest':args.input_manifest,'full_prepared_rows':manifest['accepted_rows'],'detector_received_labels':False}
    spark=SparkSession.builder.appName('is459-q2-distributed').config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','64').getOrCreate()
    try:
        index,pairs,evidence,stats=detect(spark.read.parquet(manifest['inputs']['transactions']),manifest,cfg)
        root=f's3://{out.netloc}/{caseprefix}'
        index=index.withColumn('bundle_uri',F.concat(F.lit(root+'bundles/'),F.col('case_id'),F.lit('.json')))
        index.write.mode('errorifexists').partitionBy('window_date').parquet(root+'case_index/')
        pairs.write.mode('errorifexists').parquet(root+'case_edges/')
        evidence.write.mode('errorifexists').parquet(root+'case_evidence/')
        metadata=[c for c in index.columns if c not in evidence.columns or c=='case_id']
        export=export_rows(index,evidence).repartition(64,'case_id').sortWithinPartitions('case_id','event_time','source_id')
        totals=export.rdd.mapPartitions(lambda rows:export_partition(rows,out.netloc,caseprefix)).collect()
        if sum(x[0] for x in totals)!=stats['case_count'] or sum(x[1] for x in totals)!=stats['case_evidence_rows_including_case_overlap']:
            raise ValueError('Export completion inventory differs')
        report.update(status='PASSED',statistics=stats,case_index_schema=index.schema.jsonValue(),
          outputs={'case_index':root+'case_index/','bundles':root+'bundles/','case_edges':root+'case_edges/','case_evidence':root+'case_evidence/'},
          exported_cases=sum(x[0] for x in totals),exported_evidence_memberships=sum(x[1] for x in totals))
    except Exception as error:report.update(error_type=type(error).__name__,error=str(error)[:2000]);raise
    finally:
        report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        s3.put_object(Bucket=out.netloc,Key=qualitykey,Body=(json.dumps(report,indent=2)+'\n').encode(),IfNoneMatch='*',ContentType='application/json')
        spark.stop()

if __name__=='__main__':main()
