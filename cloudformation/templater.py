'''
AWS CloudFormation Template generator
'''


from troposphere import Join, Output, Parameter, Ref, Tags, Template, GetAZs, Select, Split, GetAtt, Export, Sub, ImportValue
from troposphere import ec2, rds, elasticache, s3, elasticloadbalancing

from troposphere import cloudformation, autoscaling
from troposphere.autoscaling import AutoScalingGroup, Tag, LifecycleHookSpecification

from troposphere.policies import (
    AutoScalingReplacingUpdate, AutoScalingRollingUpdate, UpdatePolicy
)

def _(*args):
    """Join elements together to make a string. I.e. wrap all items in 'args'
    into a Fn::Join template function.
    """
    return Join("", list(args))


class DriftTemplate(object):

    """
    Drift Cloudformation Template helper class.

    Creates an instance of Template with some default parameters and provides
    context rich helper functions.
    """
    def __init__(self, template_name, description):
        """
        'template_name' is used when naming exported values. It is usually the name
        of the template itself or a drift deployable.
        'description' is added to the template description.
        """
        self.template_name = template_name
        self.t = Template()
        self.t.add_version("2010-09-09")
        self.t.add_description(description)

        # Parameters required for all Drift templates
        self.stack_group = self.t.add_parameter(Parameter(
            "StackGroup",
            Type="String",
            Description="Name of the stack group this stack belongs to. It's typically the tier name.",
        ))

    def export_value(self, name, description, *values):
        """
        Export a value using the key STACKGROUP-<template name>-<name>.
        If more than a single value is specified, it will be Join'ed together into a
        comma separated string.
        'description' is a description of the exported value.
        """
        title = name.title().replace('-', '')
        export_name = _(Ref(self.stack_group), "-{}-{}".format(self.template_name, name))
        if len(values) == 0:
            raise RuntimeError("Missing value argument!")
        elif len(values) == 1:
            value = values[0]
        else:
            value = Join(',', values)

        output = Output(
            title=title,
            Description=description,
            Value=value,
            Export=Export(export_name)
        )

        self.t.add_output(output)

    def import_value(self, name, index=None):
        """
        Import a value using the key STACKGROUP-<name>.
        If the value is an array, select the object using 'index', a number from 0 to n-1.
        """
        export_name = _(Ref(self.stack_group), "-{}".format(name))
        if index is None:
            value = ImportValue(export_name)
        else:
            value = Select(str(index), Split(',', ImportValue(export_name))),

        return value

    def get_tier_name(self):
        """Returns the tier name by looking up the exported value from STACKGROUP-tier-name."""
        return self.import_value('tier-name')

    def get_resource_name(self, resource_name):
        """Returns a templatizable name with stackgroup and 'resource_name' added together."""
        return _(Ref(self.stack_group), "-", resource_name)

    def get_tags(self, resource_name, **kwargs):
        """
        Returns Tags instance with tags from 'kwargs' plus the following default tags:
        Name=<STACKGROUP>-<resource_name>
        tier=<TIERNAME>
        """
        kwargs["Name"] = self.get_resource_name(resource_name)
        kwargs["tier"] = self.get_tier_name()
        return Tags(**kwargs)


from troposphere import logs


class Tier(DriftTemplate):

    def __init__(self):
        DriftTemplate.__init__(self, 'tier', "The root template that defines the tier itself.")

        # The tier name is defined here..
        self.tier_name = self.t.add_parameter(Parameter(
            "TierName",
            Type="String",
            Description="Name of the tier this stack group belongs to.",
        ))
        # ..and exported for every other stack to use.
        self.export_value('name', "Tier name.", Ref(self.tier_name))

        # This template really doesn't need to define any resources but it is not possible to
        # create a resource-less stack. Let's create something then:
        self.t.add_resource(
            logs.LogGroup(
                'LogGroup',
                LogGroupName=self.get_resource_name('main-log-group')
            )
        )

    def get_tier_name(self):
        # Override this as we are the root stack
        return Ref(self.tier_name)


