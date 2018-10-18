
# Set Up an IKEv2 VPN Server with StrongSwan on Ubuntu 16.04

todo: copy api router project and use crontab to generate ipsec.conf and periodically update ipsec.secrets accordingly.

https://www.digitalocean.com/community/tutorials/how-to-set-up-an-ikev2-vpn-server-with-strongswan-on-ubuntu-16-04

Set-VpnConnection -Name "VPN DEVNORTH"  -SplitTunneling $True


## VPN Server Certificates and Keys

The organization owning the configuration DB or tier has a **digital certificate**. This certificate is made  publicly available on S3. The private key used for generating the certificate is stored on S3 but is not made publicly available.

The "distinguished names" in the cert are:
  - C:  Country. Always US just for convenience.
  - O:  Organization. The organization owning the configuration DB.
  - CN: Common Name. VPN Server CA for <organization name>.

VPN server on each tier will have its own private key. A certificate for the VPN server is issued using the CA's certificate and private key as well as the VPN servers own public key. The VPN server certificate and private key never leaves the server machine itself and is not normally accessible anywhere. The VPN server itself can issue the certificate as it has access to the CA's private key and certificate on S3 through instance role access.

Each VPN client must have the CA's certificate installed on their system:

 - OSX: Double click on the certificate file and import the certificate using KeyChain. Set IP Security (IPSec) to "Always Trust".
 - Windows: Run mmc.exe, add Certificates snap-in and import the certificate into "Trusted Root Certification Authorities/Certificates" folder.
 - iOS: Send yourself an email with the certificate attached, tap on the file and select Install.


## Set up VPN user account

Run the following commands to manage VPN user accounts:

`drift-admin vpn` List VPN users and more info.
`drift-admin vpn cert` Generate a private key and issue a CA certificate.
`drift-admin vpn adduser` Add a new user or generate a new pwd for an existing user.
`drift-admin vpn removeuser` Remove user.


```bash
sudo apt-get install strongswan strongswan-plugin-eap-mschapv2 moreutils iptables-persistent

```

what to do:

create a launch config and autoscaling group and configure everything using launch config script.

```bash
aws ec2 delete-launch-template --launch-template-name LaunchyLoon

aws ec2 create-launch-template \
    --launch-template-name LaunchyLoon \
    --version-description WebVersion1 \
    --launch-template-data \
    '{
      "NetworkInterfaces": [
        {
          "DeviceIndex": 0,
          "AssociatePublicIpAddress": true,
          "SubnetId": "subnet-a8f280cd",
          "Groups": ["sg-cd4849a8", "sg-ce4849ab"]
        }
      ],

      "ImageId": "ami-2a7d75c0",
      "InstanceType": "t2.small",
      "KeyName": "devnorth-key",
      "IamInstanceProfile": {"Name": "ec2"},

      "TagSpecifications": [
        {
          "ResourceType": "instance",
          "Tags": [
            {
              "Key": "Name",
              "Value": "DEVNORTH-vpn test bloorgh"
            },
            {
              "Key": "tier",
              "Value": "DEVNORTH"
            },
            {
              "Key": "service-name",
              "Value": "vpn"
            }
          ]
        }
      ]
    }'
```

