# snapshotalyzer30000

Demo project to manage AWS EC2 instances

## About

This is a demo and uses boto3 to manage AWS EC2 instance shanpshots.

## Configuring

Shotty uses the configurations file created by the AWS cli e.g.

'aws configure --profile shotty'

## Running

'pipenv run python "shotty/shotty.py"'<command> <subcommand>
<--project=Project>

*command* is instances, volumes, or snapshots
*subcommand* depends of the command
*project* is optional
