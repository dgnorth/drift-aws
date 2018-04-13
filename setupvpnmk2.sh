# VPN Server setup for Ubuntu 16.04
# Based on "How to Set Up an IKEv2 VPN Server with StrongSwan on Ubuntu 16.04"
# https://www.digitalocean.com/community/tutorials/how-to-set-up-an-ikev2-vpn-server-with-strongswan-on-ubuntu-16-04

export server_name_or_ip=ec2-34-244-136-139.eu-west-1.compute.amazonaws.com
export rightsourceip=10.3.50.0/24

echo "Step 0 - Update apt"
sudo apt-get update -y -q
echo "cannot do sudo apt-get upgrade -y -q because of a grub prompt. Will use a workaround instead: http://askubuntu.com/questions/146921/how-do-i-apt-get-y-dist-upgrade-without-a-grub-config-prompt"
DEBIAN_FRONTEND=noninteractive sudo apt-get -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' dist-upgrade

echo "Step 1 — Installing StrongSwan"
sudo apt-get install -y -q strongswan strongswan-plugin-eap-mschapv2 moreutils iptables-persistent

echo "Step 2 — Creating a Certificate Authority"
mkdir vpn-certs
cd vpn-certs
ipsec pki --gen --type rsa --size 4096 --outform pem > server-root-key.pem
chmod 600 server-root-key.pem

ipsec pki --self --ca --lifetime 3650 \
--in server-root-key.pem \
--type rsa --dn "C=US, O=VPN Server, CN=VPN Server Root CA" \
--outform pem > server-root-ca.pem

echo "Step 3 — Generating a Certificate for the VPN Server"
ipsec pki --gen --type rsa --size 4096 --outform pem > vpn-server-key.pem

ipsec pki --pub --in vpn-server-key.pem \
--type rsa | ipsec pki --issue --lifetime 1825 \
--cacert server-root-ca.pem \
--cakey server-root-key.pem \
--dn "C=US, O=VPN Server, CN=${server_name_or_ip}" \
--san ${server_name_or_ip} \
--flag serverAuth --flag ikeIntermediate \
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
    leftsubnet=10.50.0.0/16
    right=%any
    rightid=%any
    rightauth=eap-mschapv2
    rightdns=8.8.8.8,8.8.4.4
    rightsourceip=${rightsourceip}
    rightsendcert=never
    eap_identity=%identity" | sudo tee /etc/ipsec.conf

echo "Step 5 — Configuring VPN Authentication"

# NEEEEEEEDS TO BE SHELLERIZED
sudo nano /etc/ipsec.secrets
${server_name_or_ip} : RSA "/etc/ipsec.d/private/vpn-server-key.pem"
your_username %any% : EAP "your_password"
sudo ipsec reload


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


# NEEEEEEEDS TO BE SHELLERIZED
sudo nano /etc/sysctl.conf
# Uncomment the next line to enable packet forwarding for IPv4
net.ipv4.ip_forward=1

. . .

# Do not accept ICMP redirects (prevent MITM attacks)
net.ipv4.conf.all.accept_redirects = 0
# Do not send ICMP redirects (we are not a router)
net.ipv4.conf.all.send_redirects = 0

. . .

net.ipv4.ip_no_pmtu_disc = 1