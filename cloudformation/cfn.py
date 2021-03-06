#!/usr/bin/env python

import argparse
import sys
import time
from ast import literal_eval

try:
    import boto
    import boto.cloudformation
except ImportError:
    print("boto 2.8.0+ is required")
    sys.exit(1)

def upload_template_to_s3(conn, region, bucket_name, key_name, template):
    cloudformation_bucket = conn.lookup(bucket_name)
    if not cloudformation_bucket:
        cloudformation_bucket = conn.create_bucket(bucket_name, location=region)
    key = cloudformation_bucket.new_key(key_name)
    key.set_contents_from_string(template)
    cfn_template_url = "https://s3.amazonaws.com/%s/%s" % (
        bucket_name, key_name)
    return cfn_template_url


def create_stack(conn, stackname, template=None, url=None, params=None, update=False):    
    if not update:
        print ("Creating stack '{}'".format(stackname))
        apply_to_stack = conn.create_stack
    else:
        print ("Updating stack '{}'".format(stackname))
        apply_to_stack = conn.update_stack  

    try:        
        if url:
            stack_id = apply_to_stack(
                stack_name=stackname, template_url=url, parameters=params)
        else:
            stack_id = apply_to_stack(
                stack_name=stackname, template_body=template, parameters=params)
    except boto.exception.BotoServerError as e:
        body = literal_eval(e.body)
        if not update and body['Error']['Code'] == "AlreadyExistsException":
            print("Stack '{}' already exists.".format(stackname))
            return create_stack(conn, stackname, template, url, params, update=True)

        print ("Error: {} - {}".format(body['Error']['Code'], body['Error']['Message']))
        print("Exiting...")
        sys.exit(1)
    print("Stack creation/update in progress:  %s - %s" % (stackname, stack_id))


def build_s3_name(stack_name):
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    name = stack_name
    if stack_name.endswith('.json'):
        name = stack_name[:-5]
    return '%s-%s.json' % (name, timestamp)


def describe_resources(conn, stackname):
    if stackname is not None:
        print(conn.describe_stack_resources(stackname))
    else:
        stacks = conn.describe_stacks()
        for stack in stacks:
            print("Resources for stack {0}:".format(stack.stack_name))
            print(conn.describe_stack_resources(stack.stack_name))


def get_events(conn, stackname):
    """Get the events in batches and return in chronological order"""
    next = None
    event_list = []
    while 1:
        events = conn.describe_stack_events(stackname, next)
        event_list.append(events)
        if events.next_token is None:
            break
        next = events.next_token
        time.sleep(1)
    return reversed(sum(event_list, []))


def tail(conn, stack_name):
    """Show and then tail the event log"""
    def tail_print(e):
        print("%s %s %s" % (e.resource_status, e.resource_type, e.event_id))

    # First dump the full list of events in chronological order and keep
    # track of the events we've seen already
    seen = set()
    initial_events = get_events(conn, stack_name)
    for e in initial_events:
        tail_print(e)
        seen.add(e.event_id)

    # Now keep looping through and dump the new events
    while 1:
        events = get_events(conn, stack_name)
        for e in events:
            if e.event_id not in seen:
                tail_print(e)
            seen.add(e.event_id)

            is_stack_event = e.resource_type == "AWS::CloudFormation::Stack"
            creating_or_updating = e.resource_status in [
                "CREATE_IN_PROGRESS", "UPDATE_IN_PROGRESS"
            ]

            if is_stack_event and not creating_or_updating:
                return

        time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--create", help="Create stack using template")
    parser.add_argument("-b", "--bucket", dest="s3bucket",
                        help="Upload template to S3 bucket")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Turn on boto debug logging")
    parser.add_argument("-n", "--name", dest="s3name",
                        help="Template name in S3 bucket")
    parser.add_argument("-p", "--parameter", dest="params", action='append',
                        help="stack parameters in key=value form")
    parser.add_argument("-r", "--region", default="us-east-1",
                        help="Region (default %(default)s)")
    parser.add_argument("-R", "--resources", action='store_true',
                        help="describe stack resources, list resources for "
                             "all stacks if no stack is specified")
    parser.add_argument("-t", "--tail", action='store_true',
                        help="tail event log")
    parser.add_argument("stack", nargs='?')
    values = parser.parse_args()

    if values.params:
        values.params = [x.split('=') for x in values.params]
    else:
        values.params = []

    if values.debug:
        import logging
        logging.basicConfig(filename="boto.log", level=logging.DEBUG)

    conn = boto.cloudformation.connect_to_region(values.region)

    if values.create:
        # Read in the template file
        template = open(values.create).read()

        # If needed, build an S3 name (key)
        if values.s3bucket and not values.s3name:
            values.s3name = build_s3_name(values.create)

        if values.s3bucket:
            # Upload to S3 and create the stack
            s3conn = boto.s3.connect_to_region(values.region)
            url = upload_template_to_s3(
                s3conn, values.region, values.s3bucket, values.s3name, template)
            create_stack(conn, values.stack, None, url, values.params)
        else:
            # Upload file as part of the stack creation
            create_stack(conn, values.stack, template, None, values.params)

    if values.resources:
        describe_resources(conn, values.stack)

    if values.tail:
        tail(conn, values.stack)
        print("Cloudformation execution finished.")
