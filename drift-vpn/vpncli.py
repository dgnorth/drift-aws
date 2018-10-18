# -*- coding: utf-8 -*-
import os
import sys

import boto3
import click
from tabulate import tabulate

# pygments is optional for now
try:
    got_pygments = True
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import get_formatter_by_name
except ImportError:
    got_pygments = False

from driftconfig.util import get_default_drift_config


# Enable simple in-line color and styling of output
try:
    from colorama.ansi import Fore, Back, Style
    styles = {'f': Fore, 'b': Back, 's': Style}
    # Example: "{s.BRIGHT}Bold and {f.RED}red{f.RESET}{s.NORMAL}".format(**styles)
except ImportError:
    class EmptyString(object):
        def __getattr__(self, name):
            return ''

    styles = {'f': EmptyString(), 'b': EmptyString(), 's': EmptyString()}



CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class Globals(object):
    pass


pass_globals = click.make_pass_decorator(Globals, ensure=True)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--config-url', '-c', envvar='DRIFT_CONFIG_URL', metavar='',
    help="Url or name of Drift Configuration DB.")
@click.option('--tier-name', '-t',
    help="Tier name.")
@click.option('--verbose', '-v', is_flag=True,
    help='Enable verbose mode.')
@click.version_option('1.0')
@pass_globals
def cli(ctx, config_url, tier_name, verbose):
    """This command line tool helps you manage and maintain Drift
    Configuration databases.
    """
    ctx.obj = Globals()
    ctx.obj.config_url = config_url
    if config_url:
        os.environ['DRIFT_CONFIG_URL'] = config_url
    ctx.obj.tier_name = tier_name
    ctx.obj.verbose = verbose


def _get_config_and_tier(tier_name=None):
    """Returns 'ts' and 'tier' table if possible."""
    ts = get_default_drift_config()
    domain_name = ts.get_table('domain')['domain_name']
    tiers = ts.get_table('tiers').find()
    tier_name = tier_name or os.environ.get('DRIFT_TIER')

    if len(tiers) < 1:
        click.secho("No tier defined in config {}.".format(domain_name), fg='red', bold=True)
        sys.exit(1)

    if len(tiers) > 1 and tier_name is None:
        tier_names = [tier['tier_name'] for tier in tiers]
        click.secho("More than one tier found. Please specify which one to use: {}.".format(
            ', '.join(tier_names)), fg='red', bold=True)
        sys.exit(1)

    if tier_name:
        tier = ts.get_table('tiers').get({'tier_name': tier_name})
        if not tier:
            click.secho("Tier {} not found.".format(tier_name), fg='red', bold=True)
            sys.exit(1)
    else:
        tier = tiers[0]

    return ts, tier


def fold_tags(tags):
    """Fold boto3 resource tags array into a dictionary."""
    return {tag['Key']: tag['Value'] for tag in tags}


@cli.command()
@click.option('--show-all', '-a', is_flag=True)
@pass_globals
def info(ctx, show_all):
    """Show information on templates, stacks and tiers."""
    ts, tier = _get_config_and_tier(ctx.obj.tier_name)

    #hd = ['template_name', '']
    #print "template code", [t().template_name for t in templater.export]

    _list_stacks(tier, show_all)



def fit(text, max_len=35, strip=True, **ansi):
    """
    Make 'text' fit within 'max_len' characters, optionally 'strip' at newline and
    add 'ansi' colors a la click.
    """
    text = str(text)
    if strip:
        text = text.split('\n', 1)[0]
    if len(text) > max_len:
        text = text[:max_len - 1] + u'\u2026'  # Add a "..."
    if ansi:
        text = click.style(text, **ansi)
    return text

def _list_stacks(tier, show_all):
    # List out all template types

    # List out all stacks
    # The stacks have tag 'drift:template=template name'
    cfn_client = boto3.client('cloudformation', region_name=tier['aws']['region'])
    stacks = cfn_client.describe_stacks()

    hd = ["Stack Name", "Creation Time", "Stack Status", "Description", "Tier", "Template"]
    hd = [fit(h, bold=True) for h in hd]  # Make bold

    li = []
    for s in stacks['Stacks']:
        tags = fold_tags(s['Tags'])
        if not show_all:
            if 'drift:tier' not in tags or 'drift:template' not in tags:
                continue

        if s['StackStatus'].endswith('PROGRESS'):
            status_color = 'yellow'
        elif s['StackStatus'].endswith('FAILED'):
            status_color = 'red'
        else:
            status_color = 'green'

        row = [
            fit(s['StackName']),
            fit(str(s['CreationTime']).split('.')[0]),
            fit(s['StackStatus'], fg=status_color),
            fit(s.get('Description', '')),
            fit(tags.get('drift:tier')),
            fit(tags.get('drift:template')),
        ]

        li.append(row)

    click.secho("Stacks on {}:".format(tier['tier_name']), bold=True)
    if not li:
        click.secho("Note! No stack found!. Use --show-all to see all stacks.")
    else:
        click.secho(tabulate(li, headers=hd, tablefmt='fancy_grid'))



