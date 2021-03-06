'''
AWS CloudFormation Template generator

This template describes a VPC and associated objects neccessary to run a
drift based stack.


To use:

python vpc.py > vpc.json

create stack:

aws cloudformation create-stack --stack-name roxxor-dev  --template-body file://./vpc.json --parameters ParameterKey=VPCBaseNet,ParameterValue=10.22

or

cfn -c vpc.json -t -p VPCBaseNet=10.87 --region=eu-west-1 roxxor-dev



delete stack:
aws cloudformation delete-stack --stack-name roxxor-dev


info:
aws cloudformation describe-stack-events --stack-name roxxor-dev

'''


from troposphere import Join, Output, Parameter, Ref, Tags, Template, GetAZs, Select, GetAtt, Export, Sub
from troposphere import ec2, rds, elasticache, s3, elasticloadbalancing

def _(*args):
    """Join elements together to make a string. I.e. wrap all items in 'args'
    into a Fn::Join template function.
    """
    return Join("", list(args))


def get_resource_name(resource_name):
    """Returns a templatizable name with tier name and 'postfix' added together."""
    return _(get_tier(), "-", resource_name)


def get_tier():
    """Returns a templatizable name of the tier."""
    return Ref("AWS::StackName")  # Tier name is currently the same as stack name.


class TierTags(Tags):
    """Enforces 'Name' to be set to 'tier_name' + resource_name,
    and adds tier='tier_name' to tag set.
    """
    def __init__(self, resource_name, **kwargs):
        kwargs["Name"] = get_resource_name(resource_name)
        kwargs["tier"] = get_tier()
        return super(TierTags, self).__init__(**kwargs)


t = Template()
t.add_version("2010-09-09")
t.add_description("""\
AWS VPC with VPN access.

This template describes a VPC and associated objects neccessary to run a
drift based stack.

Objects:

    * VPC
    * Subnets
    * Route Tables
    * Internet Gateways
    * NAT Gateways
    * Security Groups
    * Network ACLs

Servers:

    * Redis
    * Postgres
""")

# The VPC base net is e.g. 10.85.x.x
vpc_base_net = t.add_parameter(Parameter(
    "VPCBaseNet",
    ConstraintDescription=(
        "must be a valid first two IP numbers of the form x.x"),
    Description="The first two IP numbers for the VPC CIDR.",
    Default="10.1",
    MinLength="4",
    AllowedPattern="(\d{1,3})\.(\d{1,3})",
    MaxLength="18",
    Type="String",
))


# The VPC object
vpc = t.add_resource(ec2.VPC(
    "VPC",
    CidrBlock=_(Ref(vpc_base_net), ".0.0/16"),
    EnableDnsSupport="true",
    EnableDnsHostnames="true",
    Tags=TierTags("vpc", created_by=Ref("AWS::AccountId"))
))


# Each VPC has two public subnet, two private subnets and two RDS subnets, covering
# two availability zones.
# x.x.0.x and x.x.10.x are public subnets
# x.x.1.x and x.x.2.x are private subnets
# x.x.91.x and x.x.92.x are RDS subnets
def add_subnet(tag_name, ip_part, route_table, az, realm):
    """Add a subnet named 'tag_name' with 'ip_part as the /24 domain and
    associated with 'route_table'. 'az' is the index into list of availability
    zones, i.e. "0", "1" or "2".
    Export the subnet ID.
    """
    template_name = tag_name.title().replace('-', '')
    subnet = ec2.Subnet(
        template_name,
        VpcId=Ref("VPC"),
        CidrBlock=_(Ref(vpc_base_net), ".{}.0/24".format(ip_part)),
        AvailabilityZone=Select(az, GetAZs()),
        Tags=TierTags(tag_name, realm=realm)
    )
    subnet = t.add_resource(subnet)

    t.add_output([
        Output(
            template_name,
            Description="The ID of this subnet.",
            Value=Ref(subnet),
            Export=Export(_(Sub("${AWS::StackName}-"), tag_name)),
        )
    ])

    t.add_resource(ec2.SubnetRouteTableAssociation(
        "{}RouteTableAssociation".format(template_name),
        SubnetId=Ref(subnet),
        RouteTableId=Ref(route_table)
    ))

    return subnet

