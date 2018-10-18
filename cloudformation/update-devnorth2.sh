python templater.py
cfn -c templates/drift-cfn-vpc.json --region=eu-west-1 -u -p StackGroup=DEVNORTH2 -p VPCBaseNet=10.52 DEVNORTH2-vpc
