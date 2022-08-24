import os
import json
import boto3

from smart_open import s3
from smart_open import open

def handle(event, context):
    bucketName = os.getenv('s3_bucket')

    with open('/var/openfaas/secrets/s3-key', 'r') as s:
        s3Key = s.read()
    with open('/var/openfaas/secrets/s3-secret', 'r') as s:
        s3Secret = s.read()

    session = boto3.Session(
        aws_access_key_id=s3Key,
        aws_secret_access_key=s3Secret,
    )

    batchId = event.headers.get('X-Batch-Id')
    batchStarted = event.headers.get('X-Batch-Started')
    batchCompleted = event.headers.get('X-Batch-Completed')

    passed = []
    failed = []
    
    for key, content in s3.iter_bucket(bucketName, prefix=batchId + '/', workers=30, aws_access_key_id=s3Key, aws_secret_access_key=s3Secret):
        data = json.loads(content)
        if (data['status'] == 'error'):
            failed.append({ 'url': data['url'], 'statusCode': data['statusCode'], 'result': data['result'] })
        else:
            passed.append({ 'url': data['url'], 'statusCode': data['statusCode'] , 'result': data['result'] })

    summary = {
        'batchId': batchId,
        'batchStarted': batchStarted,
        'batchCompleted': batchCompleted,
        'failed': {
            'count': len(failed),
            'results': failed
        },
        'passed': {
            'count': len(passed),
            'results': passed,
        }
    }

    fileName = 'output.json'
    s3URL = "s3://{}/{}/{}".format(bucketName, batchId, fileName)
    with open(s3URL, 'w', transport_params={'client': session.client('s3')}) as fout:
        json.dump(summary, fout)
    
    return {
        "statusCode": 200,
        "body": 'Processed batch: {}'.format(batchId)
    }
