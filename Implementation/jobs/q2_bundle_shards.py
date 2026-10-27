"""Schema-v3 case bundles packed into bounded, immutable ZIP shards.

Packing changes storage only. Every original evidence row and case is retained;
case IDs, motif rules, scoring windows and labels are unaffected.
"""
import hashlib,io,json,itertools,zipfile
from q2_detect import DETECTOR_COLUMNS,_json_default

SHARD_BYTES=8_000_000
CHUNK_BYTES=1_000_000


def export_shards(rows,bucket,prefix,snapshot,partition,profile=None,region='us-east-1',shard_bytes=SHARD_BYTES):
    import boto3
    from botocore.exceptions import ClientError
    session=boto3.Session(profile_name=profile,region_name=region) if profile else boto3.Session(region_name=region)
    s3=session.client('s3');sequence=0;buffer=None;archive=None;size=0
    def uri():return f's3://{bucket}/{prefix}bundles/shards/{snapshot}/partition-{partition:05d}-{sequence:06d}.zip'
    def flush():
        nonlocal archive,buffer,size,sequence
        if archive is None:return
        archive.close();body=buffer.getvalue()
        if len(body)>10_000_000:raise ValueError('Compressed shard exceeds read bound')
        key=uri().split(f's3://{bucket}/',1)[1];digest=hashlib.sha256(body).hexdigest()
        try:s3.put_object(Bucket=bucket,Key=key,Body=body,IfNoneMatch='*',ContentType='application/zip',Metadata={'sha256':digest})
        except ClientError as error:
            if error.response['Error']['Code'] not in ('PreconditionFailed','412'):raise
            old=s3.get_object(Bucket=bucket,Key=key)['Body'].read()
            if hashlib.sha256(old).hexdigest()!=digest:raise ValueError('Conflicting immutable shard retry')
        buffer=None;archive=None;size=0;sequence+=1
    def add(member,body):
        nonlocal archive,buffer,size
        if len(body)>shard_bytes:raise ValueError('Single shard member exceeds export bound')
        if archive is not None and size+len(body)>shard_bytes:flush()
        if archive is None:
            buffer=io.BytesIO();archive=zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED)
        info=zipfile.ZipInfo(member,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        archive.writestr(info,body);size+=len(body)
        return {'uri':uri(),'member':member,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
    for case_id,group in itertools.groupby(rows,key=lambda r:r['case_id']):
        parts=[];chunk=[];chunk_bytes=0;count=0;nodes={};edges={};preview=[];first=None
        def write_chunk():
            nonlocal chunk,chunk_bytes
            if not chunk:return
            raw=('\n'.join(chunk)+'\n').encode();ref=add(f'evidence/{case_id}/part-{len(parts):06d}.jsonl',raw)
            ref['rows']=len(chunk);parts.append(ref);chunk=[];chunk_bytes=0
        for row in group:
            data=row.asDict(recursive=True)
            if first is None:first=data
            tx={k:data[k] for k in DETECTOR_COLUMNS if k not in ('dataset_version','run_id')}
            line=json.dumps(tx,default=_json_default,sort_keys=True);length=len(line.encode())+1
            if length>CHUNK_BYTES:raise ValueError('Single evidence row exceeds export bound')
            if chunk_bytes+length>CHUNK_BYTES:write_chunk()
            chunk.append(line);chunk_bytes+=length;count+=1
            if len(preview)<200:preview.append(tx)
            for side in ('sender','receiver'):
                nid=data['src' if side=='sender' else 'dst']
                if nid in nodes or len(nodes)<100:
                    nodes[nid]={'node_id':nid,'bank':data[side+'_bank'],'account':data[side+'_account'],
                       'entity_id':data[side+'_entity_id'],'entity_name':data[side+'_entity_name'],'entity_unknown':data[side+'_entity_unknown']}
            pair=(data['src'],data['dst'])
            if pair in edges:edges[pair]+=1
            elif len(edges)<500 and all(n in nodes for n in pair):edges[pair]=1
        write_chunk()
        if count!=first['evidence_transaction_count']:raise ValueError('Case evidence differs from distributed index')
        header={k:first[k] for k in ('case_id','pattern_type','hub','ordered_nodes','participant_count','unique_edge_count','evidence_transaction_count',
            'first_event_time','last_event_time','dataset_version','run_id','analysis_id','rule_version','window_start','window_end','snapshot_cutoff')}
        header.update(schema_version=3,nodes=list(nodes.values()),edges=[{'source':a,'target':b,'transaction_count':n} for (a,b),n in sorted(edges.items())],
          transactions=preview,evidence_parts=parts,display_capped=len(nodes)<first['participant_count'] or len(edges)<first['unique_edge_count'] or count>200,
          interpretation='Structural investigation lead; cycles are limited to the declared degree-eligible graph. No claim of laundering or chronological return of identical funds.')
        raw=(json.dumps(header,default=_json_default,sort_keys=True)+'\n').encode();ref=add(case_id+'.json',raw)
        yield (case_id,ref['uri'],ref['member'],ref['sha256'])
    flush()
