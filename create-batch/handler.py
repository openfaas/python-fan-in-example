import os
import json
import time
import uuid
import redis
import requests
import pandas as pd
import boto3

from smart_open import open

redisClient = None
s3Client = None

def initS3():
    with open('/var/openfaas/secrets/s3-key', 'r') as s:
        s3Key = s.read()
    with open('/var/openfaas/secrets/s3-secret', 'r') as s:
        s3Secret = s.read()

    session = boto3.Session(
        aws_access_key_id=s3Key,
        aws_secret_access_key=s3Secret,
    )
    
    return session.client('s3')

def initRedis():
    redisHostname = os.getenv('redis_hostname', default='redis-master.redis.svc.cluster.local')
    redisPort = os.getenv('redis_port')

    with open('/var/openfaas/secrets/redis-password', 'r') as s:
        redisPassword = s.read()

    return redis.Redis(
        host=redisHostname,
        port=redisPort,
        password=redisPassword,
    )

def handle(event, context):
    global s3Client, redisClient

    if s3Client == None:
        s3Client = initS3()

    if redisClient == None:
        redisClient = initRedis()
    
    bucketName = os.getenv('s3_bucket')

    batchFile = event.body.decode()
    s3URL = 's3://{}/{}'.format(bucketName, batchFile)
    with open(s3URL, 'rb', transport_params={'client': s3Client }) as f:
        records = pd.read_csv(f)

    batchId = str(uuid.uuid4())
    batchSize = len(records)
    batchStarted = time.time()

    redisClient.set(batchId, batchSize)

    for index, col in records.iterrows():
        headers = { 'X-Batch-Id': batchId, 'X-Batch-Started': str(batchStarted) }
        res = requests.post('http://gateway.openfaas:8080/async-function/run-model', data=col['url'], headers=headers)

    response = {
        'batch_id': batchId,
        'batch_size': batchSize
    }

    return {
        "statusCode": 201,
        "body": json.dumps(response)
    }
