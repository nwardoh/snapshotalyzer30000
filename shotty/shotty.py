import boto3
import botocore
import click
#import calendar and time to support --age parameter for snapshot creation
import calendar
import time


def start_session(profile='shotty',region='us-east-2'):
	session = boto3.Session(region_name=region,profile_name=profile)
	ec2 = session.resource('ec2')
	return ec2


def filter_instances(ec2, project, server_id = None):
	instances =[]
	if server_id:
		instances = ec2.instances.filter(InstanceIds=[server_id])
	elif project:
		filters = [{'Name':'tag:Project', 'Values':[project]}]
		instances = ec2.instances.filter(Filters=filters)
	else:
		instances = ec2.instances.all()
	return instances


def has_pending_snapshot(volume):
	snapshots = list(volume.snapshots.all())
	return snapshots and snapshots[0].state == 'pending'


@click.group()
@click.option('--profile', default='shotty',
			  help="Specify a profile other than 'shotty'")
@click.option('--region', default='us-east-2',
			  help="Specify a specific region e.g. us-east-1")
@click.pass_context
def cli(ctx,profile,region):
	"""establish session params"""
	ctx.ensure_object(dict)
	ctx.obj['PROFILE'] = profile
	ctx.obj['REGION'] = region


@cli.group('snapshots')
def snapshots():
	"""Commands for snapshots"""

@snapshots.command('list')
@click.option('--project', default=None,
	help="Only snapshots for project (tag Project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True,
			  help="List all snapshots for each volume, not just the most recent")
@click.pass_context
def list_snapshots(ctx, project, list_all):
	"List EC2 snapshots"
	ec2 = start_session(ctx.obj['PROFILE'],ctx.obj['REGION'])
	instances = filter_instances(ec2, project)
	for i in instances:
		for v in i.volumes.all():
			for s in v.snapshots.all():
				print(", ".join((
					s.id,
					v.id,
					i.id,
					s.state,
					s.progress,
					s.start_time.strftime("%c"),
					)))

				if s.state == 'completed' and not list_all: break
	return


@cli.group('volumes')
def volumes():
	"""Commands for volumes"""

@volumes.command('list')
@click.option('--id', 'server_id', default=None,
			  help="The instance ID")
@click.option('--project', default=None,
	help="Only volumes for project (tag Project:<name>)")
@click.pass_context
def list_volumes(ctx, project, server_id):
	"List EC2 volumes"
	ec2 = start_session(ctx.obj['PROFILE'],ctx.obj['REGION'])
	instances = filter_instances(ec2, project, server_id)
	for i in instances:
		for v in i.volumes.all():
			print(", ".join((
				v.id,
				i.id,
				v.state,
				str(v.size) + "GiB",
				v.encrypted and "Encrypted" or "Not Encrypted"
        		)))
	return


@cli.group('instances')
def instances():
	"""Commands for instances"""

@instances.command('snapshot',
	help="Create snapshots of all volumes")
@click.option('--id', 'server_id', default=None,
			  help="The instance ID")
@click.option('--age', default=None,
			  help="days. If most recent snapshot is less than age, no new snapshot will be created")
@click.option('--project', default=None,
	help="Only instances for project (tag Project:<name>)")
@click.option('--force', is_flag=True,
			  help="All instances")