# One public route table and one private route table
public_rtbl = t.add_resource(ec2.RouteTable(
    "PublicRouteTable",
    VpcId=Ref("VPC"),
    Tags=TierTags("rtbl-internet")
))

private_rtbl = t.add_resource(ec2.RouteTable(
    "PrivateRouteTable",
    VpcId=Ref("VPC"),
    Tags=TierTags("rtbl-private")
))


# The public and private subnets
public_subnet_1 = add_subnet("public-subnet-1", "21", public_rtbl, "0", 'public')
public_subnet_2 = add_subnet("public-subnet-2", "22", public_rtbl, "1", 'public')
private_subnet_1 = add_subnet("private-subnet-1", "1", private_rtbl, "0", 'private')
private_subnet_2 = add_subnet("private-subnet-2", "2", private_rtbl, "1", 'private')

# Managed DB's get their own subnets, referenced through a special DB subnet group
db_subnet_1 = add_subnet("db-subnet-1", "91", private_rtbl, "0", 'db')
db_subnet_2 = add_subnet("db-subnet-2", "92", private_rtbl, "1", 'db')
db_subnet_group = t.add_resource(rds.DBSubnetGroup(
    "DBSubnetGroup",
    DBSubnetGroupDescription=get_resource_name("db-subnetgroup-desc"),
    SubnetIds=[Ref(db_subnet_1), Ref(db_subnet_2)],
    Tags=TierTags("db-subnetgroup")
))

# The public route table need an Internet gateway
t.add_resource(ec2.InternetGateway(
    "InternetGateway",
    Tags=TierTags("internet-gateway")
))
t.add_resource(ec2.VPCGatewayAttachment(
    "InternetGatewayAttachment",
    InternetGatewayId=Ref("InternetGateway"),
    VpcId=Ref("VPC"),
    DependsOn="InternetGateway"
))

t.add_resource(ec2.Route(
    "IGWRoute",
    GatewayId=Ref("InternetGateway"),
    DestinationCidrBlock="0.0.0.0/0",
    RouteTableId=Ref("PublicRouteTable"),
))

# NAT Gateway for private subnets
nat_eip = t.add_resource(ec2.EIP(
    'NatEip',
    Domain="vpc",
))

nat = t.add_resource(ec2.NatGateway(
    'NatGateway',
    AllocationId=GetAtt(nat_eip, 'AllocationId'),
    SubnetId=Ref(public_subnet_1),
))

t.add_resource(ec2.Route(
    'NatRoute',
    RouteTableId=Ref(private_rtbl),
    DestinationCidrBlock='0.0.0.0/0',
    NatGatewayId=Ref(nat),
))

# Set up general security groups for the VPC and some specific ones for the
# following servers:
# - VPN server.
# - RabbitMQ server.
# - Redis server.
# - Postgres server.

# A catch-all group allowing all traffic from 10.x.x.x private network.
private_sg = t.add_resource(ec2.SecurityGroup(
    "PrivateSecurityGroup",
    VpcId=Ref("VPC"),
    Tags=TierTags("private-sg"),
    GroupDescription="Allow all traffic on 10.x.x.x",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="-1",
            FromPort="-1",
            ToPort="-1",
            CidrIp="10.0.0.0/8",
        ),
    ],
))


# Allow incoming HTTPS traffic from any remote address.
t.add_resource(ec2.SecurityGroup(
    "HTTPSSecurityGroup",
    VpcId=Ref("VPC"),
    Tags=TierTags("https-sg"),
    GroupDescription="Allow incoming HTTPS traffic from any remote address.",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="443",
            ToPort="443",
            CidrIp="0.0.0.0/0",
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="80",
            ToPort="80",
            CidrIp="0.0.0.0/0",
        ),
    ],
))


t.add_output([
    Output(
        "VPCId",
        Description="VPCId of the newly created VPC.",
        Value=Ref(vpc),
    ),
    Output(
        "VPCBaseNet",
        Description="VPCId of the newly created VPC.",
        Value=Ref("VPCBaseNet"),
    ),
    Output(
        "StackVPC",
        Description="The ID of the VPC.",
        Value=Ref(vpc),
        Export=Export(Sub("${AWS::StackName}-VPCID")),
    ),
])


print t.to_json()
#print t.to_yaml()
