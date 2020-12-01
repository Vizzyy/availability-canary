import boto3
import os
import urllib3

# Setup outside of handler so it only executes once per container
ssm = boto3.client('ssm')
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

conn = urllib3.connection_from_url(
    os.environ.get('lambda-availability-route'),
    cert_file='/tmp/lambda-cert',
    key_file='/tmp/lambda-key'
)


def lambda_handler(event=None, context=None):
    response = conn.request('GET', os.environ.get('WEBSITE_URL'), timeout=5.0)

    result = {
        'status': response.status,
        'body': response.data
    }

    print(f"Result status: {result['status']}")

    if response.status == 404:
        print("Encountered Server Error.")
        print(vars(response))
        raise RuntimeError

    return result


if os.environ.get('ENV') == "dev":
    # Run natively during development
    lambda_handler()