@click.pass_context
def create_snapshots(ctx, project, force, server_id, age):
	"Create snapshots for EC2 instances"
	ec2 = start_session(ctx.obj['PROFILE'],ctx.obj['REGION'])
	instances = filter_instances(ec2, project, server_id)

	if server_id or project or force:
		for i in instances:

			aged_out=True
			instance_state = i.state['Name']
			instance_state_now = instance_state

			for v in i.volumes.all():

				if age:
					utc_start_time = None
					now = calendar.timegm(time.gmtime())
					time_delta = now - (86400 * int(age))
					# print(now,time_delta)
					for s in v.snapshots.all():
						gmt_start_time = s.start_time.strftime('%b %d, %Y @ %H:%M:%S UTC')
						utc_start_time = calendar.timegm(time.strptime(gmt_start_time, '%b %d, %Y @ %H:%M:%S UTC'))
						if s.state == 'completed': break
					if utc_start_time:
						if int(utc_start_time) > int(time_delta):
							aged_out = False

				if aged_out is True:
					if has_pending_snapshot(v):
						print(" Skipping {0}, snapshot already in progress".format(v.id))
						continue
					print("Creating snapshot of {0}...".format(v.id))
					try:
						if instance_state != "stopped" and instance_state_now != "stopped":
							print("Stopping {0}...".format(i.id))
							i.stop()
							i.wait_until_stopped()
							instance_state_now = "stopped"
						v.create_snapshot(Description="Created by Snapshotalyzer")
					except botocore.exceptions.ClientError as e:
						print(" Could not create snapshot {0}. ".format(v.id) + str(e))
						continue

			if instance_state != "stopped" and instance_state_now == "stopped":
				print("Starting {0}...".format(i.id))
				i.start()
				i.wait_until_running()

		print("Complete!")

	else:
		print("This command requires and option. Please use --help for more information")

	return


@instances.command('list')
@click.option('--project', default=None,
	help="Only instances for project (tag Project:<name>)")
@click.pass_context
def list_instances(ctx, project):
	"List EC2 instances"
	ec2 = start_session(ctx.obj['PROFILE'],ctx.obj['REGION'])
	instances = filter_instances(ec2, project)

	for i in instances:
	    tags = { t['Key']: t['Value'] for t in i.tags or []}
	    print(', '.join((
	    	i.id,
			str(i.public_ip_address),
			i.instance_type,
	    	i.placement['AvailabilityZone'],
	    	i.state['Name'],
			#i.public_dns_name,
			tags.get('Project', '<no project>')
			)))

	return

@instances.command('stop')
@click.option('--id', 'server_id', default=None,
			  help="The instance ID")
@click.option('--project', default=None,
	help="Only instances for project")
@click.option('--force', is_flag=True,
			  help="All instances")
@click.pass_context
def stop_instaces(ctx, project, force, server_id):
	"Stop EC2 instances"
	ec2 = start_session(ctx.obj['PROFILE'],ctx.obj['REGION'])
	instances = filter_instances(ec2, project, server_id)

	if server_id or project or force:
		for i in instances:
			print("Stopping {0}...".format(i.id))
			try:
				i.stop()
			except botocore.exceptions.ClientError as e:
				print(" Could not stop {0}. ".format(i.id) + str(e))
				continue

	else:
		print("This command requires and option. Please use --help for more information")

	return


@instances.command('start')
@click.option('--id', 'server_id', default=None,
			  help="The instance ID")
@click.option('--project', default=None,
	help="Only instances for project")
@click.option('--force', is_flag=True,
			  help="All instances")
@click.pass_context
def start_instaces(ctx, project, force, server_id):
	"Start EC2 instances"
	ec2 = start_session(ctx.obj['PROFILE'],ctx.obj['REGION'])
	instances = filter_instances(ec2, project, server_id)

	if server_id or project or force:
		for i in instances:
			print("Starting {0}...".format(i.id))
			try:
				i.start()
			except botocore.exceptions.ClientError as e:
				print(" Could not start {0}. ".format(i.id) + str(e))
				continue

	else:
		print("This command requires and option. Please use --help for more information")

	return


@instances.command('reboot')
@click.option('--id', 'server_id', default=None,
			  help="The instance ID")
@click.option('--project', default=None,
			  help="All instances for project")
@click.option('--force', is_flag=True,
			  help="All instances")
@click.pass_context
def reboot_instaces(ctx, project, server_id, force):
	"reboot EC2 instance"
	ec2 = start_session(ctx.obj['PROFILE'],ctx.obj['REGION'])
	instances = filter_instances(ec2, project)

	if server_id or project or force:
		for i in instances:
			print("Rebooting {0}...".format(i.id))
			try:
				i.reboot()
			except botocore.exceptions.ClientError as e:
				print(" Could not start {0}. ".format(i.id) + str(e))
				continue

	else:
		print("This command requires and option. Please use --help for more information")

	return



if __name__ == '__main__':
	cli(obj={})
