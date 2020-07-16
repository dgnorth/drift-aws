

@echo off

python templater.py

python cfn.py -c templates/drift-cfn-tier.json --region=eu-west-1 -p StackGroup=%1 -p TierName=%1 %1
python cfn.py -c templates/drift-cfn-vpc.json --region=eu-west-1 -p StackGroup=%1 -p VPCBaseNet=%2 %1-vpc
