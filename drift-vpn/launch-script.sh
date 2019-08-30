#!/bin/bash
# --------- provide params


# export S3_KEYSTORE=s3://directive-tiers.dg-api.com/secrets/vpn-certs
# export COUNTRY=US
# export ORGANIZATION="Directive Games"
# export SERVER_NAME_OR_IP="vpn2.devnorth.dg-api.com"
# export LEFTSUBNET=10.50.0.0/16
# export RIGHTSOURCEIP=10.3.50.0/24

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

# --------- static script
echo "Step 0 - Update apt"
sudo DEBIAN_FRONTEND=noninteractive apt-get -y update


echo "Step 1 — Installing StrongSwan"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q iptables-persistent strongswan strongswan-starter strongswan-pki strongswan-swanctl moreutils iptables-persistent

echo "Step 2 — Fetch Certificate Authority"
mkdir vpn-certs
cd vpn-certs

sudo apt install awscli -y -q
aws s3 cp ${S3_KEYSTORE} . --recursive

echo "Step 3 — Generating a Certificate for the VPN Server"
# Generate a private key for this VPN server.
ipsec pki \
    --gen \
    --type rsa \
    --size 4096 \
    --outform pem > vpn-server-key.pem


# Issue a certificate for the VPN server using the VPN server public key and the CA's
# private key and certificate.
ipsec pki \
    --pub \
    --in vpn-server-key.pem \
    --type rsa \
| ipsec pki \
    --issue \
    --lifetime 1825 \
    --cacert server-root-ca.pem \
    --cakey server-root-key.pem \
    --dn "C=${COUNTRY}, O=${ORGANIZATION}, CN=${SERVER_NAME_OR_IP}" \
    --san ${SERVER_NAME_OR_IP} \
    --flag serverAuth \
    --flag ikeIntermediate \
    --outform pem > vpn-server-cert.pem

sudo cp ./vpn-server-cert.pem /etc/ipsec.d/certs/vpn-server-cert.pem
sudo cp ./vpn-server-key.pem /etc/ipsec.d/private/vpn-server-key.pem

sudo chown root /etc/ipsec.d/private/vpn-server-key.pem
sudo chgrp root /etc/ipsec.d/private/vpn-server-key.pem
sudo chmod 600 /etc/ipsec.d/private/vpn-server-key.pem

echo "Step 4 — Configuring StrongSwan"
sudo cp /etc/ipsec.conf /etc/ipsec.conf.original

echo "config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn ikev2-vpn
    auto=add
    compress=no
    type=tunnel
    keyexchange=ikev2
    fragmentation=yes
    forceencaps=yes
    ike=aes256-sha1-modp1024,3des-sha1-modp1024!
    esp=aes256-sha1,3des-sha1!
    dpdaction=clear
    dpddelay=300s
    rekey=no
    left=%any
    leftid=@${SERVER_NAME_OR_IP}
    leftcert=/etc/ipsec.d/certs/vpn-server-cert.pem
    leftsendcert=always
    leftsubnet=${LEFTSUBNET}
    right=%any
    rightid=%any
    rightauth=eap-mschapv2
    rightdns=8.8.8.8,8.8.4.4
    rightsourceip=${RIGHTSOURCEIP}
    rightsendcert=never
    eap_identity=%identity" | sudo tee /etc/ipsec.conf

echo "Step 5 — Configuring VPN Authentication"


# Generate secrets file ONLY if you are not using shared file on s3.
# remember to populate with user and passwords
echo "${SERVER_NAME_OR_IP} : RSA "/etc/ipsec.d/private/vpn-server-key.pem"
" | sudo tee /etc/ipsec.secrets

# Example entry: your_username %any% : EAP your_password
sudo aws s3 cp ${S3_KEYSTORE}/ipsec.secrets /etc/ipsec.secrets
sudo ipsec reload

# Use crontab to fetch shared ipsec.secrets



echo "Make sure the following line includes 'has private key':"
sudo ipsec listcerts | grep pubkey

echo "Step 6 — Configuring the Firewall & Kernel IP Forwarding"

echo "Turn off source/dest check."
EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id || die \"wget instance-id has failed: $?\"`"
EC2_AVAIL_ZONE="`wget -q -O - http://169.254.169.254/latest/meta-data/placement/availability-zone || die \"wget availability-zone has failed: $?\"`"
EC2_REGION="`echo \"$EC2_AVAIL_ZONE\" | sed -e 's:\([0-9][0-9]*\)[a-z]*\$:\\1:'`"
sudo aws ec2 modify-instance-attribute --instance-id ${EC2_INSTANCE_ID} --region ${EC2_REGION} --source-dest-check "{\"Value\": true}"


sudo ufw disable

sudo iptables -P INPUT ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -F
sudo iptables -Z

sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

sudo iptables -A INPUT -i lo -j ACCEPT

sudo iptables -A INPUT -p udp --dport  500 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 4500 -j ACCEPT

sudo iptables -A FORWARD --match policy --pol ipsec --dir in  --proto esp -s ${RIGHTSOURCEIP} -j ACCEPT
sudo iptables -A FORWARD --match policy --pol ipsec --dir out --proto esp -d ${RIGHTSOURCEIP} -j ACCEPT

sudo iptables -t nat -A POSTROUTING -s ${RIGHTSOURCEIP} -o eth0 -m policy --pol ipsec --dir out -j ACCEPT
sudo iptables -t nat -A POSTROUTING -s ${RIGHTSOURCEIP} -o eth0 -j MASQUERADE

sudo iptables -t mangle -A FORWARD --match policy --pol ipsec --dir in -s ${RIGHTSOURCEIP} -o eth0 -p tcp -m tcp --tcp-flags SYN,RST SYN -m tcpmss --mss 1361:1536 -j TCPMSS --set-mss 1360

sudo iptables -A INPUT -j DROP
sudo iptables -A FORWARD -j DROP

sudo netfilter-persistent save
sudo netfilter-persistent reload


echo "# Enable packet forwarding for IPv4
net.ipv4.ip_forward=1
# Do not accept ICMP redirects (prevent MITM attacks)
net.ipv4.conf.all.accept_redirects = 0
# Do not send ICMP redirects (we are not a router)
net.ipv4.conf.all.send_redirects = 0

net.ipv4.ip_no_pmtu_disc = 1"| sudo tee /etc/sysctl.conf


# ------------------------
echo "Installing crontab job for fetching ipsec.secrets:"
if crontab -l -u ubuntu | grep -q 'ipsec.secrets'; then
  echo "  crontab already configured to fetch ipsec.secrets"
else
  echo "  updating crontab to fetch ipsec.secrets."
  crontab -l -u ubuntu | { cat; echo "* * * * * sudo aws s3 cp ${S3_KEYSTORE}/ipsec.secrets /etc/ipsec.secrets && sudo ipsec secrets"; } | crontab - -u ubuntu
fi


# probably not needed
do-release-upgrade
sudo reboot

