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
        t.add_version("2010-09-09")
        t.add_description(description)

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
        export_name = _(self.stack_group, "-{}".format(name))
        if index is None:
            value = ImportValue(export_name)
        else:
            value = Select(str(index), Split(',', ImportValue(export_name))),

        return value

    def get_tier_name(self):
        """Returns the tier name by looking up the exported value from STACKGROUP-tier-name."""
        return self.import_value('tier-name')

    def get_tags(self, resource_name, **kwargs):
        """
        Returns Tags instance with tags from 'kwargs' plus the following default tags:
        Name=<TIERNAME>-<resource_name>
        tier=<TIERNAME>
        """
        def __init__(self, resource_name, **kwargs):
            kwargs["Name"] = _(self.get_tier_name(), "-{}".format(resource_name))
            kwargs["tier"] = self.get_tier_name()
            return TierTags(**kwargs)


t = Template()
t.add_version("2010-09-09")
t.add_description("""\
ASG Test
""")

tier_name = t.add_parameter(Parameter(
    "TierName",
    Type="String",
    Description="Tier name.",
))

subnet_2 = t.add_parameter(Parameter(
    "subnet2",
    Type="String",
    Description="Second private VPC subnet ID for the api app.",
))

subnet_1 = t.add_parameter(Parameter(
    "subnet1",
    Type="String",
    Description="First private VPC subnet ID for the api app.",
))

t.add_parameter

AutoscalingGroup = t.add_resource(AutoScalingGroup(
    "AutoscalingGroup",
    DesiredCapacity=1,
    Tags=[
        Tag("Name", "DEVNORTH-drift-base-auto", True),
        Tag("tier", "DEVNORTH", True),
        Tag("service-name", "drift-base", True),
        Tag("api-target", "drift-base", True),
        Tag("api-status", "online", True),
        Tag("api-port", "10080", True),
    ],
    LaunchConfigurationName="DEVNORTH-drift-base-launchconfig-2018-03-23 16.06.41.285897-",
    MinSize=1,
    MaxSize=2,
    VPCZoneIdentifier=[Ref(subnet_1), Ref(subnet_2)],
    #LoadBalancerNames=[Ref(LoadBalancer)],
    #AvailabilityZones=[Ref(VPCAvailabilityZone1), Ref(VPCAvailabilityZone2)],
    HealthCheckType="EC2",
    UpdatePolicy=UpdatePolicy(
        AutoScalingReplacingUpdate=AutoScalingReplacingUpdate(
            # WillReplace=True,
        ),
        AutoScalingRollingUpdate=AutoScalingRollingUpdate(
            # PauseTime='PT5M',
            MinInstancesInService="1",
            # MaxBatchSize='1',
            # WaitOnResourceSignals=True
        )
    ),
    LifecycleHookSpecificationList=[
        LifecycleHookSpecification(
            LifecycleHookName='Wait-2-minutes-on-termination',
            LifecycleTransition='autoscaling:EC2_INSTANCE_TERMINATING',
            HeartbeatTimeout='120',
            DefaultResult='CONTINUE',
        ),
    ],
))


t.add_output([
    Output(
        "AutoscalingGroup",
        Description="The ID of the AutoscalingGroup.",
        Value=Ref(AutoscalingGroup),
        Export=Export(Sub("${AWS::StackName}-AutoscalingGroup")),
    ),
    Output(
        "AutoscalingGroupx2",
        Description="The ID of the AutoscalingGroup 2",
        Value=Join('', [Ref(AutoscalingGroup), Ref(AutoscalingGroup)]),
        Export=Export(Sub("${AWS::StackName}-AutoscalingGroupx2")),
    ),
    Output(
        "TestingStuff",
        Description="The ID of the AutoscalingGroup exported from myself",
        Value=Select("0", Split(',', ImportValue(Sub("${AWS::StackName}-some-name")))),
    ),
    #export_value('some-name', "Describing some name value", Ref(AutoscalingGroup), Ref(AutoscalingGroup)),
])


from troposphere.certificatemanager import Certificate, DomainValidationOption


class AsgTest(DriftTemplate):

    def __init__(self):
        DriftTemplate.__init__(self, 'asg', "Some test template, that's all.")
        self.export_value('dns', "Root domain.", 'dg-api.com')


        self.t.add_resource(
            Certificate(
                'mycert',
                DomainName='dg-api.com',
                DomainValidationOptions=[
                    DomainValidationOption(
                        DomainName='dg-api.com',
                        ValidationDomain='dg-api.com',
                    ),
                ],
                Tags=[
                    {
                        'Key': 'tier',
                        'Value': 'DEVNORTH'
                    },
                ],
            )
        )

        self.export_value('rootcert', "Certificate for root domain.", Ref('mycert'))

print AsgTest().t.to_json()
#print t.to_json()
