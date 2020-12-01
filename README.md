# availability-canary

Python Lambda script to externally query infra in case of total internal failure. 

```bash
#!/bin/bash

FUNC_NAME="availability-canary"

aws cloudformation delete-stack --stack-name $FUNC_NAME # delete stack

zip -r lambda_function.zip availability-canary.py -q
sam package --s3-bucket vizzyy-packaging --output-template-file packaged.yml
aws cloudformation wait stack-delete-complete --stack-name $FUNC_NAME
sam deploy --template-file packaged.yml --stack-name $FUNC_NAME --capabilities CAPABILITY_IAM
rm lambda_function.zip
rm packaged.yml
```
