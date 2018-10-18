#!/bin/bash

# VPN Server setup for Ubuntu 16.04
# Based on "How to Set Up an IKEv2 VPN Server with StrongSwan on Ubuntu 16.04"
# https://www.digitalocean.com/community/tutorials/how-to-set-up-an-ikev2-vpn-server-with-strongswan-on-ubuntu-16-04

# Global params
# export COUNTRY=US
# export ORGANIZATION="Directive Games"
# export S3_KEYSTORE=s3://directive-tiers.dg-api.com/secrets/vpn-certs


: "${S3_KEYSTORE?Set environment variable S3_KEYSTORE to something like: s3://bucket-name/secrets/vpn-certs}"
: "${COUNTRY?Set environment variable COUNTRY to something like: US}"
: "${ORGANIZATION?Set environment variable ORGANIZATION to something like: Directive Games}"

: "${SERVER_NAME_OR_IP?Set environment variable SERVER_NAME_OR_IP to something like: vpn.mydomain.com}"
: "${LEFTSUBNET?Set environment variable LEFTSUBNET to the subnet mask of the VPN network using CIDR notation}"
: "${RIGHTSOURCEIP?Set environment variable RIGHTSOURCEIP to the accompanying subnet mask of the VPN client using CIDR notation.}"


echo "Using following environment values:"
echo "S3_KEYSTORE:       ${S3_KEYSTORE}"
echo "COUNTRY:           ${COUNTRY}"
echo "ORGANIZATION:      ${ORGANIZATION}"
echo "SERVER_NAME_OR_IP: ${SERVER_NAME_OR_IP}"
echo "LEFTSUBNET:        ${LEFTSUBNET}"
echo "RIGHTSOURCEIP:     ${RIGHTSOURCEIP}"


# ---------------- for easy editing of secrets file:
aws s3 cp s3://config.1939games.com/vpn-certs/ipsec.secrets .
nano ipsec.secrets
if [ $? -eq 0 ]
then
  echo "Not uploading file."
else
    echo "Uploading file to S3."
    aws s3 cp ipsec.secrets s3://config.1939games.com/vpn-certs/
fi


# --- Example of windows setup, user powershell in admin mode:
Add-VPNConnection -Name "1939-LIVE" -ServerAddress "vpn4.live.1939api.com" -SplitTunneling -PassThru
Add-VpnConnectionRoute -ConnectionName "1939-LIVE" -DestinationPrefix 10.75.0.0/16

