import os
import json
import uuid
import redis
import requests
import pandas as pd
import boto3

from smart_open import open

def handle(event, context):
    redisHostname = os.getenv('redis_hostname', default='redis-master.redis.svc.cluster.local')
    redisPort = os.getenv('redis_port')
    bucketName = os.getenv('s3_bucket')
    
    with open('/var/openfaas/secrets/redis-password', 'r') as s:
        redisPassword = s.read()
    with open('/var/openfaas/secrets/s3-key', 'r') as s:
        s3Key = s.read()
    with open('/var/openfaas/secrets/s3-secret', 'r') as s:
        s3Secret = s.read()

    r = redis.Redis(
        host=redisHostname,
        port=redisPort,
        password=redisPassword,
    )

    session = boto3.Session(
        aws_access_key_id=s3Key,
        aws_secret_access_key=s3Secret,
    )

    batchFile = event.body.decode()
    s3URL = 's3://{}/{}'.format(bucketName, batchFile)
    with open(s3URL, 'rb', transport_params={'client': session.client('s3')}) as f:
        records = pd.read_csv(f)

    batchId = str(uuid.uuid4())
    batchSize = len(records)

    r.set(batchId, batchSize)

    for index, col in records.iterrows():
        headers = { 'X-Batch-Id': batchId }
        res = requests.post('http://gateway.openfaas:8080/async-function/run-model', data=col['url'], headers=headers)

    response = {
        'batch_id': batchId,
        'batch_size': batchSize
    }

    return {
        "statusCode": 201,
        "body": json.dumps(response)
    }
