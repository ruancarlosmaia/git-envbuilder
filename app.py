#### LIBRARIES IMPORT
import os
import logging
import click
import yaml
import shutil
import subprocess
import io
import re

from pathlib import Path
from tqdm import tqdm

#### BASIC APP CONFIGURATIONS
APP_VERSION = '1.0.0'
BASE_PATH = os.path.abspath(os.path.dirname(__file__))

with open(BASE_PATH + '/config.yml') as r:
    config = yaml.safe_load(r.read())

#### DEFAULT CLI GROUP
@click.group()
def cli(): pass

@cli.command('sync')
def sync():

    for repo, repo_info in config['repositories'].items():
        
        subprocess.run(
            'cd {} && git fetch --all'.format(repo_info['project']), 
            shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        remote_branches = io.BytesIO(
            subprocess.check_output(
                'cd {} && git branch -a'.format(repo_info['project']), shell=True
            )
        )

        for remote_branch in _normalize(remote_branches):

            if _match(remote_branch, repo_info['branches']):
                print(remote_branch)


def _match(remote_branch_name, branch_patterns):
    for branch, info in branch_patterns.items():
        if re.match(info['pattern'], remote_branch_name):
            return True
    return False


def _normalize(remote_branches):
    
    branches = set()
    clear_regex = re.compile('(\*|\s|\n|remotes/origin/)')

    for remote_branch in remote_branches:
        cleaned_remote_branch_name = clear_regex.sub('', remote_branch.decode())
        branches.add(cleaned_remote_branch_name)
    
    return branches