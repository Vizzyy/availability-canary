import datetime

import boto3
import os
import urllib3
import ssl
from mysql.connector.constants import ClientFlag
import mysql.connector
import json

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

with open('/tmp/db-cert', 'w') as file:
    file.write(os.environ["db-cert"])

routes = os.environ.get('lambda-availability-route').split(',')

conn = urllib3.connection_from_url(
    os.environ.get('lambda-availability-host'),
    cert_file='/tmp/lambda-cert',
    key_file='/tmp/lambda-key'
)

secrets_object = json.loads(os.environ["secrets"])

SSL_CONFIG = {
    'user': secrets_object["grafana"]["DB_USER"],
    'password': secrets_object["grafana"]["DB_PASS"],
    'host': secrets_object["grafana"]["DB_HOST"],
    'port': secrets_object["grafana"]["DB_PORT"],
    'database': 'graphing_data',
    'client_flags': [ClientFlag.SSL],
    'ssl_ca': '/tmp/db-cert',
}
db = mysql.connector.connect(**SSL_CONFIG)
db._ssl['version'] = ssl.PROTOCOL_TLSv1_2
cursor = db.cursor()
print("Connected to Database!")


def store_log(start_time, success, failure, id):
    try:
        now = datetime.datetime.now()
        elapsed = now - start_time
        elapsed_ms = elapsed.total_seconds() * 1000  # elapsed milliseconds
        path = id.split(".com")[1]

        sql = f"INSERT INTO graphing_data.canary_metrics(path, ms_elapsed, timestamp, error, success) " \
              f"VALUES('{path}', '{elapsed_ms}', '{now}', '{failure}', '{success}')"
        cursor.execute(sql)
        db.commit()
        print(f"{sql}")
    except Exception as e:
        print(e)


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
        store_log(start_time, 0, 1, target_route)
        raise RuntimeError

    store_log(start_time, 1, 0, target_route)

    return result


if os.environ.get('ENV') == "dev":
    # Run natively during development
    lambda_handler()
