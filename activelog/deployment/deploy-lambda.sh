#!/bin/bash
# Deploy ActiveLog to AWS Lambda for serverless compute offloading

# Package application
zip -r activelog-lambda.zip . -x "*.git*" "node_modules/*" "__pycache__/*" "*.pyc"

# Create Lambda function
aws lambda create-function \
    --function-name activelog-compute-offloader \
    --runtime python3.11 \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
    --handler lambda_handler.handler \
    --zip-file fileb://activelog-lambda.zip \
    --timeout 300 \
    --memory-size 1024 \
    --environment Variables='{
        "CLOUD_MODE":"true",
        "DEVICE_OFFLOAD":"true"
    }'

# Create API Gateway
aws apigateway create-rest-api \
    --name activelog-compute-api \
    --description "ActiveLog Compute Offloading API"

echo "Deployment complete. Update your cloud_providers.json with the endpoint."
