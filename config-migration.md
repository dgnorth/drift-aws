


# DEVEAST upgrade steps
March 27th, 2017

> ERRATA: Pushing config to origin may require the --force switch due to a bug in the crc check.

## AWS prep

Nuke all ec2's except NAT and api-router.


## Config prep

Add dg-superkaiju tier, deployables, product and tenant:

```bash
dconf tier add DEVEAST --is-dev
dconf deployable register all --tier DEVEAST
dconf organization add directivegames dg
dconf product add dg-superkaiju
dconf tenant add dg-superkaiju-deveast dg-superkaiju


driftconfig addtenant dgnorth -n dg-superkaiju-deveast -t DEVEAST -o directivegames -p dg-superkaiju -d drift-base
driftconfig push dgnorth
```

The config is missing the auto-filled entries for aws. This needs to be added manually until the provision logic is fully rigged.

domain.json:

```json
    "aws": {
        "ami_baking_region": "eu-west-1"    },
    ...
```

tiers.json:

```json
    {
        "tier_name": "DEVEAST",
        "aws": 
        {
            "region": "ap-southeast-1",
            "ssh_key": "livenorth-key"            
        }, 
        "celery_broker_url": "redis://redis.deveast.dg-api.com:6379/15",
        "service_user": 
        {            "password": "SERVICE",             "username": "user+pass:$SERVICE$"        },       
      
       "resource_defaults": [            {                "parameters": {                    "database": null,                     "driver": "postgresql",                     "password": "zzp_user",                     "port": 5432,                     "server": "postgres.deveast.dg-api.com",                     "username": "zzp_user"                },                 "resource_name": "postgres"            },             {                "parameters": {                    "host": "redis.deveast.dg-api.com",                     "port": 6379,                     "socket_connect_timeout": 5,                     "socket_timeout": 5                },                 "resource_name": "redis"            },             {                "parameters": {                    "build_bucket_url": ""                },                 "resource_name": "gameserver"            },             {                "parameters": {                    "allow_client_pin": false,                     "repository": "",                     "revision": ""                },                 "resource_name": "staticdata"            }        ], 
      
      
        ...
    }
    
```

authentication/public-keys.json:

```
...

    {        "deployable_name": "drift-base",        "keys": [            {                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAu55QGUOfqE+3dc520TEBSvn99Hc/4V8qV7Q2zV2PU5PY0MtZ\nG6ly8mW/I6VRhLX7OH4QY9Cyn9rWwi7umhtqMh/Egjg4X+X0XphJxWNcOSNLKLxA\nvPoo1LsOJcBeNg1ZMU4PYKCmAbBODgkQvQM2wQ32MAWY8LJFwEOYedpg+kanoQ02\njj74d5cnqAdylbC4kFNTO5ZCQL3HXVmo0j5lsqoCyidNEahpXo+2ROm5aZl8tqfE\neaD/+c4txkcMsylo/gdAliFPLUZVUzbZzxYO+RU4H6d2gw/bwUib92n1zj91zccx\nZxluy+W8nh94GjMGjxxDKpvagmiqKGDMZszBUwIDAQABAoIBAQCp1+cq98zQ0VmD\njCSDu5kwBp+fb1Sk8UGjo8D4qHnXb0AXw/4mzH8CcJlX65CgUx3ZRkYQFh2eGL3R\njCrz112LgraiK8LdDY7rE3G0/v29u/WOKt1wNgZAjhWAl2SyCeN0fvXsw4GEhdYj\nXpGIiiBHJBx53JdXTgtWwdqGdOrVpRPGTDQt4v9lWPH3I1IDdeGDpvbp3ZkznYMz\nb2fe6WaKRM/DJ0s5vn42TwXYpnSVDBoCK6FvSBJBax6T416FzESxS/tZPwpv0AMU\nkLxwnx54ZpSovchY6Od1wkZkhYO14MVzcV6oPDGK6u9wiuPCOQac2HvX+dcJpdRv\nzkK7XOwBAoGBAN4R9QwliKbLovxB4fnDLm6CoEtzYAwxfPS7Af/hLRvyke33r+HH\nU2Ed/0VtLaOIt+wndPCf5pjWXayI7OTOXGCqTKPWqsU9s0W0Fdzu0T9M8NOIEXAL\nl9aSWr/1ehcg/6Jv2NcOMrtextU8rjIas79FI6Njps3KKkszU9rVhXu7AoGBANhI\nz9Xt/05SX3661eYDoZynNSAC8fyLSfnGk76yTgUKMabgUCRzcCFuWYBpocsO/y/X\nhy3DLhtuA49T/SYPJRUKeYWqf8Y2bvDPXwzjMAi8ae3HAYQFeoEL8/OXAwcEFQqC\n+d+fNL4qcX/6dZq488eb2z6i0yfErzC+xgdXs1tJAoGAS///SmnqC5Nzsztk+BKJ\naH7CFzBkNagWKLd7prPMuVzZ/oQfKHkMGxemDn+f9/DJaUPTrKo8xB/RLUQrNt89\nFEQUOJo2FYzZNsi8FsGQ0UYmwW428Y62J1QtRLbhUtsTQedfYbJVQHTePYon37Pt\nwk8KNFfddV5z/QqS7zjWFxMCgYBT9Bdww/xJC6Jzz9Q9f4VZCHKPpXUHAY5KfTFW\nYWH1hNp3GzUgoQqSf4IQXXBnIMAfcvrO4adhEFgjZ4epIVHUlAdNwjvs1a5EnUoY\n94rqqTA5EvlcpL/Dnb8o+6I6M/Ry6xpRGjxf4JvEAJVr5IUEI1R8QLnUAv253yOB\nMCK3uQKBgQCQXl6GWEPTJccPfbsHTR8orHxDUoQ96AgaXyVVligKNdyxxmQGTfJL\nGCpdFZsutQmhjR8/x3hLyfgbFAJdhZYeLbRLCcv85LIpc9WZ+9oGbPepFlYsTWHI\n5XBWmUQGRs4PDqD+btKHsmM3Yi/W85gwGcO/YfjRUPQPfxGZG1m+WA==\n-----END RSA PRIVATE KEY-----",                "pub_rsa": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7nlAZQ5+oT7d1znbRMQFK+f30dz/hXypXtDbNXY9Tk9jQy1kbqXLyZb8jpVGEtfs4fhBj0LKf2tbCLu6aG2oyH8SCODhf5fRemEnFY1w5I0sovEC8+ijUuw4lwF42DVkxTg9goKYBsE4OCRC9AzbBDfYwBZjwskXAQ5h52mD6RqehDTaOPvh3lyeoB3KVsLiQU1M7lkJAvcddWajSPmWyqgLKJ00RqGlej7ZE6blpmXy2p8R5oP/5zi3GRwyzKWj+B0CWIU8tRlVTNtnPFg75FTgfp3aDD9vBSJv3afXOP3XNxzFnGW7L5byeH3gaMwaPHEMqm9qCaKooYMxmzMFT drift-base@dg-api.com"            }        ],        "tier_name": "DEVEAST"    }
    ...
    
    DUPLICATE ENTRY ABOVE FOR superkaiju-backend AS WELL!
```

