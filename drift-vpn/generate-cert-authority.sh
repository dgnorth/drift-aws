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
: "${ORGANIZATION?Set environment variable ORGANIZATION to something like: s3://bucket-name/secrets/vpn-certs}"


# ----------------------------------------------------------------------------
echo "Creating Certificate Authority for ${ORGANIZATION} and storing the certificate and private key in ${S3_KEYSTORE}"
# Assuming ipsec is installed

mkdir vpn-certs
cd vpn-certs
# ipsec pki commands used below:
# --gen     Generate a new private key.
# --self    Generate a self-signed X.509 certificate.
# --pub     Extract the public key from a private key, PKCS#10 certificate request or X.509 certificate.
# --issue   Issue an X.509 certificate signed with a CA's private key.

# Distinguished names or --dn arguments:
# CN: CommonName
# OU: OrganizationalUnit
# O: Organization
# L: Locality
# S: StateOrProvinceName
# C: CountryName

# Generate a private key for the Certificate Authority.
ipsec pki \
    --gen \
    --type rsa \
    --size 4096 \
    --outform pem > server-root-key.pem

chmod 600 server-root-key.pem

# Generate a self-signed X.509 certificate for the Certificate Authority.
ipsec pki \
    --self \
    --ca \
    --lifetime 3650 \
    --in server-root-key.pem \
    --type rsa \
    --dn "C=${COUNTRY}, O=${ORGANIZATION}, CN=${ORGANIZATION} Root CA" \
    --outform pem > server-root-ca.pem


# Generate ipsec.secrets file - remember to populate with user and passwords
# and add any new tier as well.
echo "vpn.at-some-place.com : RSA "/etc/ipsec.d/private/vpn-server-key.pem"
" | tee ipsec.secrets

CERT_FILE=${S3_KEYSTORE}/server-root-ca.pem

# Make sure there is no certificate already on S3
aws s3 ls ${CERT_FILE}
if [ $? -eq 0 ]
then
  echo "Error: There is already a certificate at ${CERT_FILE}" >&2
  echo "Delete the file or pick a different S3 url." >&2
else
    # Archive all in a private S3 bucket:
    aws s3 cp . ${S3_KEYSTORE} --recursive

    # Make the certificate publicly readable
    aws s3 cp server-root-ca.pem ${CERT_FILE} --acl public-read
fi

echo ""
echo "Note! The certificate must be installed and trusted on the VPN client machines."
echo "Here is a public url to the file:"
aws s3 presign ${CERT_FILE} | cut -d '?' -f 1  # Tis' a hack
