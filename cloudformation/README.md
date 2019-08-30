# Drift Cloudformation Templates

A single Drift tier is composed of several CFN templates. They use parameters to define specific behavior and export explicitly references to certain resources so there is no need to assume any naming convention of the resources themselves.

All of them are agnostic to particular types of tiers so there should be no need to customize the templates themselves. 

This approach may also fit well with the [Stack Sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html) concept.

## Base template features:
All the templates include these basic features:

```
Parameters:
 - StackGroup: Name of the stack group this stack belongs to. It's typically the tier name."

```


## Tier:
This is the root template and simply defines the tier itself and exports some useful values like the name of the tier.

```
Stack Name: STACKGROUP-tier
  - logs.LogGroup (really just to have some resource in this template)
  
Parameters:
  - TierName

Exports:
  - STACKGROUP-tier-name = Ref(TierName)
```


## VPC:

Configuration for the VPC. This template contains only pure VPC resources.

```
 Stack Name: STACKGROUP-vpc
 - VPC
 - Route tables
 - Subnets (public, private, db) + rtblassoc
 - Internet Gateway
 - NAT Gateway
 - Security group for 10.0.0.0/8

 Parameters:
  - VPCBaseNet

 Exports:
  - TIERNAME-vpc-id = VPC
  - TIERNAME-vpc-base-net = VPCBaseNet
  - TIERNAME-vpc-public-subnet-1 = PublicSubnet1 (note, all subnets)
```


## Postgres:

```
 Stack Name: TIERNAME-postgres
 - DBInstance (postgres)
 - rds.DBSubnetGroup
 - Security group for 10.0.0.0/8, tcp port 5432,5433
 - route53.RecordSetType (ex: name=postgres.devnorth.dg-api.com)
```

## Redis:
```
 Stack Name: TIERNAME-redis
 - CacheCluster (redis)
 - elasticache.SubnetGroup
 - Security group for 10.0.0.0/8, tcp port 6379
 - route53.RecordSetType (ex: name=redis.devnorth.dg-api.com)
```

## VPN:
```
 Stack Name: TIERNAME-vpn
 - EIP
 - route53.RecordSetType on EIP, (ex: name=vpn.devnorth.dg-api.com)
 - EC2 or AMI
 - route53.RecordSetType (ex: name=vpn.devnorth.dg-api.com)
```


## Drift REST API/web deployable:
```
 Stack Name: TIERNAME-service-name
 - AutoScalingGroup
```


## API router:
```
 Stack Name: TIERNAME-drift-apirouter
 - AutoScalingGroup
 - elb.LoadBalancer
 - route53.RecordSetType (ex: name=*.devnorth.dg-api.com)
 - certificatemanager.Certificate
```


### ruslakista?
 - s3.Bucket (ex: name=logs.devnorth.dg-api.com)

