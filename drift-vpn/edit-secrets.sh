#!/bin/bash

: "${S3_KEYSTORE?Set environment variable S3_KEYSTORE to something like: s3://bucket-name/secrets/vpn-certs}"

echo "Using following environment values:"
echo "S3_KEYSTORE:       ${S3_KEYSTORE}"

# ---------------- for easy editing of secrets file:
aws s3 cp ${S3_KEYSTORE}/ipsec.secrets .
nano ipsec.secrets
echo "Uploading file to S3."
aws s3 cp ipsec.secrets ${S3_KEYSTORE}/
echo "Removing local copy of ipsec.secrets."
rm ipsec.secrets
echo "Done."
