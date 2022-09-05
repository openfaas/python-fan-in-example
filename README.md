# Fan-out/fan-in pattern with OpenFaaS
This repo contains an example of how to fan out and back in using OpenFaaS.

> The complete write up for this example is published on the OpenFaaS blog:
> - [Exploring the Fan out and Fan in pattern with OpenFaaS](https://www.openfaas.com/blog/fan-out-and-back-in-using-functions/)

In the example a csv file containing image urls is used is the input for a batch job. The inception function is called for each url and categorizations are returned through machine learning. The result of each invocation is stored in an S3 bucket. When the batch is completed a final function is called that aggregates and summarizes the results. The summary is stored in the S3 bucket.

![Screenshot of the queue-worker metrics, aws S3 console showing individual function results and a json file with the final results of the batch job.](https://pbs.twimg.com/media/FahM5rCVEAESamf?format=jpg&name=medium)

## How to run it?
### Setup dependencies
S3 is used as a data store. You will need to create an S3 bucket that the functions can use. This example uses a bucket named `of-demo-inception-data` replace any references to this bucket with your own bucket name.

Redis is used to keep track of the completed work by decrementing a counter for each batch.
You can deploy redis using `arkade`
```bash
arkade install redis
```

### Add secrets
Make sure the required secrets are available for the functions.

S3 credentials:

```bash
echo $aws_access_key_id | faas-cli secret create s3-key
echo $aws_secret_access_key | faas-cli secret create s3-secret
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

### Deploy the functions
Deploy the stack.

```bash
faas-cli template pull stack
```

```bash
faas-cli deploy
```

### Run with example data
The [data](./data) folder has several csv files containing urls that can be used as data source for this example.
```
data
├── batch-200.csv # 200 records
├── batch-500.csv # 500 records
├── batch-1000.csv # 1000 records
└── batch-2000.csv # 2000 records
```

The `create-batch` function looks for the input files in the S3 bucket. Upload them to your S3 bucket.

```bash
aws s3 cp data/batch-200.csv s3://of-demo-inception-data/data/batch-200.csv
```

Invoke the function `create-batch` with the name of the source file you want to start processing.
```bash
curl -i  http://127.0.0.1:8080/function/create-batch -d data/batch-200.csv

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
