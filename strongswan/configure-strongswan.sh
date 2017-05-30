#!/bin/bash
sudo bash

unset UCF_FORCE_CONFFOLD
export UCF_FORCE_CONFFNEW=YES
ucf --purge /boot/grub/menu.lst
export DEBIAN_FRONTEND=noninteractive

echo net.ipv4.ip_forward = 1 >> /etc/sysctl.conf
sysctl -p
sudo apt-get install -y -q strongswan


PRIVATEIP=`curl http://169.254.169.254/latest/meta-data/local-ipv4`
SUBNETIP=`echo ${PRIVATEIP} | cut -d '.' -f 2`

# See http://manpages.ubuntu.com/manpages/trusty/man5/ipsec.conf.5.html

echo "# /etc/ipsec.conf - strongSwan IPsec configuration file

config setup

conn %default
     ikelifetime=60m
     keylife=20m
     rekeymargin=3m
     keyingtries=1
     left=${PRIVATEIP}
     leftsubnet=10.${SUBNETIP}.0.0/16
     leftid=theglobalsecretid
     right=%any
     rightsourceip=10.3.${SUBNETIP}.0/24
     auto=add

conn PresharedKey
     keyexchange=ikev2
     authby=secret
" > /etc/ipsec.conf

echo "# /etc/ipsec.secrets - strongSwan IPsec secrets file

theglobalsecretid : PSK ${STRONGSWAN_PSK}
" > /etc/ipsec.secrets

ipsec restart

apt-get install -y -q iptables-persistent
iptables --table nat --append POSTROUTING --source 10.${SUBNETIP}.0.0/16 -j MASQUERADE
iptables-save > /etc/iptables/rules.v4
