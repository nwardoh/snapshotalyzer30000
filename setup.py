from setuptools import setup

setup(
    name='snapshotalyzer-3000',
    version='0.1',
    author="Dustin Wilson",
    author_email="dustin@dkamwilson.com",
    description="Snapshotalyzer 3000 is a tool to manage AWS EC2 instances, volumes, and snapshots",
    license="GPLv3+",
    packages=['shotty'],
    url="https://github.com/nwardoh/snapshotalyzer30000",
    install_requires=[
        'click',
        'boto3'
    ],
    entry_points='''
        [console_scripts]
        shotty=shotty.shotty:cli
    ''',
)