if 0:

    @click.command()
    @click.option('--verbose', '-v', is_flag=True, help='Enables verbose mode.')
    @click.option('--test', '-t', is_flag=True, help='Run a test suite and skip deployment.')
    @click.version_option('1.0')
    @click.pass_context
    @click.argument('config-urls', type=str, nargs=-1)
    def cli(ctx, config_urls, verbose, test):
        """Set up and manage VPN servers in Drift tiers.
        """
        ctx.obj = Globals()
        tiers = {}
        ts = get_default_drift_config()
        domain = ts.get_table('domain').get()
        for tier in ts.get_table('tiers').find():
            tier_name = tier['tier_name']

            if 'organization_name' not in tier:
                secho("Note: Tier {} does not define 'organization_name'.".format(tier_name))

            s3_origin_url = domain['origin']

            if tier_name in tiers:
                secho("Error: Duplicate tier names found. Tier '{}' is "
                    "defined in both of the following configs:".format(tier_name), fg='red')
                secho("Config A: {}".format(s3_origin_url))
                secho("Config B: {}".format(tiers[tier_name]['s3_origin_url']))
                secho("'{}' from config B will be skipped, but please fix!".format(tier_name))
                continue

            if 'aws' not in tier or 'region' not in tier['aws']:
                click.secho("Note: Tier {} does not define aws.region. Skipping.".format(tier_name))
                continue

            click.secho("Processing {}".format(tier_name), bold=True)

            # Figure out in which aws region this config is located
            aws_region = tier['aws']['region']
            parts = urlsplit(s3_origin_url)
            bucket_name = parts.hostname
            s3_bucket_region = boto3.resource("s3").meta.client.get_bucket_location(
                Bucket=bucket_name)["LocationConstraint"]
            # If 'get_bucket_location' returns None, it really means 'us-east-1'.
            s3_bucket_region = s3_bucket_region or 'us-east-1'

            echo("Connecting to AWS region {} to gather subnets and security group.".format(aws_region))
            ec2 = boto3.resource('ec2', aws_region)
            filters = [
                {'Name': 'tag:tier', 'Values':[ tier_name]},
                {'Name': 'tag:Name', 'Values': [tier_name+'-private-subnet-1', tier_name+'-private-subnet-2']}
                ]
            subnets=list(ec2.subnets.filter(Filters=filters))
            subnets = [subnet.id for subnet in subnets]

            filters = [
                {'Name': 'tag:tier', 'Values':[ tier_name]},
                {'Name': 'tag:Name', 'Values': [tier_name+'-private-sg']}
                ]

            security_groups=list(ec2.security_groups.filter(Filters=filters))
            security_groups = [sg.id for sg in security_groups]

            # Sum it up
            tier_args = {
                's3_origin_url': s3_origin_url,
                'tier_name': tier_name,
                'organization_name': tier.get('organization_name', domain['domain_name']),
                'aws_region': aws_region,
                's3_bucket_region': s3_bucket_region,
                'bucket_name': bucket_name,
                'subnets': subnets,
                'security_groups': security_groups,
                '_ts': ts,
            }
            tiers[tier_name] = tier_args

        env = Environment(loader=PackageLoader('driftconfig', package_path='templates'))
        template = env.get_template('zappa_settings.yml.jinja')
        zappa_settings_text = template.render(tiers=tiers.values())

        echo(pretty(zappa_settings_text, 'yaml'))
        filename = '{}.settings.yml'.format(domain['domain_name'])
        with open(filename, 'w') as f:
            f.write(zappa_settings_text)

        secho("\n{} generated.\n".format(click.style(filename, bold=True)))

        if test:
            _run_sanity_check(tiers)
            return

        for tier_name in tiers.keys():
            cmd = ['zappa', 'update', '-s', filename, tier_name]
            echo("Running command: {}".format(' '.join(cmd)))
            ret = subprocess.call(cmd)
            if ret == 255:
                cmd = ['zappa', 'deploy', '-s', filename, tier_name]
                secho("Running command: {}".format(' '.join(cmd)))
                ret = subprocess.call(cmd)


    def _run_sanity_check(tiers):
        for tier_name, tier in tiers.items():
            ts = tier['_ts']
            echo("Testing {} from {}".format(tier_name, ts))

            domain = ts.get_table('domain').get()
            domain['_dctest'] = datetime.utcnow().isoformat() + 'Z'
            result = push_to_origin(ts, force=False)
            if not result['pushed']:
                secho("Couldn't run test on {} from {}: {}".format(
                    tier_name, ts, result['reason']), fg='red', bold=True)
                continue

            b = get_redis_cache_backend(ts, tier_name)
            if not b:
                echo("Couldn't get cache backend on {} from {}.".format(tier_name, ts))
            else:
                try:
                    ts2 = b.load_table_store()
                except Exception as e:
                    if "Redis cache doesn't have" in str(e):
                        secho("{}. Possible timeout?".format(e), fg='red', bold=True)
                        continue

                    if "Timeout" in str(e):
                        secho("Cache check failed. Redis connection timeout.", fg='red', bold=True)
                        continue

                    raise

                domain2 = ts2.get_table('domain').get()
                if domain['_dctest'] != domain2.get('_dctest'):
                    echo("Cache check failed while comparing {} to {}.".format(domain['_dctest'], domain2.get('_dctest')))


if __name__ == '__main__':
    cli()