deployables.json:

```json

    {        "deployable_name": "superkaiju-backend",         "is_active": true,         "jwt_trusted_issuers": [            {                "iss": "drift-base",                 "pub_rsa": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7nlAZQ5+oT7d1znbRMQFK+f30dz/hXypXtDbNXY9Tk9jQy1kbqXLyZb8jpVGEtfs4fhBj0LKf2tbCLu6aG2oyH8SCODhf5fRemEnFY1w5I0sovEC8+ijUuw4lwF42DVkxTg9goKYBsE4OCRC9AzbBDfYwBZjwskXAQ5h52mD6RqehDTaOPvh3lyeoB3KVsLiQU1M7lkJAvcddWajSPmWyqgLKJ00RqGlej7ZE6blpmXy2p8R5oP/5zi3GRwyzKWj+B0CWIU8tRlVTNtnPFg75FTgfp3aDD9vBSJv3afXOP3XNxzFnGW7L5byeH3gaMwaPHEMqm9qCaKooYMxmzMFT drift-base@dg-api.com"            }        ],         "tags": [            "core",             "product"        ],         "tier_name": "DEVEAST"    },   

```

> Also had to make a new file in legacy auth config. See **directive-tiers/tiers/DEVEAST/superkaiju-backend.json** for more info.

## DNS entry for the Endpoint
Make a DNS entry for the tenant:

```
# In Route53 AWS console:
Name:  dg-superkaiju-deveast.dg-api.com
Type:  A record
Alias: dualstack.deveast-api-router-lb-auto2-625491317.ap-southeast-1.elb.amazonaws.com.
```

## Provision tenant resources

Run this on your local machine:

```bash
drift-admin --tier DEVEAST tenant dg-superkaiju-deveast create
```

## Prepare an AMI for drift-base

In the **drift-base** folder:

```bash
drift-admin ami bake
drift-admin --tier DEVEAST ami run
```


## Fixes made to superkaiju-backend code

#### superkaiju-backend project
All the files in drift-base/config copied over, renamed accordingly and the contents search-replaced for "drift-base" -> "superkaiju-backend".

> Remember to copy and fix up ALL THE FILES!

The project was baked and run:

```bash
# Executed from superkaiju-backend root folder:
drift-admin --tier DEVEAST ami bake
drift-admin --tier DEVEAST ami run
```

#### api-router
The current api-router is using the old config mgmt. The json file in directive-tiers/tiers/DEVEAST.JSON was updated manually with this, and then published:

```json
        {
            "name": "superkaiju-backend",
            "api": "superkaiju",
            "ssh_key": "deveast-key.pem"
        },
```


