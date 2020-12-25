import datetime
import boto3
import os
import urllib3
import json

# Setup outside of handler so it only executes once per container
ssm = boto3.client('ssm')
sqs = boto3.client('sqs')

paginator = ssm.get_paginator('get_parameters_by_path')
iterator = paginator.paginate(Path=os.environ.get('SSM_PATH'), WithDecryption=True)
params = []

for page in iterator:
    params.extend(page['Parameters'])
    for param in page.get('Parameters', []):
        # Load all SSM params into environment
        os.environ[param.get('Name').split('/')[-1]] = param.get('Value')

for param in params:
    print(param["Name"])

# Write SSL client cert/key into container
with open('/tmp/lambda-cert', 'w') as file:
    file.write(os.environ["lambda-cert"])

with open('/tmp/lambda-key', 'w') as file:
    file.write(os.environ["lambda-key"])

with open('/tmp/db-cert', 'w') as file:
    file.write(os.environ["db-cert"])

routes = os.environ.get('lambda-availability-route').split(',')

conn = urllib3.connection_from_url(
    os.environ.get('lambda-availability-host'),
    cert_file='/tmp/lambda-cert',
    key_file='/tmp/lambda-key'
)


def sqs_send(start_time: datetime, target_route: str, success: bool = True):
    queue_url = os.environ["queue-url"]
    now = datetime.datetime.now()
    elapsed = now - start_time
    elapsed_ms = elapsed.total_seconds() * 1000  # elapsed milliseconds
    path = target_route.split(".com")[1]

    message = {
        "action": "insert",
        "table": "canary_metrics",
        "values": {
            "path": path,
            "ms_elapsed": elapsed_ms,
            "timestamp": now.__str__(),
            "success": success
        }
    }

    # Send message to SQS queue
    response = sqs.send_message(QueueUrl=queue_url, MessageBody=(json.dumps(message)))
    print(response)
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        raise RuntimeError("Could not enqueue message!")


def lambda_handler(event=None, context=None):
    start_time = datetime.datetime.now()
    target_route = routes[int(os.environ.get('INDEX'))]
    print(f"Checking route: {target_route}")

    response = conn.request('GET', target_route, timeout=5.0)

    result = {
        'status': response.status,
        'body': response.data
    }

    print(f"Result status: {result['status']}")

    if response.status != 200:
        print("Encountered Server Error.")
        print(vars(response))
        sqs_send(start_time, target_route, False)
        raise RuntimeError

    sqs_send(start_time, target_route, True)

    return result


if os.environ.get('ENV') == "dev":
    # Run natively during development
    lambda_handler()
