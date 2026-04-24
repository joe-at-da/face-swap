#!/bin/bash

# Setup script for configuring AWS CLI with Hetzner S3 credentials
# This script configures AWS CLI to work with Hetzner's S3-compatible object storage

echo "==============================================="
echo "Configuring AWS CLI for Hetzner S3"
echo "==============================================="

# Hetzner S3 Configuration
S3_ENDPOINT="https://fsn1.your-objectstorage.com"
S3_BUCKET="veedoo-coolify"
S3_ACCESS_KEY="MP8VSZZ3VVCXYZIGXE1M"
S3_SECRET_KEY="zJ2Bw32vDvsjlpvYBdBnUkllFIlR8zRPfSheAWUm"
S3_REGION="fsn1"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Installing..."

    # Detect OS and install AWS CLI accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf awscliv2.zip aws/
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
        sudo installer -pkg AWSCLIV2.pkg -target /
        rm AWSCLIV2.pkg
    else
        echo "Unsupported OS. Please install AWS CLI manually."
        echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
fi

# Create AWS config directory if it doesn't exist
mkdir -p ~/.aws

# Create or update AWS credentials file
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = ${S3_ACCESS_KEY}
aws_secret_access_key = ${S3_SECRET_KEY}

[hetzner]
aws_access_key_id = ${S3_ACCESS_KEY}
aws_secret_access_key = ${S3_SECRET_KEY}
EOF

# Create or update AWS config file
cat > ~/.aws/config << EOF
[default]
region = ${S3_REGION}
output = json

[profile hetzner]
region = ${S3_REGION}
output = json
s3 =
    endpoint_url = ${S3_ENDPOINT}
    signature_version = s3v4
EOF

echo "✓ AWS CLI configured for Hetzner S3"

# Test the configuration
echo ""
echo "Testing S3 connection..."
aws s3 ls s3://${S3_BUCKET}/ --endpoint-url=${S3_ENDPOINT} --profile hetzner 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ Successfully connected to Hetzner S3!"
    echo ""
    echo "You can now use AWS CLI commands with Hetzner S3:"
    echo "  aws s3 ls s3://${S3_BUCKET}/ --endpoint-url=${S3_ENDPOINT}"
    echo "  aws s3 cp file.txt s3://${S3_BUCKET}/ --endpoint-url=${S3_ENDPOINT}"
    echo ""
    echo "Or use the 'hetzner' profile:"
    echo "  aws s3 ls s3://${S3_BUCKET}/ --profile hetzner --endpoint-url=${S3_ENDPOINT}"
else
    echo "✗ Failed to connect to Hetzner S3"
    echo "Please check your credentials and endpoint URL"
    exit 1
fi

echo ""
echo "==============================================="
echo "Configuration complete!"
echo "==============================================="