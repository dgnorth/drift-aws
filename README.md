# drift-aws
Provisioning and management tools for AWS cloud.

This document assumes you have the [AWS Command Line Interface Tool](http://docs.aws.amazon.com/cli/latest/reference/index.html#cli-aws) installed. Use these [install instructions](http://docs.aws.amazon.com/cli/latest/userguide/installing.html) to get the very latest version of the tool.


## Configuration setup and VPC provisioning:

Run this, with the appropriate adjustments:

```bash
# Set the proper values here
TIERNAME=DEVSKULL
REGION=eu-west-1
ROOTDOMAIN=dg-api.com
VPCBASENET=10.99

# Don't change this
alias awsrun='aws --region ${REGION} --output text $1'
TIERNAMELOWER=`echo ${TIERNAME} | tr '[:upper:]' '[:lower:]'`
SSHKEYNAME=${TIERNAMELOWER}-key
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

```bash
awsrun ec2 create-key-pair --key-name ${SSHKEYNAME} --query 'KeyMaterial' > ${SSHKEYNAME}.pem
```

Copy the key into your *~/.ssh* folder and *chmod* it to 400.

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

If you haven't done it already, copy the **ipsec.conf** file found in the strongswan folder to `/etc/ipsec.conf` on Linux or `/sumthingsumthing` on OSX.


```bash
echo 'conn '`echo ${TIERNAMELOWER}`'
	right=vpn.'`echo ${TIERNAMELOWER}.${ROOTDOMAIN}`'
	rightsubnet='`echo ${VPCBASENET}`'.0.0/16
' >> strongswan/ipsec.conf
```
This script adds the tier to the [strongswan/ipsec.conf](strongswan/ipsec.conf) file.


## Provisioning Drift Tier Servers
Each Drift tier runs a few off the shelf servers or services:

 - VPN server.
 - S3 buckets.
 - Redis server.
 - Postgres server.
 
At the moment these services are set up semi-manually.

**NOTE! In the Bash code, set the proper values in to the environment variables before executing the rest of the commands. The ones that require changes are grouped together in the examples below.**


### VPN Server

#### ERRATA - Use aws NAT service!
 - In AWS web console, go to **VPC** dashboard.
 - Select **NAT Gateways** and click on **Create NAT Gateway**. Select the public subnet of the tier, assign/create elastic IP for it and click on **Create a NAT Gateway**.
 - Select **Route Tables**.
 - Select the tiers *private* route table, click on **Routes** tab and click **Edit**.
 - For destination `0.0.0.0/0` change the target to the newly created nat instance. (The AWS nat resource id's are prefixed with *nat-*).
 - Add a new entry for destination `10.3.0.0/16` and assign the VPN box as target. (The VPN box instance name is *TIERNAME-nat* so it's easy to spot).



##### Launch the EC2 instance
The latest Ubuntu-Trusty 14.04 AMI is used as base image.

The launch script is loosely based on [how to set up strongSwan on AWS](https://wiki.strongswan.org/projects/strongswan/wiki/AwsVpc).

![](img/1449085590_warning.png) Run this command from the root of your **drift-aws** repo:

```bash
SGNAME=${TIERNAME}-nat-sg
SGNAMEPRIV=${TIERNAME}-private-sg
VPCID=`aws ec2 describe-vpcs --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-vpc | grep "VPCS" | cut -f 7`
SGID=`aws ec2 describe-security-groups --region ${REGION} --output text --filters Name=tag:Name,Values=${SGNAME} | grep SECURITYGROUPS | cut -f 3`
SGIDPRIV=`aws ec2 describe-security-groups --region ${REGION} --output text --filters Name=tag:Name,Values=${SGNAMEPRIV} | grep SECURITYGROUPS | cut -f 3`
AMI=`aws ec2 describe-images --region ${REGION} --output text --output text --owners 099720109477 --filters Name=name,Values="ubuntu*trusty*14.04*" --query 'Images[*].[CreationDate,ImageId,Name]'  | grep ubuntu/images/hvm/ubuntu-trusty-14.04 | sort | tail -n 1 | cut -f 2`
SUBNETID=`aws ec2 describe-subnets --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-public-subnet-1 | grep SUBNETS | cut -f 8`

LAUNCHSCRIPT=`cat strongswan/configure-strongswan.sh`
   
EC2ID=`aws ec2 run-instances --region ${REGION} --output text --image-id ${AMI} --count 1 --instance-type t2.small --key-name ${SSHKEYNAME} --security-group-ids ${SGID} ${SGIDPRIV} --subnet-id ${SUBNETID} --monitoring Enabled=true --disable-api-termination --iam-instance-profile Name=nat --user-data ${LAUNCHSCRIPT} | grep INSTANCES | cut -f 8`

echo NAT Box instance: ${EC2ID}
awsrun ec2 wait instance-running --instance-ids ${EC2ID}
```

Once the instance is available, continue here to tag the instance, turn off source-dest check, allocate an elastic IP address and add a route from within the VPC out to VPN clients:

```bash
aws ec2 create-tags --region ${REGION} --output text --resources ${EC2ID} --tags Key=Name,Value=${TIERNAME}-nat  Key=tier,Value=${TIERNAME} Key=service-name,Value=nat

aws ec2 modify-instance-attribute --region ${REGION} --output text --instance-id ${EC2ID} --source-dest-check "{\"Value\": false}"

EIPALLOCID=`aws ec2 allocate-address --region ${REGION} --output text --domain ${VPCID} | cut -f 1`
aws ec2 associate-address --region ${REGION} --output text --instance-id ${EC2ID} --allocation-id ${EIPALLOCID}

RTPUB=`aws ec2 describe-route-tables --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-rtbl-internet | grep ROUTETABLES | cut -f 2`
aws ec2 create-route --region ${REGION} --output text --route-table-id ${RTPUB} --destination-cidr-block 10.3.0.0/16 --instance-id ${EC2ID}
RTPRIV=`aws ec2 describe-route-tables --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-rtbl-private | grep ROUTETABLES | cut -f 2`
aws ec2 create-route --region ${REGION} --output text --route-table-id ${RTPRIV} --destination-cidr-block 0.0.0.0/0 --instance-id ${EC2ID}
VPNIP=`aws ec2 describe-addresses --region ${REGION} --output text --filters Name=allocation-id,Values=${EIPALLOCID} --query 'Addresses[*].[PublicIp]'`

VPNDNS=`awsrun ec2 describe-instances --instance-ids ${EC2ID} --query 'Reservations[0].Instances[0].[PublicDnsName]'`

echo NAT Box IP address: ${VPNIP}
echo NAT Box DNS Name: ${VPNDNS}

```

Remember to add DNS entry to the instance. The address is in `${VPNIP}` environment variable.

*Note: If external SSH access is needed, the security group must be modified to allow SSH traffic from the internet (preferably to our own public IP address). Here are the commands to connect:*

```bash
ssh ubuntu@${VPNIP} -i ~/.ssh/${SSHKEYNAME}.pem
```


### Strongswan Config
 * Make a DNS entry which points to the NAT/VPN instance (See Adding DNS section below).
 * Add the new tier to */strongswan/ipsec.conf*


### RabbitMQ Server
The RabbitMQ server is a single EC2 instance running Ubuntu and RabbitMQ.

![](img/1449085590_warning.png) Run this command from the root of your **drift-aws/rabbitmq** repo and folder:

##### These keypairs are used globally
```bash
TIERNAME=roxxor-dev
SSHKEYNAME=dgn-dev-ec2
REGION=eu-west-1
```

##### Use Packer to provision the RabbitMQ AMI
```bash
AMI=`aws ec2 describe-images --region ${REGION} --output text --owners 099720109477 --filters Name=name,Values="ubuntu*trusty*14.04*" --query 'Images[*].[CreationDate,ImageId,Name]'  | grep ubuntu/images/hvm/ubuntu-trusty-14.04 | sort | tail -n 1 | cut -f 2`
echo "Using AMI ${AMI}"
packer build -var source_ami=${AMI} -var rabbit_pwd=rabbit -var admin_pwd=rabbit -var tier=${TIERNAME} -var aws_region=${REGION} rabbitmq.json
```

##### Launch the RabbitMQ instance
```bash
SGNAME=${TIERNAME}-rabbitmq-sg
SGNAMEPRIV=${TIERNAME}-private-sg
SGID=`aws ec2 describe-security-groups --region ${REGION} --output text --filters Name=tag:Name,Values=${SGNAME} | grep SECURITYGROUPS | cut -f 3`
SGIDPRIV=`aws ec2 describe-security-groups --region ${REGION} --output text --filters Name=tag:Name,Values=${SGNAMEPRIV} | grep SECURITYGROUPS | cut -f 3`
AMINAME=rabbitmq
OWNERID=092475124519
AMI=`aws ec2 describe-images --region ${REGION} --output text --owners ${OWNERID} --filters Name=name,Values="${AMINAME}*" | grep IMAGES | sort | tail -n 1 | cut -f 5`
SUBNETID=`aws ec2 describe-subnets --region ${REGION} --output text --filters Name=tag:Name,Values=${TIERNAME}-private-subnet-1 | grep SUBNETS | cut -f 8`

LAUNCHSCRIPT='
#!/bin/bash
sudo rabbitmqctl delete_user guest
sudo rabbitmqctl add_user rabbit rabbit
sudo rabbitmqctl set_permissions -p / rabbit ".*" ".*" ".*"
sudo rabbitmqctl add_user rabbit_admin rabbit
sudo rabbitmqctl set_permissions -p / rabbit_admin ".*" ".*" ".*"
sudo rabbitmqctl set_user_tags rabbit_admin administrator
'

EC2ID=`aws ec2 run-instances --region ${REGION} --output text --image-id ${AMI} --count 1 --instance-type t2.small --key-name ${SSHKEYNAME} --security-group-ids ${SGID} ${SGIDPRIV} --subnet-id ${SUBNETID} --monitoring Enabled=true --disable-api-termination --iam-instance-profile Name=rabbitmq --user-data ${LAUNCHSCRIPT} | grep INSTANCES | cut -f 8`
echo "Instance launched: ${EC2ID}"
aws ec2 create-tags --region ${REGION} --output text --resources ${EC2ID} --tags Key=Name,Value=${TIERNAME}-rabbitmq  Key=tier,Value=${TIERNAME} Key=service-name,Value=rabbitmq
RABBITIP=`aws ec2 --region ${REGION} describe-instances --instance-ids ${EC2ID} --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text`

echo RabbitMQ IP address: ${RABBITIP}
echo Please add a DNS A record for this: rabbitmq.${TIERNAMELOWER}.${ROOTDOMAIN}
```

Remember to add DNS entry to the instance as described by the last echos from the script above.

**ERRATA**: The *rabbitmqctl* commands are not working, neither in the baking nor in the launch script. The only current work-around is to **ssh** into the instance and run the commands there manually:

```bash
ssh ubuntu@${RABBITIP} -i ~/.ssh/${SSHKEYNAME}.pem
sudo rabbitmqctl delete_user guest
sudo rabbitmqctl add_user rabbit rabbit
sudo rabbitmqctl set_permissions -p / rabbit ".*" ".*" ".*"
sudo rabbitmqctl add_user rabbit_admin rabbit
sudo rabbitmqctl set_permissions -p / rabbit_admin ".*" ".*" ".*"
sudo rabbitmqctl set_user_tags rabbit_admin administrator

```

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
DBSUBNETGROUP=`aws rds describe-db-subnet-groups --region ${REGION} --output text | grep ${TIERNAME}-db-subnetgroup | cut -f 3`
aws rds create-db-instance --region ${REGION} --output text --db-name postgres --db-instance-identifier ${TIERNAME}-postgresql --allocated-storage 20 --db-instance-class db.t2.small --engine postgres --master-username postgres --master-user-password postgres --vpc-security-group-ids ${SGID} --db-subnet-group-name ${DBSUBNETGROUP} --no-multi-az --no-publicly-accessibl --tags Key=tier,Value=${TIERNAME} --storage-type gp2

awsrun rds wait db-instance-available --db-instance-identifier ${TIERNAME}-postgresql

POSTGRESQLADDR=`aws rds --region ${REGION} describe-db-instances --db-instance-identifier ${TIERNAME}-postgresql --query 'DBInstances[0].Endpoint.Address' --output text`
```

Remember to add DNS entry to the instance. The address is in `${POSTGRESQLADDR}` environment variable.

## Adding servers to DNS
Create a DNS entry for each of the servers. Example:


| Name       | Type | Env Var | Example Value |
| ---------- | ---- | ------- |-------------- |
|redis.devnorth.dg-api.com | CNAME | ${REDISADDR} | devnorth-redis.xnves0.0001.euw1.cache.amazonaws |
|postgres.devnorth.dg-api.com | CNAME | ${POSTGRESQLADDR} | devnorth-postgresql.c40zji49p9dj.eu-west-1.rds.amazonaws |
|rabbitmq.devnorth.dg-api.com | A | ${RABBITIP} | 10.50.1.76 |
|vpn.devnorth.dg-api.com| A | ${VPNIP} |52.18.20.30|



 
 

  