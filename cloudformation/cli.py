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

import templater


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
        click.secho(tabulate(li, headers=hd, tablefmt='github'))


@cli.command()
@click.argument('stack-name')
@pass_globals
def update(ctx, stack_name):
    """Create or update a stack.

    ia m temporoary
    """
    print ("stack name: {}".format(stack_name))



@cli.command()
@click.argument('table-name')
@click.option('--tier-name', '-t', type=str, default=None)
def edit(table_name, tier_name):
    """Edit a config table.\n
    TABLE_NAME is one of: domain, organizations, tiers, deployable-names, deployables,
    products, tenant-names, tenants.
    """
    click.secho("some ediot ctable name command " + table_name)
    click.secho("tier name= {}".format(tier_name))


PRETTY_FORMATTER = 'console256'
PRETTY_STYLE = 'tango'


def pretty(ob, lexer=None):
    """
    Return a pretty console text representation of 'ob'.
    If 'ob' is something else than plain text, specify it in 'lexer'.

    If 'ob' is not string, Json lexer is assumed.

    Command line switches can be used to control highlighting and style.
    """
    if lexer is None:
        if isinstance(ob, basestring):
            lexer = 'text'
        else:
            lexer = 'json'

    if lexer == 'json':
        ob = json.dumps(ob, indent=4, sort_keys=True)

    if got_pygments:
        lexerob = get_lexer_by_name(lexer)
        formatter = get_formatter_by_name(PRETTY_FORMATTER, style=PRETTY_STYLE)
        #from pygments.filters import *
        #lexerob.add_filter(VisibleWhitespaceFilter())
        ret = highlight(ob, lexerob, formatter)
    else:
        ret = ob

    return ret.rstrip()


if __name__ == '__main__':
    cli()
