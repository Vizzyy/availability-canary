#!/bin/bash

FUNC_NAME=$1
S3_PATH=$2

npm i
zip -r lambda_function.zip index.js node_modules package.json -q
aws lambda update-function-code --function-name "$FUNC_NAME" --zip-file fileb://lambda_function.zip
rm lambda_function.zip

aws s3 cp . "$S3_PATH" --recursive --exclude "*" --include "*.html" --exclude "*/*" --acl public-read

#trigger function
#aws lambda invoke --function-name "$FUNC_NAME" output.json