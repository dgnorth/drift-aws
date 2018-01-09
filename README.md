# drift-aws
Provisioning and management tools for AWS cloud.

This document assumes you have the [AWS Command Line Interface Tool](http://docs.aws.amazon.com/cli/latest/reference/index.html#cli-aws) installed. Use these [install instructions](http://docs.aws.amazon.com/cli/latest/userguide/installing.html) to get the very latest version of the tool.

It is highly recommended that you use an IAM user account type. Here's how to set one up:

- In AWS Console, go to IAM service and create a new IAM user for your personal use.
- Give it **PowerUserAccess** role.
- Generate an access key pair.

Add a profile for your IAM user in your local aws config file. Example:

##### ~/.aws/credentials
```ini
[beijing]
aws_access_key_id = AKIA123123123123123
aws_secret_access_key = 9b90fed63b94/05374a6b
```

##### ~/.aws/config
```ini
[profile beijing]
region = cn-north-1
output = text
```

Now the aws tool can be run using any of the profiles defined in the config files:

`aws --profile beijing	do-something`
  

## Configuration setup and VPC provisioning:

Run this, with the appropriate adjustments:

```bash
# Set the proper values here
TIERNAME=DEVSKULL
AWSPROFILE=beijing
REGION=eu-west-1
ROOTDOMAIN=dg-api.com
VPCBASENET=10.99

# Don't change this
alias awsrun='aws --profile ${AWSPROFILE} --output text $1'
TIERNAMELOWER=`echo ${TIERNAME} | tr '[:upper:]' '[:lower:]'`
SSHKEYNAME=${TIERNAMELOWER}-key
export AWS_PROFILE=${AWSPROFILE}
```

# Configuring the Tier Template

Under **cloudformation** folder are scripts and templates for AWS CloudFormation which are used to manage AWS infrastructure deployments for Drift.

> AWS CloudFormation gives developers and systems administrators an easy way to create and manage a collection of related AWS resources, provisioning and updating them in an orderly and predictable fashion.
> 
> You can deploy and update a template and its associated collection of resources (called a stack) by using the AWS Management Console, AWS Command Line Interface, or APIs.

### [cfn.py](./cloudformation/cfn.py)
A boto based script which applies cloudformation templates. It is a more convenient alternative to using the ```aws cloudformation create-stack``` and ```aws cloudformation update-stack``` commands.


### [vpc.py](./cloudformation/vpc.py)
A [Troposphere](https://github.com/cloudtools/troposphere) script describing a VPC and associated objects neccessary to run a Drift based stack.

### Usage:

If changes are made to any of the Troposphere scripts, run ```generate-templates``` to create or update the CloudFormation templates.

The list of Troposhpere scripts to process is inside the ```generate-templates``` shell script. 






### Step 1: Create an SSH key for EC2 instances:

Create a key pair in ~/.ssh and chmod it to 400:

```bash
awsrun ec2 create-key-pair --key-name ${SSHKEYNAME} --query 'KeyMaterial' > ~/.ssh/${SSHKEYNAME}.pem
chmod 400 ~/.ssh/${SSHKEYNAME}.pem     
```


### Step 2: Set up and run the AWS CloudFormation Tier command:
![](img/1449085590_warning.png) Run this command from the root of your **drift-aws** repo:

```bash
# Create an executable script that sets up or modifies the tier on AWS
echo '
#!/bin/bash

# set cwd to where this script is
cd "$(dirname "$0")"

python cfn.py -c vpc.json -t -p VPCBaseNet='`echo ${VPCBASENET}`' --region='`echo ${REGION} ${TIERNAME}`'
' > ./cloudformation/run-vpc-${TIERNAMELOWER}
chmod +x ./cloudformation/run-vpc-${TIERNAMELOWER}

# Run the initial setup
./cloudformation/run-vpc-${TIERNAMELOWER}
```


### Step 3: Add Tier to StrongSwan VPN configuration:

If you haven't done it already, copy the **ipsec.conf** file found in the strongswan folder to `/etc/ipsec.conf` on Linux or `/usr/local/etc/ipsec.conf` on OSX.

Add connection to ipsec.conf on your macbook:

```bash
echo '\nconn '`echo ${TIERNAMELOWER}`'
	right=vpn.'`echo ${TIERNAMELOWER}.${ROOTDOMAIN}`'
	rightsubnet='`echo ${VPCBASENET}`'.0.0/16
' >> /usr/local/etc/ipsec.conf
```



## Provisioning Drift Tier Servers
Each Drift tier runs a few off the shelf servers or services:

 - VPN server.
 - S3 buckets.
 - Redis server.
 - Postgres server.
 
At the moment these services are set up semi-manually.

**NOTE! In the Bash code, set the proper values in to the environment variables before executing the rest of the commands. The ones that require changes are grouped together in the examples below.**

### NAT Service

 - In AWS web console, go to **VPC** dashboard.
 - Select **NAT Gateways** and click on **Create NAT Gateway**. Select the public subnet of the tier, assign/create elastic IP for it and click on **Create a NAT Gateway**.
 - Select **Route Tables**.
 - Select the tiers *private* route table, click on **Routes** tab and click **Edit**.
 - For destination `0.0.0.0/0` change the target to the newly created nat instance. (The AWS nat resource id's are prefixed with *nat-*).

  
### VPN Server

In IAM, create a role called vpn and assign no policy to it.

##### Launch the EC2 instance
The latest Ubuntu-Trusty 14.04 AMI is used as base image.

The launch script is loosely based on [how to set up strongSwan on AWS](https://wiki.strongswan.org/projects/strongswan/wiki/AwsVpc).

![](img/1449085590_warning.png) Run this command from the root of your **drift-aws** repo:

```bash
SGNAME=${TIERNAME}-vpn-sg
SGNAMEPRIV=${TIERNAME}-private-sg
VPCID=`aws ec2 describe-vpcs --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-vpc | grep "VPCS" | cut -f 7`
SGID=`aws ec2 describe-security-groups --region ${REGION} --output text --filters Name=tag:Name,Values=${SGNAME} | grep SECURITYGROUPS | cut -f 3`
SGIDPRIV=`aws ec2 describe-security-groups --region ${REGION} --output text --filters Name=tag:Name,Values=${SGNAMEPRIV} | grep SECURITYGROUPS | cut -f 3`
AMI=`aws ec2 describe-images --region ${REGION} --output text --output text --owners 099720109477 --filters Name=name,Values="ubuntu*xenial*16.04*" --query 'Images[*].[CreationDate,ImageId,Name]'  | grep ubuntu/images/hvm-ssd/ubuntu-xenial-16.04 | sort | tail -n 1 | cut -f 2`
SUBNETID=`aws ec2 describe-subnets --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-public-subnet-1 | grep SUBNETS | cut -f 9`

LAUNCHSCRIPT=`cat strongswan/configure-strongswan.sh`
   
EC2ID=`aws ec2 run-instances --region ${REGION} --output text --image-id ${AMI} --count 1 --instance-type t2.small --key-name ${SSHKEYNAME} --security-group-ids ${SGID} ${SGIDPRIV} --subnet-id ${SUBNETID} --monitoring Enabled=true --disable-api-termination --iam-instance-profile Name=vpn --user-data '${LAUNCHSCRIPT}' | grep INSTANCES | cut -f 8`

echo VPN Box instance: ${EC2ID}
awsrun ec2 wait instance-running --instance-ids ${EC2ID}
```

Once the instance is available, continue here to tag the instance, turn off source-dest check, allocate an elastic IP address and add a route from within the VPC out to VPN clients:

```bash
aws ec2 modify-instance-attribute --region ${REGION} --output text --instance-id ${EC2ID} --source-dest-check "{\"Value\": false}"
aws ec2 create-tags --region ${REGION} --output text --resources ${EC2ID} --tags Key=Name,Value=${TIERNAME}-vpn  Key=tier,Value=${TIERNAME} Key=service-name,Value=vpn

EIPALLOCID=`aws ec2 allocate-address --region ${REGION} --output text --domain ${VPCID} | cut -f 1`
aws ec2 associate-address --region ${REGION} --output text --instance-id ${EC2ID} --allocation-id ${EIPALLOCID}

RTPUB=`aws ec2 describe-route-tables --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-rtbl-internet | grep ROUTETABLES | cut -f 2`
aws ec2 create-route --region ${REGION} --output text --route-table-id ${RTPUB} --destination-cidr-block 10.3.0.0/16 --instance-id ${EC2ID}

VPNIP=`aws ec2 describe-addresses --region ${REGION} --output text --filters Name=allocation-id,Values=${EIPALLOCID} --query 'Addresses[*].[PublicIp]'`

VPNDNS=`awsrun ec2 describe-instances --instance-ids ${EC2ID} --query 'Reservations[0].Instances[0].[PublicDnsName]'`

echo VPN Box IP address: ${VPNIP}
echo VPN Box DNS Name: ${VPNDNS}
echo "Add this as A record to your root domain:"
echo vpn.${TIERNAMELOWER}.${ROOTDOMAIN} = ${VPNIP}

```

*Note: If external SSH access is needed, the security group must be modified to allow SSH traffic from the internet (preferably to our own public IP address). Here are the commands to connect:*

See if you can ssh onto the vpn:


```bash
ssh ubuntu@${VPNIP} -i ~/.ssh/${SSHKEYNAME}.pem
```

#### Errata:
The ipsec.conf file is not proper. Use this one with the appropriate amendments:

```
# /etc/ipsec.conf - strongSwan IPsec configuration fileconfig setupconn %default     ikelifetime=60m     keylife=20m     rekeymargin=3m     keyingtries=1     keyexchange=ikev2     authby=secret     auto=addconn PresharedKey     left=10.50.21.148     leftsubnet=10.50.0.0/16     leftid=theglobalsecretid     right=%any     rightsourceip=10.3.50.0/24
```

### Strongswan Config
 * Make a DNS entry which points to the VPN instance (See Adding DNS section below).
 * Add the new tier to */strongswan/ipsec.conf*


### Redis Server
The Redis server is a managed instance.

##### Launch a Redis cache cluster
```bash
ELASTISUBNET=`aws elasticache describe-cache-subnet-groups --region ${REGION} --output text | grep ${TIERNAME}-elasticache-subnet-group | cut -f 3`
SGID=`aws ec2 describe-security-groups --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-redis-sg | grep SECURITYGROUPS | cut -f 3`

aws elasticache create-cache-cluster --region ${REGION} --output text --cache-cluster-id ${TIERNAME}-redis --engine redis --cache-subnet-group-name ${ELASTISUBNET} --security-group-ids ${SGID} --tags Key=tier,Value=${TIERNAME} --cache-node-type cache.t2.small --num-cache-nodes 1
REDISADDR=`aws elasticache --region ${REGION} describe-cache-clusters --show-cache-node-info --cache-cluster-id ${TIERNAME}-redis --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' --output text`
```

Remember to add DNS entry to the instance. The address is in `${REDISADDR}` environment variable.


### PostgreSQL


##### Create DB instance
```bash
SGID=`aws ec2 describe-security-groups --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-private-sg | grep SECURITYGROUPS | cut -f 3`
DBSUBNETGROUP=`aws rds describe-db-subnet-groups --region ${REGION} --output text | grep ${TIERNAME}-db-subnetgroup | cut -f 4`
aws rds create-db-instance --region ${REGION} --output text --db-name postgres --db-instance-identifier ${TIERNAME}-postgresql --allocated-storage 20 --db-instance-class db.t2.small --engine postgres --master-username postgres --master-user-password postgres --vpc-security-group-ids ${SGID} --db-subnet-group-name ${DBSUBNETGROUP} --no-multi-az --no-publicly-accessibl --tags Key=tier,Value=${TIERNAME} --storage-type gp2

awsrun rds wait db-instance-available --db-instance-identifier ${TIERNAME}-postgresql

POSTGRESQLADDR=`aws rds --region ${REGION} describe-db-instances --db-instance-identifier ${TIERNAME}-postgresql --query 'DBInstances[0].Endpoint.Address' --output text`
```

Remember to add DNS entry to the instance. The address is in `${POSTGRESQLADDR}` environment variable.

The user **zzp_user** must be created manually.

 - Connect to the DB machine with pgAdmin4 or psql (`psql -h {POSTGRESQLADDR} -U postgres`).
 - Create a user called **zzp_user** with same password (`create user zzp_user with password 'zzp_user';`).
 - Asssing "can login" privilege, and add role **rds_superuser** to the user (`grant rds_superuser to zzp_user;`)



## Adding servers to DNS
Create a DNS entry for each of the servers. Example:


| Name       | Type | Env Var | Example Value |
| ---------- | ---- | ------- |-------------- |
|redis.devnorth.dg-api.com | CNAME | ${REDISADDR} | devnorth-redis.xnves0.0001.euw1.cache.amazonaws |
|postgres.devnorth.dg-api.com | CNAME | ${POSTGRESQLADDR} | devnorth-postgresql.c40zji49p9dj.eu-west-1.rds.amazonaws |
|vpn.devnorth.dg-api.com| A | ${VPNIP} |52.18.20.30|



 
 

  