# Fan-out/fan-in pattern with OpenFaaS
This repo contains an example of how to fan out and back using OpenFaaS.

## How to run it?
### Setup dependencies
S3 is used as a data store so will need to create an S3 bucket that the functions can use.
You can use [amazon S3](https://aws.amazon.com/s3/), [minio](https://min.io/) or any other S3 compatible object storage.

Redis is used to keep track of the work that is done on each batch.
You can deploy redis using `arkade`
```bash
arkade install redis
```

### Add secrets
Make sure the required secrets are available for the functions.

S3 credentials:

```bash
echo $access_key_id | faas-cli secret create s3-key
echo $secret_access_key | faas-cli secret create s3-secret
```

Redis password:

```bash
export REDIS_PASSWORD=$(kubectl get secret --namespace redis redis -o jsonpath="{.data.redis-password}" | base64 --decode)

echo $REDIS_PASSWORD | faas-cli secret create redis-password
```

### Set env variables
The `env.yml` file contains some env variables used by the function like the name of the bucket that should be used and the redis hostname. Update this file with your values.

```yaml
environment:
  redis_hostname: "redis-master.redis.svc.cluster.local"
  redis_port: 6379
  s3_bucket: of-demo-inception-data
```

### Deploy
Deploy the stack.

```bash
faas-cli template pull stack
```

```bash
faas-cli deploy
```

### Run with example data
The data folder contains multiple csv files that can be used as input for a batch job. Upload them to your S3 bucket.

Invoke the function `creat-batch` with the name of the source file you want to start processing.
```bash
curl -i  http://127.0.0.1:8080/function/create-batch -d batch1.csv

HTTP/1.1 201 Created
Content-Type: text/html; charset=utf-8
Date: Wed, 17 Aug 2022 15:19:56 GMT
Server: waitress
X-Call-Id: 4121651e-8bd4-470a-8ad3-70ecd68b8194
X-Duration-Seconds: 0.387640
X-Start-Time: 1660749596315319961
Content-Length: 69

{"batch_id": "55f22778-675f-4a85-8e1c-5d777faa4399", "batch_size": 200}%  
```
