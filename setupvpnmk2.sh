# VPN Server setup for Ubuntu 16.04
# Based on "How to Set Up an IKEv2 VPN Server with StrongSwan on Ubuntu 16.04"
# https://www.digitalocean.com/community/tutorials/how-to-set-up-an-ikev2-vpn-server-with-strongswan-on-ubuntu-16-04

# Global params
export country=US
export organization="Directive Games"
export s3_keystore=s3://directive-tiers.dg-api.com/secrets/vpn-certs


# ----------------------------------------------------------------------------
echo "Step one time setup — Create Certificate Authority"
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
    --dn "C=${country}, O=${organization}, CN=${organization} Root CA" \
    --outform pem > server-root-ca.pem


# Generate ipsec.secrets file - remember to populate with user and passwords
# and add any new tier as well.
echo "vpn.at-some-place.com : RSA "/etc/ipsec.d/private/vpn-server-key.pem"
" | tee ipsec.secrets

# Archive all in a private S3 bucket:
aws s3 cp . ${s3_keystore} --recursive

# Make the certificate publicly readable
aws s3 cp server-root-ca.pem ${s3_keystore}/server-root-ca.pem --acl public-read

echo "The CA file must be installed and trusted on the VPN client machines."
echo "Here is a public url to the file:"
aws s3 presign ${s3_keystore}/server-root-ca.pem | cut -d '?' -f 1



# ----------------------------------------------------------------------------

# Launch script

export country=US
export organization="Directive Games"
export s3_keystore=s3://directive-tiers.dg-api.com/secrets/vpn-certs

export server_name_or_ip=vpn4.dev.1939api.com
export leftsubnet=10.70.0.0/16
export rightsourceip=10.3.70.0/24



echo "Step 0 - Update apt"
sudo DEBIAN_FRONTEND=noninteractive apt-get -y update


echo "Step 1 — Installing StrongSwan"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q strongswan strongswan-plugin-eap-mschapv2 moreutils iptables-persistent

echo "Step 2 — Fetch Certificate Authority"
mkdir vpn-certs
cd vpn-certs

sudo apt install awscli -y -q
aws s3 cp ${s3_keystore} . --recursive

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
    --dn "C=${country}, O=${organization}, CN=${server_name_or_ip}" \
    --san ${server_name_or_ip} \
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
    leftid=@${server_name_or_ip}
    leftcert=/etc/ipsec.d/certs/vpn-server-cert.pem
    leftsendcert=always
    leftsubnet=${leftsubnet}
    right=%any
    rightid=%any
    rightauth=eap-mschapv2
    rightdns=8.8.8.8,8.8.4.4
    rightsourceip=${rightsourceip}
    rightsendcert=never
    eap_identity=%identity" | sudo tee /etc/ipsec.conf

echo "Step 5 — Configuring VPN Authentication"


# Generate secrets file ONLY if you are not using shared file on s3.
# remember to populate with user and passwords
echo "${server_name_or_ip} : RSA "/etc/ipsec.d/private/vpn-server-key.pem"
" | sudo tee /etc/ipsec.secrets

# Example entry: your_username %any% : EAP your_password
sudo nano /etc/ipsec.secrets
sudo ipsec reload

# Use crontab to fetch shared ipsec.secrets



echo "Make sure the following line includes 'has private key':"
sudo ipsec listcerts | grep pubkey

echo "Step 6 — Configuring the Firewall & Kernel IP Forwarding"

sudo ufw disable

iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -F
iptables -Z

sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

sudo iptables -A INPUT -i lo -j ACCEPT

sudo iptables -A INPUT -p udp --dport  500 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 4500 -j ACCEPT

sudo iptables -A FORWARD --match policy --pol ipsec --dir in  --proto esp -s ${rightsourceip} -j ACCEPT
sudo iptables -A FORWARD --match policy --pol ipsec --dir out --proto esp -d ${rightsourceip} -j ACCEPT

sudo iptables -t nat -A POSTROUTING -s ${rightsourceip} -o eth0 -m policy --pol ipsec --dir out -j ACCEPT
sudo iptables -t nat -A POSTROUTING -s ${rightsourceip} -o eth0 -j MASQUERADE

sudo iptables -t mangle -A FORWARD --match policy --pol ipsec --dir in -s ${rightsourceip} -o eth0 -p tcp -m tcp --tcp-flags SYN,RST SYN -m tcpmss --mss 1361:1536 -j TCPMSS --set-mss 1360

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
  venv=`cat /etc/opt/drift-apirouter/venv`
  echo "  updating crontab to fetch ipsec.secrets."
  crontab -l -u ubuntu | { cat; echo "* * * * * sudo aws s3 cp s3://config.1939games.com/vpn-certs/ipsec.secrets /etc/ipsec.secrets && sudo ipsec secrets"; } | crontab - -u ubuntu
fi


# probably not needed
do-release-upgrade
sudo reboot


# DONE!



# ---------------- for easy editing of secrets file:
aws s3 cp s3://config.1939games.com/vpn-certs/ipsec.secrets .
nano ipsec.secrets
aws s3 cp ipsec.secrets s3://config.1939games.com/vpn-certs/

# --- Example of windows setup, user powershell in admin mode:
Add-VPNConnection -Name "1939-LIVE" -ServerAddress "vpn4.live.1939api.com" -SplitTunneling -PassThru
Add-VpnConnectionRoute -ConnectionName "1939-LIVE" -DestinationPrefix 10.75.0.0/16

