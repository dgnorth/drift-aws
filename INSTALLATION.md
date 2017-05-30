# How to rig up Drift Tier on AWS

## Create a new account on AWS
 - Create a new account on AWS if you don't have one already.
 - Turn on MFA for the master account.
 - Create an IAM user, assign MFA to it and assign administration role.
 - Use the IAM account instead of the master account from now on.
 - For general prettyness, customize the IAM user sign-in link (IAM dashboard, top of page)


## Configure AWS command line tool.
 - Install AWS CLI.
 - Generate access keys in the IAM web console.
 - run `aws Configure` and put in the access keys.


## Create domain for your organization.
 - In Route 53, register a new domain for the web services. (Don't use your main organization domain).
 - Make it clear that the domain is a web service domain, example: wickedstuff-api.com or wickedstuffapi.io.
 - Register a wildcard certificate on the domain using AWS Certificate Manager. (Both root and wild).


## Set up a VPC
Read the **Creating a New Drift Tier** section in the README.md file which is located in the same folder as this file. 

The first tier should be a "live" tier. Development and staging tiers can be added later if needed.

The name of the tier should be in upper case and for live tier, it should start with the letters LIVE. The subnet should start on 10.75.x.x. or something similar.


## Set up Strongswan

Copy the strongswan folder from drift-aws and edit accordingly.


## Prepare role for EC2's
In IAM, create a role called **nat** and assign AmazonS3FullAccess policy to it, and another role called **ec2** and assign PowerUserAccess to it.


