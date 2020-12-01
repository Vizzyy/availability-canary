#!/bin/bash

FUNC_NAME="availability-canary"

npm i
zip -r lambda_function.zip index.js node_modules package.json -q
aws lambda update-function-code --function-name "$FUNC_NAME" --zip-file fileb://lambda_function.zip
rm lambda_function.zip

#trigger function
#aws lambda invoke --function-name "$FUNC_NAME" output.json