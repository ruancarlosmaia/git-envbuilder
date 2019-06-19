#### LIBRARIES IMPORT
import os
import logging
import click
import yaml
import shutil
import subprocess
import io
import re
import pprint

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
    gitEnvBuilder = GitEnvBuilder(config)
    gitEnvBuilder.sync()

class GitEnvBuilder:

    def __init__(self, config):
        
        self._branches_deployed = set()

        for repo, repo_info in config['repositories'].items():
            
            subprocess.run(
                'git fetch --all', 
                cwd=repo_info['install_project_path'], shell=True, check=False, 
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            remote_branches = io.BytesIO(
                subprocess.check_output(
                    'git branch -a', 
                    cwd=repo_info['install_project_path'], shell=True
                )
            )

            self._setup(self._normalize(remote_branches), repo_info['branches'])

    def sync(self):
        
        print('REMOTE BRANCHES:')
        pprint.pprint(self._branches_deployed)
        print('')

        for repo, repo_info in config['repositories'].items():
            for branch, branch_info in repo_info['branches'].items():
                
                print('BRANCH: ' + branch)
                pprint.pprint(branch_info)

                for remote_branch_info in branch_info['remote_branches']:
                
                    holder_path = Path(branch_info['path']).name
                    branch_path = remote_branch_info['path']

                    if holder_path == branch_path:
                        branch_path = ''

                    full_path = branch_info['path'] + '/' + branch_path
                    self._branches_deployed.add(full_path.rstrip('/'))
                    print(full_path.rstrip('/'))

                    os.makedirs(full_path.rstrip('/'), exist_ok=True)
                    
                    print('REMOTE BRANCH NAME:', remote_branch_info['name'])
                    # local_paths = set(Path(branch_info['path']).glob('*'))
                    # for f in Path(branch_info['path']).glob('*'):
                    #     print('local path: ', f.name)
                    #     print('branch name: ', f.parent)
                    #     print(f.name in self._branches_deployed)
                    # print(Path(branch_info['path']).glob('*'))
                print('')
        
                self._clean_deleted_branches(branch_info['path'])


    def _clean_deleted_branches(self, local_path):
        print(self._branches_deployed)
        for f in Path(local_path).glob('*'):
            print(f, '==>', str(f) in self._branches_deployed)

            if str(f) not in self._branches_deployed:
                # FOLDER TO BE DELETED
                shutil.rmtree(f)

        print('')

    def _normalize(self, remote_branches):
        
        branches = set()
        clear_regex = re.compile('(\*|\s|\n|remotes/origin/)')

        for remote_branch in remote_branches:
            cleaned_remote_branch_name = clear_regex.sub('', remote_branch.decode())
            branches.add(cleaned_remote_branch_name)

        return branches

    def _setup(self, remote_branches, branches_config):
        
        for remote_branch in remote_branches:
            
            for branch, info in branches_config.items():
                
                matched_value = re.match(info['pattern'], remote_branch)

                if matched_value is not None:
                    
                    path = matched_value.group(0)
                    if len(matched_value.groups()) > 0:
                        path = matched_value.group(1)

                    info.setdefault('remote_branches', [])
                    info['remote_branches'].append({
                        'path': path,
                        'name': remote_branch
                    })