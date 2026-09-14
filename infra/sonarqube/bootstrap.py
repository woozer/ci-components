#!/usr/bin/env python3
"""Configure this lab's SonarQube and a project-scoped GitLab analysis token."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / 'secrets'
HTTP = build_opener(ProxyHandler({}))
PROJECT = 'hello-world'
TOKEN_NAME = 'gitlab-analysis-token'


def save(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
        stream.write(value)
    path.chmod(0o600)


def credentials():
    path = PRIVATE / 'credentials.json'
    if not path.exists():
        save(path, json.dumps({'admin': secrets.token_urlsafe(24),
                               'database': secrets.token_urlsafe(24),
                               'ci': secrets.token_urlsafe(24)}, indent=2))
    return json.loads(path.read_text())


def api(path, method='GET', values=None, password=None, allowed=(), login='admin'):
    auth = base64.b64encode((login + ':' + (password or credentials()['admin'])).encode()).decode()
    url = 'http://' + os.environ.get('DEMO_ADMIN_HOST', '127.0.0.1') + ':9000' + path
    data = None
    if values:
        if method == 'GET':
            url += '?' + urlencode(values)
        else:
            data = urlencode(values).encode()
    request = Request(url, data=data, method=method, headers={'Authorization': 'Basic ' + auth})
    try:
        with HTTP.open(request, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except HTTPError as error:
        if error.code in allowed:
            return {'http_status': error.code}
        raise SystemExit(f'SonarQube {method} {path}: HTTP {error.code}') from None


def prepare():
    refs = {}
    for key, name in [('SONARQUBE_IMAGE', 'sonarqube:26.9.0.129388-community'),
                      ('POSTGRES_IMAGE', 'postgres:17')]:
        image = 'localhost:8082/docker/' + name
        info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', image], text=True))[0]
        refs[key] = next(value for value in info['RepoDigests'] if value.startswith('localhost:8082/'))
    save(ROOT / '.env', ''.join(f'{key}={value}\n' for key, value in refs.items())
         + 'SONAR_DB_PASSWORD=' + credentials()['database'] + '\n')
    print('Pinned local Artifactory images and generated private database credentials.')


def configure():
    secret = credentials()
    if not api('/api/authentication/validate').get('valid'):
        api('/api/users/change_password', 'POST', {'login': 'admin', 'previousPassword': 'admin',
                                                  'password': secret['admin']}, password='admin')
    if not api('/api/components/show', values={'component': PROJECT}, allowed=(404,)).get('component'):
        api('/api/projects/create', 'POST', {'project': PROJECT, 'name': 'Hello World',
                                            'mainBranch': 'main', 'visibility': 'private'})
    users = api('/api/users/search', values={'q': 'gitlab-ci'})['users']
    if not any(user['login'] == 'gitlab-ci' for user in users):
        api('/api/users/create', 'POST', {'login': 'gitlab-ci', 'name': 'Local GitLab analysis',
                                         'password': secret['ci'], 'local': 'true'})
    for permission in ('scan', 'user'):
        api('/api/permissions/add_user', 'POST', {'login': 'gitlab-ci', 'projectKey': PROJECT,
                                                'permission': permission})
    token_path = PRIVATE / TOKEN_NAME
    if not token_path.exists():
        token = api('/api/user_tokens/generate', 'POST', {'name': PROJECT + '-ci',
                    'type': 'PROJECT_ANALYSIS_TOKEN', 'projectKey': PROJECT},
                    login='gitlab-ci', password=secret['ci'])['token']
        save(token_path, token + '\n')
    api('/api/settings/set', 'POST', {'key': 'sonar.core.serverBaseURL', 'value': 'http://localhost:9000'})
    sys.path.insert(0, str(ROOT.parent / 'gitlab-runner'))
    import configure as gitlab
    project = gitlab.project_id(PROJECT)
    gitlab.variable('SONAR_HOST_URL', 'http://sonarqube:9000', project=project)
    gitlab.variable('SONAR_PROJECT_KEY', PROJECT, project=project)
    gitlab.variable('SONAR_TOKEN', token_path.read_text().strip(), project=project, protected=True, masked=True)
    print('SonarQube project configured; protected project analysis token stored in local GitLab.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'configure', 'status'])
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'configure':
        configure()
    else:
        print(json.dumps(api('/api/system/status')))
