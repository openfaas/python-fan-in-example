import os
import redis
import requests
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

    batchId = event.headers.get('X-Batch-Id')

    res = requests.get("http://gateway.openfaas:8080/function/inception", data=event.body)

    if res.status_code != 200:
        return {
            "statusCode": res.status_code,
            "body": "Failed to run model"
        }

    callId = res.headers.get('X-Call-Id')

    fileName = '{}/{}.json'.format(batchId, callId)
    s3URL = "s3://{}/{}".format(bucketName, fileName)
    with open(s3URL, 'wb', transport_params={'client': session.client('s3')}) as fout:
        fout.write(res.content)

    remainingWork = r.decr(batchId)

    if remainingWork == 0:
        headers = { 'X-Batch-Id': batchId, 'X-Callback-Url': 'https://requestbin.io/v51kfiv5'}
        res = requests.post("http://gateway.openfaas:8080/async-function/env", headers=headers)
        r.delete(batchId)

    return {
        "statusCode": 200,
        "body": "Success running model"
    }
