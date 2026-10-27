"""Upload one new full ingestion copy with conditional multipart completion."""
import argparse,base64,hashlib,json,subprocess
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from build_stack import ACCOUNT,REGION,BUCKET
ROOT=Path(__file__).resolve().parents[2]


def main():
 p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--region',default=REGION)
 p.add_argument('--input',type=Path,default=ROOT/'Implementation/data/full-20220901-29-v1');args=p.parse_args()
 subprocess.run(['bash','Implementation/scripts/check_aws_profile.sh',args.profile],cwd=ROOT,check=True)
 s=boto3.Session(profile_name=args.profile,region_name=args.region)
 if args.region!=REGION or s.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong project account/region')
 s3=s.client('s3');manifest=json.loads((args.input/'manifest.json').read_text());counts=manifest['counts']
 if counts['source_records']!=31898238 or counts['selected_records']!=31898238 or counts['outside_development_scope'] or counts['ingestion_quarantined']:
  raise ValueError('Require complete verified original-file accounting')
 if manifest['dataset_version']!='ibm-hi-medium-b1b99c68b765580f':raise ValueError('Unexpected dataset identity')
 encryption=s3.get_bucket_encryption(Bucket=BUCKET,ExpectedBucketOwner=ACCOUNT)
 if encryption['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']!='AES256':raise ValueError('Unexpected bucket encryption')
 block=s3.get_public_access_block(Bucket=BUCKET,ExpectedBucketOwner=ACCOUNT)['PublicAccessBlockConfiguration']
 if not all(block.values()):raise ValueError('Project bucket must remain private')
 observed={}
 for name,info in manifest['artifacts'].items():
  path=args.input/name;key='raw/full-v1/'+name
  try:head=s3.head_object(Bucket=BUCKET,Key=key,ExpectedBucketOwner=ACCOUNT)
  except ClientError as e:
   if e.response['Error']['Code'] not in ('404','NoSuchKey'):raise
   head=None
  if head is not None:
   if head['ContentLength']!=info['size_bytes'] or head.get('Metadata',{}).get('sha256')!=info['sha256']:raise ValueError('Conflicting existing full input object')
   observed[name]={'status':'existing exact size/hash metadata; no overwrite',**info};continue
  if path.stat().st_size==0:
   s3.put_object(Bucket=BUCKET,Key=key,Body=b'',IfNoneMatch='*',ServerSideEncryption='AES256',Metadata={'sha256':info['sha256']},ExpectedBucketOwner=ACCOUNT)
   observed[name]={'status':'new empty quarantine artifact',**info};continue
  created=s3.create_multipart_upload(Bucket=BUCKET,Key=key,ServerSideEncryption='AES256',ChecksumAlgorithm='SHA256',Metadata={'sha256':info['sha256']},ExpectedBucketOwner=ACCOUNT)
  upload_id=created['UploadId'];parts=[];whole=hashlib.sha256()
  try:
   with path.open('rb') as f:
    while body:=f.read(16*1024*1024):
     whole.update(body);checksum=base64.b64encode(hashlib.sha256(body).digest()).decode();number=len(parts)+1
     response=s3.upload_part(Bucket=BUCKET,Key=key,UploadId=upload_id,PartNumber=number,Body=body,ChecksumSHA256=checksum,ExpectedBucketOwner=ACCOUNT)
     if response.get('ChecksumSHA256')!=checksum:raise ValueError('Server part checksum differs')
     parts.append({'PartNumber':number,'ETag':response['ETag'],'ChecksumSHA256':checksum})
   if whole.hexdigest()!=info['sha256']:raise ValueError('Local artifact changed during upload')
   result=s3.complete_multipart_upload(Bucket=BUCKET,Key=key,UploadId=upload_id,MultipartUpload={'Parts':parts},IfNoneMatch='*',ExpectedBucketOwner=ACCOUNT)
   head=s3.head_object(Bucket=BUCKET,Key=key,ExpectedBucketOwner=ACCOUNT)
   if head['ContentLength']!=info['size_bytes']:raise ValueError('Uploaded object size differs')
   observed[name]={'status':'new conditional upload; every part checksum verified by S3; local whole-file hash matched',**info,'parts':len(parts),'server_composite_checksum_sha256':result.get('ChecksumSHA256')}
  except Exception:
   s3.abort_multipart_upload(Bucket=BUCKET,Key=key,UploadId=upload_id,ExpectedBucketOwner=ACCOUNT);raise
  print('Verified full input '+name,flush=True)
 raw=(args.input/'manifest.json').read_bytes();key='raw/full-v1/manifest.json'
 try:s3.put_object(Bucket=BUCKET,Key=key,Body=raw,IfNoneMatch='*',ContentType='application/json',ServerSideEncryption='AES256',ExpectedBucketOwner=ACCOUNT)
 except ClientError as e:
  if e.response['Error']['Code'] not in ('PreconditionFailed','412'):raise
 if s3.get_object(Bucket=BUCKET,Key=key,ExpectedBucketOwner=ACCOUNT)['Body'].read()!=raw:raise ValueError('Input manifest differs')
 record={'dataset_version':manifest['dataset_version'],'counts':counts,'destination':'s3://'+BUCKET+'/raw/full-v1/','objects':observed,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'originals_changed':False,'paid_processing_started':False}
 (ROOT/'Implementation/aws/reviews/full-input-upload.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

if __name__=='__main__':main()
