import os
import json
import time
import redis
import requests
import boto3

from smart_open import open

s3Client = None
redisClient = None

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

    batchId = event.headers.get('X-Batch-Id')
    url = event.body.decode()

    res = requests.get("http://gateway.openfaas:8080/function/inception", data=url)

    callId = res.headers.get('X-Call-Id')
    status = 'success' if res.status_code == 200 else 'error'
    result = res.json() if res.status_code == 200 else res.text
    taskResult = {
        'batchId': batchId,
        'callId': callId,
        'statusCode': res.status_code,
        'url': url,
        'result': result,
        'status': status,
    }

    fileName = '{}/{}.json'.format(batchId, callId)
    s3URL = "s3://{}/{}".format(bucketName, fileName)
    with open(s3URL, 'w', transport_params={'client': s3Client }) as fout:
        json.dump(taskResult, fout)

    remainingWork = redisClient.decr(batchId)

    if remainingWork == 0:
        batchCompleted = time.time()
        batchStarted = event.headers.get('X-Batch-Started')

        headers = { 'X-Batch-Id': batchId, 'X-Batch-Started': batchStarted, 'X-Batch-Completed': str(batchCompleted) }
        res = requests.post("http://gateway.openfaas:8080/async-function/collect-result", headers=headers)
        redisClient.delete(batchId)

    return {
        "statusCode": 200,
        "body": "Success running model"
    }