class VPC(DriftTemplate):

    def __init__(self):
        DriftTemplate.__init__(self, 'vpc', "VPC resources.")

        self.vpc_base_net = self.t.add_parameter(Parameter(
            "VPCBaseNet",
            ConstraintDescription=(
                "must be a valid first two IP numbers of the form x.x"),
            Description="The first two IP numbers for the VPC CIDR.",
            MinLength="4",
            AllowedPattern="(\d{1,3})\.(\d{1,3})",
            MaxLength="18",
            Type="String",
        ))

        # The VPC
        self.vpc = self.t.add_resource(ec2.VPC(
            "VPC",
            CidrBlock=_(Ref(self.vpc_base_net), ".0.0/16"),
            EnableDnsSupport="true",
            EnableDnsHostnames="true",
            Tags=self.get_tags('vpc', created_by=Ref("AWS::AccountId"))
        ))

        # Route tables, one public and one private.
        self.public_rtbl = self.t.add_resource(ec2.RouteTable(
            "PublicRouteTable",
            VpcId=Ref("VPC"),
            Tags=self.get_tags("rtbl-internet")
        ))

        self.private_rtbl = self.t.add_resource(ec2.RouteTable(
            "PrivateRouteTable",
            VpcId=Ref("VPC"),
            Tags=self.get_tags("rtbl-private")
        ))


        # Subnets
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
                VpcId=Ref(self.vpc),
                CidrBlock=_(Ref(self.vpc_base_net), ".{}.0/24".format(ip_part)),
                AvailabilityZone=Select(az, GetAZs()),
                Tags=self.get_tags(tag_name, realm=realm)
            )
            subnet = self.t.add_resource(subnet)

            self.t.add_resource(ec2.SubnetRouteTableAssociation(
                "{}RouteTableAssociation".format(template_name),
                SubnetId=Ref(subnet),
                RouteTableId=Ref(route_table)
            ))

            return subnet

        # The public and private subnets
        self.public_subnet_1 = add_subnet("public-subnet-1", "21", self.public_rtbl, "0", 'public')
        self.public_subnet_2 = add_subnet("public-subnet-2", "22", self.public_rtbl, "1", 'public')
        self.private_subnet_1 = add_subnet("private-subnet-1", "1", self.private_rtbl, "0", 'private')
        self.private_subnet_2 = add_subnet("private-subnet-2", "2", self.private_rtbl, "1", 'private')

        # Managed DB's get their own subnets, referenced through a special DB subnet group
        self.db_subnet_1 = add_subnet("db-subnet-1", "91", self.private_rtbl, "0", 'db')
        self.db_subnet_2 = add_subnet("db-subnet-2", "92", self.private_rtbl, "1", 'db')

        # The public route table needs an Internet gateway
        self.t.add_resource(ec2.InternetGateway(
            "InternetGateway",
            Tags=self.get_tags("internet-gateway")
        ))
        self.t.add_resource(ec2.VPCGatewayAttachment(
            "InternetGatewayAttachment",
            InternetGatewayId=Ref("InternetGateway"),
            VpcId=Ref("VPC"),
            DependsOn="InternetGateway"
        ))

        self.t.add_resource(ec2.Route(
            "IGWRoute",
            GatewayId=Ref("InternetGateway"),
            DestinationCidrBlock="0.0.0.0/0",
            RouteTableId=Ref("PublicRouteTable"),
        ))

        # NAT Gateway for private subnets
        self.nat_eip = self.t.add_resource(ec2.EIP(
            'NatEip',
            Domain="vpc",
            #Tags=self.get_tags("nat-gw-eip")  # NOTE, tags not supported in Cloudformation just yet.
        ))

        self.nat = self.t.add_resource(ec2.NatGateway(
            'NatGateway',
            AllocationId=GetAtt(self.nat_eip, 'AllocationId'),
            SubnetId=Ref(self.public_subnet_1),
            Tags=self.get_tags("nat-gateway")
        ))

        self.t.add_resource(ec2.Route(
            'NatRoute',
            RouteTableId=Ref(self.private_rtbl),
            DestinationCidrBlock='0.0.0.0/0',
            NatGatewayId=Ref(self.nat),
        ))

        # A catch-all group allowing all traffic from 10.x.x.x private network.
        self.private_sg = self.t.add_resource(ec2.SecurityGroup(
            "PrivateSecurityGroup",
            VpcId=Ref("VPC"),
            Tags=self.get_tags("private-sg"),
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

        # Exported values
        self.export_value('id', "VPC ID.", Ref(self.vpc))
        self.export_value('vpc-base-net', "The first two IP numbers for the VPC CIDR.", Ref(self.vpc_base_net))
        self.export_value('public-subnets', "Public subnets.", Ref(self.public_subnet_1), Ref(self.public_subnet_2))
        self.export_value('private-subnets', "Private subnets.", Ref(self.private_subnet_1), Ref(self.private_subnet_2))
        self.export_value('db-subnets', "DB subnets.", Ref(self.db_subnet_1), Ref(self.db_subnet_2))


export = [Tier, VPC]

for c in export:
    template = c()
    with open('templates/drift-cfn-{}.json'.format(template.template_name), 'w') as f:
        f.write(template.t.to_json())

'''

an idea for a cli:

- the template code is generated into templates folder every time a cli is executed. it's there for reference and such.

- always create a change set which can be reviewed and/or executed. this is the only way to create or modify a stack.

- pretty print the change set in the same manner as the aws web represents it in "change set details".

- use parameters from driftconfig. allow override for testing purposes.

- tag the stacks properly. use the tags to find/enumerate drift stacks.


- to simplify cli, the only input is stack name and template name and if needed tier name
  for driftconfig if it cannot be inferred from the stack name.



  "UpdatePolicy": {


    "AutoScalingRollingUpdate": {


        "MaxBatchSize": Integer,


        "MinInstancesInService": Integer,


        "MinSuccessfulInstancesPercent": Integer


        "PauseTime": String,


        "SuspendProcesses": [ List of processes ],


        "WaitOnResourceSignals": Boolean


     }




"UpdatePolicy" : {
  "AutoScalingRollingUpdate" : {
  }
}

'''