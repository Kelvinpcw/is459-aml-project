"""Separate structural-v2 evaluator; distributed denominators, bounded references.

Detection is frozen before this job reads labels/annotations. A calibration file
is required for holdout; its source scopes must end before 9 September. Exact
reference matching preserves ambiguities and source ordinals, never guesswork.
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
import json,hashlib,math
from evaluate_q2 import parse_annotations,topology,pair,MATCH_COLUMNS


def metrics(population,positive,alerted,tp):
    return {'population':population,'positive_labels':positive,'unique_alerted_transactions':alerted,
            'true_positive':tp,'false_positive':alerted-tp,'false_negative':positive-tp,
            'true_negative':population-positive-alerted+tp,
            'precision':tp/alerted if alerted else None,'recall':tp/positive if positive else None,
            'lift_vs_population':tp/alerted/(positive/population) if population and positive and alerted else None,
            'recall_status':'measured' if positive else 'no_positive_labels'}


def validate_calibration(policy,config):
    if policy.get('schema_version')!=1 or policy.get('frozen') is not True:
        raise ValueError('Require a frozen development calibration policy')
    if policy.get('rule_version')!='structural-v2' or policy['min_counterparties']!=config['min_counterparties'] or policy['max_cycle_degree']!=config['max_cycle_degree']:
        raise ValueError('Detection settings differ from frozen calibration')
    if not policy.get('development_analyses') or any(datetime.fromisoformat(r['window_end'])>datetime(2022,9,9) for r in policy['development_analyses']):
        raise ValueError('Calibration includes holdout/future scope')
    for currency,rate in policy['amount_alert_fraction_by_currency'].items():
        if not 0<=Decimal(str(rate))<=1:raise ValueError('Invalid calibrated baseline fraction')
    if not policy.get('improvement_target'):raise ValueError('Improvement target must be declared before holdout')


def complete_fan_pairs(fan,edges):
    """Reconstruct fan pairs with keyed joins; OR direction predicates are Cartesian.

    Time/cutoff bounds remain case-local. Parallel payments collapse only here
    to directional pairs; the independent evidence check retains source IDs.
    """
    from pyspark.sql import functions as F
    directions=[]
    for pattern,endpoint in [('fan_in','dst'),('fan_out','src')]:
        f=fan.filter(F.col('pattern_type')==pattern).alias('f');e=edges.alias('e')
        matches=f.join(e,F.col('f.hub')==F.col('e.'+endpoint))
        directions.append(matches.filter((F.col('e.event_time')>=F.col('f.window_start'))&(F.col('e.event_time')<F.col('f.window_end'))&(F.col('e.event_time')<=F.col('f.snapshot_cutoff')))
            .select(F.col('f.case_id').alias('case_id'),F.col('e.src').alias('src'),F.col('e.dst').alias('dst')))
    return directions[0].unionByName(directions[1]).distinct()


def evaluate(facts,labels,index,pairs,evidence,prep,detector,attempts,calibration=None,scoring_window=None):
    from pyspark.sql import functions as F,types as T,Window
    cfg=detector['config'];start,end,cutoff=(datetime.fromisoformat(cfg[x]) for x in ('window_start','window_end','snapshot_cutoff'))
    if detector.get('status')!='PASSED' or detector.get('rule_version')!='structural-v2' or detector.get('detector_received_labels') is not False:
        raise ValueError('Only a complete frozen label-free structural-v2 result may be evaluated')
    score_start,score_end=(tuple(datetime.fromisoformat(x) for x in scoring_window) if scoring_window else (start,end))
    if not start<=score_start<score_end<=end:raise ValueError('Scoring period must lie inside the detection history')
    if score_start<datetime(2022,9,9)<score_end or score_start<datetime(2022,9,17)<score_end:
        raise ValueError('Development, holdout and sparse tail must be scored separately')
    holdout=score_start>=datetime(2022,9,9)
    if holdout:
        if calibration is None:raise ValueError('Freeze development calibration before holdout evaluation')
        validate_calibration(calibration,cfg)
    keys=['source_id','dataset_version','run_id','event_date']
    expected=prep['accepted_rows']
    for frame in (facts,labels):
        if frame.count()!=expected:raise ValueError('Full fact/label population differs')
        invalid=F.lit(False)
        for key in keys:invalid=invalid|F.col(key).isNull()
        invalid=invalid|(F.col('dataset_version')!=cfg['dataset_version'])|(F.col('run_id')!=cfg['run_id'])
        if frame.filter(invalid).limit(1).count() or frame.groupBy('source_id').count().filter('count>1').limit(1).count():
            raise ValueError('Missing/duplicate/foreign source identity')
    for col in ('amount_paid','amount_received'):
        if facts.schema[col].dataType!=T.DecimalType(38,8):raise ValueError('Exact decimal contract required')
    if labels.filter(~F.coalesce(F.col('is_laundering').isin(0,1),F.lit(False))).limit(1).count():raise ValueError('Invalid label')
    joined=facts.join(labels,keys).localCheckpoint(eager=True)
    if joined.count()!=expected:raise ValueError('Fact-label join differs')
    actual={r['payment_format']:(r['n'],r['l']) for r in joined.groupBy('payment_format').agg(F.count('*').alias('n'),F.sum('is_laundering').alias('l')).collect()}
    if actual!={r['payment_format']:(r['transactions'],r['labelled_laundering']) for r in prep['accepted_by_format']}:raise ValueError('Full per-format labels differ')
    history=joined.filter((F.col('event_time')>=F.lit(start))&(F.col('event_time')<F.lit(end))&(F.col('event_time')<=F.lit(cutoff))).localCheckpoint(eager=True)
    if history.count()!=detector['statistics']['scoped_rows']:raise ValueError('Detector history population differs')
    eligible=history.filter((F.col('event_time')>=F.lit(score_start))&(F.col('event_time')<F.lit(score_end))).localCheckpoint(eager=True)
    population=eligible.count()
    identity_bad=(F.col('dataset_version')!=cfg['dataset_version'])|(F.col('run_id')!=cfg['run_id'])|(F.col('analysis_id')!=cfg['analysis_id'])
    if index.filter(~F.coalesce(~identity_bad,F.lit(False))).limit(1).count():raise ValueError('Foreign case index identity')
    if index.filter((F.col('window_start')<F.lit(start))|(F.col('window_end')>F.lit(end))|(F.col('window_start')>=F.col('window_end'))|(F.col('snapshot_cutoff')>F.col('window_end'))).limit(1).count():raise ValueError('Invalid case snapshot scope')
    seed={'dataset_version':F.lit(cfg['dataset_version']),'run_id':F.lit(cfg['run_id']),'rule_version':F.lit('structural-v2'),
          'min_counterparties':F.lit(cfg['min_counterparties']),'max_cycle_degree':F.lit(cfg['max_cycle_degree'])}
    for key in ('window_start','window_end','snapshot_cutoff'):seed[key]=F.date_format(key,"yyyy-MM-dd'T'HH:mm:ss")
    prefix=F.to_json(F.struct(*[seed[key].alias(key) for key in sorted(seed)]))
    expected_id=F.sha2(F.concat(prefix,F.to_json(F.struct('pattern_type','ordered_nodes'))),256)
    if index.filter(F.col('case_id')!=expected_id).limit(1).count():raise ValueError('Case identity hash differs from frozen motif/window')
    if index.count()!=detector['statistics']['case_count'] or index.groupBy('case_id').count().filter('count>1').limit(1).count():raise ValueError('Case index incomplete/duplicated')
    if evidence.count()!=detector['statistics']['case_evidence_rows_including_case_overlap']:raise ValueError('Evidence inventory incomplete')
    if evidence.groupBy('case_id','source_id').count().filter('count>1').limit(1).count():raise ValueError('Duplicate evidence membership')
    if evidence.join(history.select('source_id'),'source_id','left_anti').limit(1).count():raise ValueError('Foreign/out-of-window evidence')
    if evidence.select('case_id').distinct().join(index.select('case_id'),'case_id','left_anti').limit(1).count():raise ValueError('Foreign case evidence')
    # Select only snapshots available within this scoring period. Future cases
    # must never turn historical payments into earlier alerts.
    index=index.filter((F.col('snapshot_cutoff')<=F.lit(score_end))&(F.col('snapshot_cutoff')>F.lit(score_start)))
    selected_ids=index.select('case_id')
    evidence=evidence.join(selected_ids,'case_id')
    pairs=pairs.join(selected_ids,'case_id')
    # Re-derive complete membership from frozen pairs and their case-local history.
    ed=history.withColumn('src',F.to_json(F.array('sender_bank','sender_account'))).withColumn('dst',F.to_json(F.array('receiver_bank','receiver_account'))).filter('src<>dst')
    fan=index.filter(F.col('pattern_type').isin('fan_in','fan_out')).select('case_id','hub','pattern_type','window_start','window_end','snapshot_cutoff')
    complete_fan=complete_fan_pairs(fan,ed)
    actual_fan=pairs.join(fan.select('case_id'),'case_id').select('case_id','src','dst')
    if complete_fan.exceptAll(actual_fan).limit(1).count() or actual_fan.exceptAll(complete_fan).limit(1).count():raise ValueError('Fan topology drops or adds counterparties')
    if complete_fan.groupBy('case_id').count().filter(F.col('count')<cfg['min_counterparties']).limit(1).count():raise ValueError('Fan does not meet frozen degree')
    cycle=index.filter(F.col('pattern_type').startswith('cycle_'))
    invalid_cycle=(~F.size('ordered_nodes').isin(2,3,4))|(F.size(F.array_distinct('ordered_nodes'))!=F.size('ordered_nodes'))|F.col('hub').isNotNull()|(F.col('pattern_type')!=F.concat(F.lit('cycle_'),F.size('ordered_nodes')))
    if cycle.filter(invalid_cycle).limit(1).count():raise ValueError('Invalid oriented cycle participants')
    cycle_pairs=(cycle.select('case_id','ordered_nodes',F.posexplode('ordered_nodes').alias('pos','src'))
      .withColumn('dst',F.element_at('ordered_nodes',((F.col('pos')+1)%F.size('ordered_nodes'))+1)).select('case_id','src','dst'))
    actual_cycle=pairs.join(cycle.select('case_id'),'case_id').select('case_id','src','dst')
    if cycle_pairs.exceptAll(actual_cycle).limit(1).count() or actual_cycle.exceptAll(cycle_pairs).limit(1).count():raise ValueError('Cycle directional edges differ')
    if index.filter(~F.col('pattern_type').isin('fan_in','fan_out','cycle_2','cycle_3','cycle_4')).limit(1).count():raise ValueError('Unsupported case type')
    actual_counts=evidence.groupBy('case_id').agg(F.count('*').alias('observed_evidence'),F.min('event_time').alias('first'),F.max('event_time').alias('last'))
    if index.join(actual_counts,'case_id','left').filter(F.col('observed_evidence').isNull()|(F.col('observed_evidence')!=F.col('evidence_transaction_count'))|(F.col('first')!=F.col('first_event_time'))|(F.col('last')!=F.col('last_event_time'))).limit(1).count():raise ValueError('Case evidence counts/times differ')
    expected_members=(pairs.join(index.select('case_id','window_start','window_end','snapshot_cutoff'),'case_id').join(ed,['src','dst'])
      .filter((F.col('event_time')>=F.col('window_start'))&(F.col('event_time')<F.col('window_end'))&(F.col('event_time')<=F.col('snapshot_cutoff'))).select('case_id','source_id'))
    actual_members=evidence.select('case_id','source_id')
    if expected_members.exceptAll(actual_members).limit(1).count() or actual_members.exceptAll(expected_members).limit(1).count():raise ValueError('Directional pair evidence is incomplete or extraneous')
    # Compare actual stored evidence fields, not just source IDs.
    fields=['source_id']+list(MATCH_COLUMNS)
    if evidence.select(*fields).distinct().exceptAll(history.select(*fields)).limit(1).count():raise ValueError('Stored evidence differs from source facts')
    alerts=evidence.select('source_id').distinct().localCheckpoint(eager=True)
    def score(ids):
        rows=eligible.join(ids.withColumn('alert',F.lit(1)),'source_id','left')
        r=rows.agg(F.count('*').alias('n'),F.sum('is_laundering').alias('l'),F.sum(F.coalesce('alert',F.lit(0))).alias('a'),F.sum(F.when(F.col('alert')==1,F.col('is_laundering')).otherwise(0)).alias('tp')).first()
        return metrics(r['n'],r['l'] or 0,r['a'] or 0,r['tp'] or 0)
    budgets=eligible.join(alerts,'source_id').groupBy('payment_currency').count().withColumnRenamed('count','budget')
    currency_pop=eligible.groupBy('payment_currency').count().withColumnRenamed('count','population')
    matched_audit=currency_pop.join(budgets,'payment_currency','left').na.fill(0)
    audit=matched_audit
    if calibration:
        rates=calibration['amount_alert_fraction_by_currency']
        # Decimal fractions avoid floating monetary values or cross-currency totals.
        rate_schema=T.StructType([T.StructField('payment_currency',T.StringType(),False),T.StructField('fraction',T.DecimalType(20,12),False)])
        rate_df=facts.sparkSession.createDataFrame([(k,Decimal(str(v))) for k,v in rates.items()],rate_schema)
        if currency_pop.join(rate_df,'payment_currency','left_anti').limit(1).count():raise ValueError('Uncalibrated holdout currency')
        audit=currency_pop.join(rate_df,'payment_currency').withColumn('budget',F.ceil(F.col('population')*F.col('fraction')).cast('long'))
    rank=Window.partitionBy('payment_currency').orderBy(F.col('amount_paid').desc(),F.col('source_id'))
    ranked=eligible.withColumn('rank',F.row_number().over(rank)).localCheckpoint(eager=True)
    baseline=ranked.join(audit.select('payment_currency','budget'),'payment_currency').filter(F.col('rank')<=F.col('budget')).select('source_id').localCheckpoint(eager=True)
    matched_baseline=(ranked.join(matched_audit.select('payment_currency','budget'),'payment_currency').filter(F.col('rank')<=F.col('budget')).select('source_id').localCheckpoint(eager=True)) if calibration else baseline
    detector_metrics=score(alerts);frozen_baseline_metrics=score(baseline)
    baseline_metrics=score(matched_baseline) if calibration else frozen_baseline_metrics
    # Reference shape/window checks use only the small checksum-bounded annotation file.
    all_windows=detector.get('snapshots') or [cfg]
    available_windows=[s for s in all_windows if score_start<datetime.fromisoformat(s['snapshot_cutoff'])<=score_end]
    meta=[];refs=[]
    for a in attempts:
        rows=a['transactions'];times=[r['event_time'] for r in rows];reasons=[]
        if not all(score_start<=t<score_end for t in times):reasons.append('outside_declared_window')
        if any(t>cutoff for t in times):reasons.append('after_snapshot_cutoff')
        if not any(datetime.fromisoformat(w['window_start'])<=min(times) and max(times)<datetime.fromisoformat(w['window_end']) and max(times)<=datetime.fromisoformat(w['snapshot_cutoff']) for w in available_windows):reasons.append('no_eligible_snapshot')
        category={'FAN-IN':'fan_in','FAN-OUT':'fan_out','CYCLE':'cycle'}.get(a['annotation_type'],'unsupported')
        shape,reason=topology({pair(r) for r in rows},category,cfg['min_counterparties'])
        if reason:reasons.append(reason)
        meta.append({'attempt_id':a['attempt_id'],'annotation_type':a['annotation_type'],'annotation_transaction_count':len(rows),'exclusion_reasons':reasons,'shape':shape,'pattern_type':shape['pattern_type'] if shape else None,'source_matching':'not_applicable_ineligible_scope_or_shape' if reasons else 'checked'})
        if not reasons:
            for ordinal,r in enumerate(rows):refs.append({'attempt_id':a['attempt_id'],'ordinal':ordinal,**r})
    audits={a['attempt_id']:a for a in meta};matched=[]
    if refs:
        schema=T.StructType([T.StructField('attempt_id',T.StringType(),False),T.StructField('ordinal',T.IntegerType(),False)]+[T.StructField(k,T.TimestampType() if k=='event_time' else T.DecimalType(38,8) if k.startswith('amount_') else T.StringType(),False) for k in MATCH_COLUMNS])
        ref_df=facts.sparkSession.createDataFrame(refs,schema)
        matches=ref_df.join(eligible.select('source_id','is_laundering',*MATCH_COLUMNS),list(MATCH_COLUMNS),'left').groupBy('attempt_id','ordinal').agg(F.count('source_id').alias('candidate_count'),F.min('source_id').alias('source_id'),F.min('is_laundering').alias('is_laundering'))
        # At most 22,743 annotation occurrences, not the transaction population.
        for r in matches.collect():
            a=audits[r['attempt_id']]
            a.setdefault('source_candidate_counts',{})[str(r['ordinal'])]=r['candidate_count']
            if r['candidate_count']!=1:a['exclusion_reasons'].append('unmatched_source_transaction' if not r['candidate_count'] else 'ambiguous_source_transaction')
            elif r['is_laundering']!=1:a['exclusion_reasons'].append('annotation_label_conflict')
            else:matched.append((r['attempt_id'],r['source_id']))
        by_attempt={}
        for aid,sid in matched:by_attempt.setdefault(aid,[]).append(sid)
        for aid,ids in by_attempt.items():
            if len(ids)!=len(set(ids)):audits[aid]['exclusion_reasons'].append('repeated_annotation_source')
        valid={k for k,a in audits.items() if not a['exclusion_reasons']}
        matched=[(aid,sid) for aid,sid in matched if aid in valid]
    recovered={};coverage={};basecoverage={};frozen_coverage={}
    if matched:
        mapping=facts.sparkSession.createDataFrame(matched,['attempt_id','source_id'])
        relevant=evidence.select('case_id','source_id').join(mapping,'source_id').groupBy('attempt_id','case_id').count()
        # Only reference-overlapping case summaries reach the driver; cap and fail,
        # never truncate or silently remove candidates from an eligible denominator.
        joined_cases=relevant.join(index.select('case_id','pattern_type','hub','ordered_nodes'),'case_id').limit(100001).collect()
        if len(joined_cases)>100000:raise ValueError('Annotation-overlapping case guard exceeded')
        from evaluate_q2 import node
        for r in joined_cases:
            a=audits[r['attempt_id']];shape=a['shape'];same=r['pattern_type']==shape['pattern_type'] and r['hub']==shape['hub']
            if shape['pattern_type'].startswith('cycle_'):
                nodes=r['ordered_nodes'];same=same and set(zip(nodes,nodes[1:]+nodes[:1]))==set(shape['edges'])
            if same and 5*r['count']>=4*a['annotation_transaction_count']:recovered[r['attempt_id']]=True
        for frame,target in ((alerts,coverage),(matched_baseline,basecoverage),(baseline,frozen_coverage)):
            for row in mapping.join(frame,'source_id').groupBy('attempt_id').count().collect():target[row['attempt_id']]=5*row['count']>=4*audits[row['attempt_id']]['annotation_transaction_count']
    eligible_n=hits=0
    for aid,a in audits.items():
        a['eligible']=not a['exclusion_reasons'];a['exclusion_reasons']=sorted(set(a['exclusion_reasons']))
        a.pop('shape',None)
        if a['eligible']:
            eligible_n+=1;hits+=int(recovered.get(aid,False));a.update(recovered=recovered.get(aid,False),detector_coverage_80pct=coverage.get(aid,False),amount_coverage_80pct=basecoverage.get(aid,False),frozen_amount_coverage_80pct=frozen_coverage.get(aid,False))
    pattern_rows=(evidence.select('case_id','source_id').join(index.select('case_id','pattern_type'),'case_id').select('source_id','pattern_type').distinct()
      .join(eligible.select('source_id','is_laundering'),'source_id').groupBy('pattern_type').agg(F.count('*').alias('n'),F.sum('is_laundering').alias('tp')).collect())
    per_pattern={r['pattern_type']:r for r in pattern_rows}
    volumes={r['pattern_type']:r['count'] for r in index.groupBy('pattern_type').count().collect()}
    pattern_metrics=[]
    for kind in ('fan_in','fan_out','cycle_2','cycle_3','cycle_4'):
        eligible_attempts=[a for a in audits.values() if a['eligible'] and a['pattern_type']==kind]
        recovered_n=sum(bool(a['recovered']) for a in eligible_attempts);pr=per_pattern.get(kind)
        pattern_metrics.append({'pattern_type':kind,'case_count':volumes.get(kind,0),'eligible_annotated_attempts':len(eligible_attempts),'recovered_attempts':recovered_n,
          'attempt_recovery':recovered_n/len(eligible_attempts) if eligible_attempts else None,
          'transaction_metrics':metrics(detector_metrics['population'],detector_metrics['positive_labels'],pr['n'] if pr else 0,pr['tp'] if pr else 0)})
    return {'schema_version':2,'benchmark_status':('sparse_tail' if score_start>=datetime(2022,9,17) else 'frozen_holdout') if holdout else 'development_calibration',
       'scoring_window':{'start_inclusive':score_start.isoformat(),'end_exclusive':score_end.isoformat()},'detector_history_population':detector['statistics']['scoped_rows'],
       'detector_transaction_metrics':detector_metrics,'amount_baseline_transaction_metrics':baseline_metrics,'frozen_amount_baseline_transaction_metrics':frozen_baseline_metrics,'pattern_metrics':pattern_metrics,
       'annotation_metrics':{'total_file_attempts':len(attempts),'eligible_attempts':eligible_n,'recovered_attempts':hits,'attempt_recovery':hits/eligible_n if eligible_n else None,
           'detector_type_agnostic_coverage_80pct':sum(coverage.values())/eligible_n if eligible_n else None,'amount_baseline_coverage_80pct':sum(basecoverage.values())/eligible_n if eligible_n else None,'frozen_amount_baseline_coverage_80pct':sum(frozen_coverage.values())/eligible_n if eligible_n else None},
       'currency_population_and_alert_budgets':[r.asDict() for r in audit.collect()], 'attempt_evaluation':list(audits.values()),
       'full_prepared_rows_reconciled':expected,'case_count':index.count()}


def freeze_calibration(results,development_analyses,min_counterparties,max_cycle_degree):
    """Use development alert volume, never holdout answers, to freeze the baseline."""
    from collections import defaultdict
    totals=defaultdict(lambda:[0,0])
    if not results or len(results)!=len(development_analyses):raise ValueError('Require every declared development evaluation')
    for result in results:
        if result['benchmark_status']!='development_calibration':raise ValueError('Only development may calibrate')
        for row in result['currency_population_and_alert_budgets']:
            totals[row['payment_currency']][0]+=row['population'];totals[row['payment_currency']][1]+=row['budget']
    policy={'schema_version':1,'frozen':True,'rule_version':'structural-v2','min_counterparties':min_counterparties,'max_cycle_degree':max_cycle_degree,
       'development_analyses':development_analyses,'amount_alert_fraction_by_currency':{c:str((Decimal(a)/Decimal(n)).quantize(Decimal('.000000000001'))) for c,(n,a) in sorted(totals.items())},
       'recovery_improvement_target_pp':5,'improvement_target':'At least 5 percentage points higher typed eligible-attempt recovery than matched-volume amount coverage. Also report the frozen development-fraction baseline and transaction precision. Report unmet/no-denominator targets honestly; no retuning after holdout.'}
    validate_calibration(policy,{'min_counterparties':min_counterparties,'max_cycle_degree':max_cycle_degree})
    return policy


def evaluation_suffix(config,evaluation_id,attempt_id=''):
    from q2_detect import Config
    Config(config['dataset_version'],config['run_id'],evaluation_id,config['window_start'],config['window_end'],config['snapshot_cutoff']).times()
    from pipeline.release import safe_id
    safe_id(config['analysis_id'])
    if attempt_id:safe_id(attempt_id)
    suffix=f"dataset_version={config['dataset_version']}/run_id={config['run_id']}/analysis_id={config['analysis_id']}/evaluation_id={evaluation_id}/"
    return suffix+('attempt='+attempt_id+'/' if attempt_id else '')


def main():
    import argparse,boto3
    from datetime import timezone
    from urllib.parse import urlparse
    from pyspark.sql import SparkSession
    p=argparse.ArgumentParser()
    for name in ('preparation-report','detector-report','annotations','annotations-sha256','output-root','evaluation-id'):
        p.add_argument('--'+name,required=True)
    p.add_argument('--attempt-id',default='')
    args,_=p.parse_known_args();s3=boto3.client('s3',region_name='us-east-1')
    def read(uri,limit=5_000_000):
        loc=urlparse(uri)
        if loc.scheme!='s3':raise ValueError('Explicit S3 input required')
        response=s3.get_object(Bucket=loc.netloc,Key=loc.path.lstrip('/'))
        try:body=response['Body'].read(limit+1)
        finally:response['Body'].close()
        if len(body)>limit:raise ValueError('Evaluator input metadata exceeds bound')
        return body
    prep=json.loads(read(args.preparation_report));detector=json.loads(read(args.detector_report));config=detector['config']
    if any(config[k]!=prep[k] for k in ('dataset_version','run_id')):raise ValueError('Foreign preparation/detection inputs')
    annotations=parse_annotations(read(args.annotations).decode(),args.annotations_sha256)
    out=urlparse(args.output_root)
    if out.scheme!='s3':raise ValueError('Explicit output root required')
    base=out.path.strip('/');base=base+'/' if base else ''
    suffix=evaluation_suffix(config,args.evaluation_id,args.attempt_id)
    prefix=base+'evaluation/'+suffix;qualitykey=base+'quality/evaluation/'+suffix+'report.json'
    for key in (prefix,base+'quality/evaluation/'+suffix):
        if s3.list_objects_v2(Bucket=out.netloc,Prefix=key,MaxKeys=1).get('KeyCount',0):raise ValueError('Fresh evaluation attempt required')
    def put(name,value):
        body=(json.dumps(value,indent=2,default=str)+'\n').encode();key=prefix+name
        s3.put_object(Bucket=out.netloc,Key=key,Body=body,IfNoneMatch='*',ContentType='application/json')
        return {'uri':f's3://{out.netloc}/{key}','bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
    report={'schema_version':2,'stage':'evaluation','status':'FAILED','dataset_version':config['dataset_version'],'run_id':config['run_id'],
      'evaluation_id':args.evaluation_id,'attempt_id':args.attempt_id,'detector_analysis_id':config['analysis_id'],'detector_report_sha256':hashlib.sha256(read(args.detector_report)).hexdigest()}
    spark=SparkSession.builder.appName('is459-evaluation-distributed').config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','64').getOrCreate()
    try:
        def clear_blocks():
            spark.catalog.clearCache()
            blocks=spark.sparkContext._jsc.sc().getPersistentRDDs().values().iterator()
            while blocks.hasNext():blocks.next().unpersist(False)
        facts=spark.read.parquet(prep['outputs']['transactions']);labels=spark.read.parquet(prep['outputs']['labels'])
        from pyspark.sql.types import StructType
        index=spark.read.schema(StructType.fromJson(detector['case_index_schema'])).parquet(detector['outputs']['case_index']);pairs=spark.read.parquet(detector['outputs']['case_edges']);evidence=spark.read.parquet(detector['outputs']['case_evidence'])
        development=evaluate(facts,labels,index,pairs,evidence,prep,detector,annotations,scoring_window=('2022-09-01T00:00:00','2022-09-09T00:00:00'))
        dev_ref=put('development.json',development)
        policy=freeze_calibration([development],[{'analysis_id':config['analysis_id'],'window_start':'2022-09-01T00:00:00','window_end':'2022-09-09T00:00:00','development_metrics':dev_ref}],config['min_counterparties'],config['max_cycle_degree'])
        calibration=put('calibration-frozen.json',policy)
        clear_blocks()
        # This conditional write is complete before any holdout scoring call.
        holdout=evaluate(facts,labels,index,pairs,evidence,prep,detector,annotations,calibration=policy,scoring_window=('2022-09-09T00:00:00','2022-09-17T00:00:00'))
        clear_blocks()
        tail=evaluate(facts,labels,index,pairs,evidence,prep,detector,annotations,calibration=policy,scoring_window=('2022-09-17T00:00:00','2022-09-29T00:00:00'))
        artifacts={'development.json':dev_ref,'calibration-frozen.json':calibration,'holdout.json':put('holdout.json',holdout),'sparse-tail.json':put('sparse-tail.json',tail)}
        total=sum(x['detector_transaction_metrics']['population'] for x in (development,holdout,tail))
        positive=sum(x['detector_transaction_metrics']['positive_labels'] for x in (development,holdout,tail))
        if total!=prep['accepted_rows']:raise ValueError('Non-overlapping scoring periods do not account for all accepted facts')
        target=holdout['annotation_metrics'];amount=target['amount_baseline_coverage_80pct'];recovery=target['attempt_recovery']
        summary={k:v for k,v in holdout.items() if k!='attempt_evaluation'}
        summary.update(evaluation_id=args.evaluation_id,full_input_rows_accounted=total,sparse_tail_report=artifacts['sparse-tail.json'],development_report=dev_ref,
          calibration=calibration,improvement_target=policy['improvement_target'],recovery_improvement_percentage_points=100*(recovery-amount) if recovery is not None and amount is not None else None,improvement_target_met=100*(recovery-amount)>=policy['recovery_improvement_target_pp'] if recovery is not None and amount is not None else None,
          limitations=['Structural leads are not proof of laundering. Cycle exclusions are declared in each snapshot. Development, holdout and sparse tail are scored separately; historical context never adds future cases to earlier metrics.'])
        artifacts['metrics.json']=put('metrics.json',summary)
        report.update(status='PASSED',artifacts=artifacts,benchmark_status='separate_development_frozen_holdout_sparse_tail',
          full_prepared_rows_reconciled=prep['accepted_rows'],eligible_transactions=total,eligible_positive_labels=positive,
          case_count=detector['statistics']['case_count'],eligible_annotated_attempts=holdout['annotation_metrics']['eligible_attempts'],
          frozen_calibration_sha256=calibration['sha256'],calibration=calibration,holdout_evaluation_complete=True)
    except Exception as error:report.update(error_type=type(error).__name__,error=str(error)[:2000]);raise
    finally:
        report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        s3.put_object(Bucket=out.netloc,Key=qualitykey,Body=(json.dumps(report,indent=2)+'\n').encode(),IfNoneMatch='*',ContentType='application/json');spark.stop()

if __name__=='__main__':main()
