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
import arrow

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
        
        self._report = {}
        self._branches_deployed = set()

        for repo, repo_info in config['repositories'].items():
            
            os.makedirs(repo_info['base_project_path'], exist_ok=True)
            if not self._is_repo(repo_info['base_project_path']):
                self._clone(repo_info['repo_url'], 'master', repo_info['base_project_path'])
                if 'scripts' in  repo_info:
                    self._execute_scripts(repo_info['base_project_path'], repo_info['scripts'])
            self._fetch_all(repo_info['base_project_path'])

            remote_branches = self._get_remote_branches(repo_info['base_project_path'])
            self._setup(self._normalize(remote_branches), repo_info['branches'])

    def sync(self):
        for repo, repo_info in config['repositories'].items():

            self._report.setdefault(repo, {})
            for branch, branch_info in repo_info['branches'].items():

                for remote_branch_info in branch_info['remote_branches']:
                
                    holder_path = Path(branch_info['path']).name
                    branch_path = remote_branch_info['path']

                    if holder_path == branch_path:
                        branch_path = ''

                    full_path = (branch_info['path'] + '/' + branch_path).rstrip('/')
                    self._branches_deployed.add(full_path)

                    self._report[repo][full_path] = 'Sync with remote branch "{}".'.format(remote_branch_info['name'])

                    os.makedirs(full_path, exist_ok=True)
                    
                    if not self._is_repo(full_path):
                        self._clone(repo_info['repo_url'], remote_branch_info['name'], full_path)
                    
                    self._pull(full_path)
                    if 'scripts' in branch_info:
                        self._execute_scripts(full_path, branch_info['scripts'])
                    
                self._clean_deleted_branches(repo, branch_info['path'])

        self._print_report()

    def _print_report(self):
        for repo, branches in self._report.items():
            print('[' + str(arrow.now('America/Sao_Paulo')) + ']', repo.upper(), ':')
            for branch_path, branch_msg in branches.items():
                print('   ', branch_path, '->', branch_msg)

    def _get_remote_branches(self, local_path):
        return io.BytesIO(
            subprocess.check_output(
                'git branch -a', cwd=local_path, shell=True
            )
        )

    def _execute_scripts(self, local_path, scripts):
        for script in scripts:
            subprocess.run(
                script, cwd=local_path, shell=True, check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

    def _fetch_all(self, local_path):
        subprocess.run(
            'git fetch --all', 
            cwd=local_path, shell=True, check=False, 
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _pull(self, local_path):
        subprocess.run(
            'git pull', cwd=local_path, shell=True, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _clone(self, url, branch, local_path):
        subprocess.run(
            'git clone {} -b {} .'.format(url, branch),
            cwd=local_path, shell=True, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _is_repo(self, local_path):
        return Path(local_path + '/.git').exists()

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

    def _clean_deleted_branches(self, repo_name, local_path):
        if not self._is_repo(local_path):
            for f in Path(local_path).glob('*'):
                if str(f) not in self._branches_deployed:
                    self._report[repo_name][str(f)] = 'REMOVED! This branch is no more available on remote repository.'
                    shutil.rmtree(f)