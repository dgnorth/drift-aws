
# Set Up an IKEv2 VPN Server with StrongSwan on Ubuntu 18.04

## Update secrets file:

Run `edit-secrets.sh` and add an entry for the vpn server at the top. Example:

```
vpn2.tiername.dg-api.com : RSA /etc/ipsec.d/private/vpn-server-key.pem
```

## Prepare launch script:

Make a copy of the [launch-script.sh](launch-script.sh) and edit the values of the environment variables at the top of the file:

```bash
# export S3_KEYSTORE=s3://directive-tiers.dg-api.com/secrets/vpn-certs
# export COUNTRY=US
# export ORGANIZATION="Directive Games"
# export SERVER_NAME_OR_IP="vpn2.devnorth.dg-api.com"
# export LEFTSUBNET=10.50.0.0/16
# export RIGHTSOURCEIP=10.3.50.0/24
```

(Remember to uncomment the lines as well)


## Launch the VPN server:

Go to AWS Web console and launch an EC2 instance with the following settings:

 - AMI: Ubuntu Server 18.04 LTS
 - Instance Type: t2.micro
 - Network: Choose the tier's VPC, public subnet and auto-assign public IP.
 - IAM role: ec2
 - Advanced details: User data as file. Upload your copy of the *launch-script.sh* file.
 - Add Tags: tier:THETIER, service-name:vpn, Name:TIERNAME-vpn2
 - Security group: TIERNAME-nat if available or make a new one with inbound rule `upd 500, 4500` on source `0.0.0.0/0`.
 - SSH Key pair: Choose the one that's associated with the tier.

**Important:** Source/dest check MUST be turned OFF! Once the instance is available in the AWS Web console, select it and click on **Actions, Networking, Change Source/Dest. Check**

## Make a DNS entry:

In Route53 add a new record:

 - Name: vpn2.tiername.dg-api.com
 - Type: CNAME
 - Value: The public DNS name of the instance as seen in the AWS Web console.

# Manage VPN user accounts:

Run `edit-secrets.sh` and modify the user account section accordingly. The format is `<username> %any% : EAP <password>`. Example:

```
myusername %any% : EAP 1234567890abcdefghijklmnopqrst
```

# Reference

[https://www.digitalocean.com/community/tutorials/how-to-set-up-an-ikev2-vpn-server-with-strongswan-on-ubuntu-16-04](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-ikev2-vpn-server-with-strongswan-on-ubuntu-16-04)


# VPN Server Certificates and Keys

The organization owning the configuration DB or tier has a **digital certificate**. This certificate is made  publicly available on S3. The private key used for generating the certificate is stored on S3 but is not made publicly available.

The "distinguished names" in the cert are:
  - C:  Country. Always US just for convenience.
  - O:  Organization. The organization owning the configuration DB.
  - CN: Common Name. VPN Server CA for <organization name>.

VPN server on each tier will have its own private key. A certificate for the VPN server is issued using the CA's certificate and private key as well as the VPN servers own public key. The VPN server certificate and private key never leaves the server machine itself and is not normally accessible anywhere. The VPN server itself can issue the certificate as it has access to the CA's private key and certificate on S3 through instance role access.

## Creating Certificate Authority 

Set these environment variables:

```bash
export COUNTRY=US
export ORGANIZATION="Directive Games"
export S3_KEYSTORE=s3://directive-tiers.dg-api.com/secrets/vpn-certs
```

Run `generate-cert-authority.sh`



# VPN Client Setup:

Note that each VPN client must have the CA's certificate installed on their system. This is a one time setup if the VPN servers are using the same CA.

 ## Windows

Run the following commands in a PowerShell:

```PowerShell
Add-VPNConnection -Name "CONNECTION-NAME" -ServerAddress "thevpn.somewhere.com" -SplitTunneling -PassThru
Add-VpnConnectionRoute -ConnectionName "CONNECTION-NAME" -DestinationPrefix 10.999.0.0/16
```

To set up the certificate run mmc.exe, add Certificates snap-in and import the certificate into "Trusted Root Certification Authorities/Certificates" 

## OSX

Use the built-in VPN client. It's mostly self explanatory.

To set up the certificate double click on the certificate file and import the certificate using KeyChain. Set IP Security (IPSec) to "Always Trust".

## IOS

Use the built-in VPN client.

To set up the certificate send yourself an email with the certificate attached, tap on the file and select Install.

## Linux

Use Strongswan. The finer details of the setup is not available. The VPN server is Strongswan so it's just a matter of using the same configuration.


# Future TODOs:

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

