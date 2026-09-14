#!/usr/bin/env python3
"""Configure release permissions for the existing local hello-world lab."""
import importlib.util
import json
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.parse import quote
from urllib.request import Request
from xml.sax.saxutils import escape

import configure as gitlab

ARTIFACTORY = Path(__file__).resolve().parents[1] / 'artifactory'
sys.path.insert(0, str(ARTIFACTORY))
import bootstrap as jfrog

spec = importlib.util.spec_from_file_location('docker_hub', ARTIFACTORY / 'configure-docker-hub.py')
hub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hub)
REPOSITORY = 'docker-releases-local'
PRIVATE = gitlab.PRIVATE


def variable(key, value, scope='release/*', file=False, masked=False):
    current = gitlab.api(f'/projects/{gitlab.PROJECT}/variables?per_page=100')
    exists = any(v['key'] == key and v['environment_scope'] == scope for v in current)
    endpoint = f'/projects/{gitlab.PROJECT}/variables'
    if exists:
        endpoint += '/' + key + '?filter[environment_scope]=' + quote(scope, safe='')
    gitlab.api(endpoint, 'PUT' if exists else 'POST', {
        'key': key, 'value': value, 'environment_scope': scope,
        'variable_type': 'file' if file else 'env_var', 'protected': True,
        'masked': masked, 'raw': True,
    })


def permission(session, name, users, targets):
    value = {'name': name, 'resources': {'artifact': {
        'actions': {'users': users},
        'targets': {r: {'include_patterns': ['**']} for r in targets},
    }}}
    current = jfrog.ui_api('/permissions/' + name, session)
    if current[0] == 404:
        jfrog.require_success(jfrog.ui_api('/permissions', session, 'POST', value), name)
    else:
        jfrog.require_success(current, name)
        artifact = json.loads(current[1])['resources']['artifact']
        actual_users = {name: set(rights) for name, rights in artifact['actions'].get('users', {}).items()}
        expected_users = {name: set(rights) for name, rights in users.items()}
        actual_targets = artifact['targets']
        expected_targets = set(targets)
        target_matches = set(actual_targets) == expected_targets and all(
            config.get('include_patterns') == ['**'] and not config.get('exclude_patterns')
            and not config.get('include_attributes') and not config.get('exclude_attributes')
            for config in actual_targets.values()
        )
        if actual_users != expected_users or artifact['actions'].get('groups') or not target_matches:
            raise SystemExit(f'Existing {name} differs; inspect it before changing permissions.')


def main():
    credentials = json.loads((jfrog.PRIVATE / 'credentials.json').read_text())
    session = jfrog.ui_session(credentials['admin'])
    listing = jfrog.api('/api/repositories', credentials['admin'])
    jfrog.require_success(listing, 'Repository listing')
    if REPOSITORY not in {r['key'] for r in json.loads(listing[1])}:
        hub.request(session, '/onboarding/createQuickRepos', 'POST', {'repositories': [{
            'repoName': REPOSITORY, 'packageType': 'Docker', 'repoType': 'LOCAL', 'xrayEnabled': False,
        }]})
    account_file = PRIVATE / 'release-registry.json'
    if not account_file.exists():
        gitlab.save(account_file, json.dumps({'username': 'local-release', 'password': secrets.token_urlsafe(32)}))
    account = json.loads(account_file.read_text())
    result = jfrog.ui_api('/users/' + account['username'], session)
    if result[0] == 404:
        jfrog.require_success(jfrog.ui_api('/users', session, 'POST', {
            **account, 'email': 'local-release@localhost.invalid', 'admin': False,
            'profileUpdatable': False, 'disableUiAccess': True, 'groups': [],
        }), 'Create release publisher')
    else:
        jfrog.require_success(result, 'Read release publisher')
        user = json.loads(result[1])
        if user.get('admin') or user.get('groups'):
            raise SystemExit('Release publisher has unexpected administrator/group privileges.')
    permission(session, 'local-release-publisher', {account['username']: ['READ', 'WRITE']}, [REPOSITORY])
    # OCI manifests need properties to retain their media type in Artifactory.
    permission(session, 'local-release-oci-metadata', {account['username']: ['ANNOTATE']}, [REPOSITORY])
    permission(session, 'local-release-base-images', {account['username']: ['READ']}, ['docker-local'])
    permission(session, 'local-release-reader', {credentials['reader']['username']: ['READ']}, [REPOSITORY])

    variable('ARTIFACTORY_USERNAME', account['username'])
    variable('ARTIFACTORY_PASSWORD_FILE', account['password'], file=True, masked=True)
    settings = '<settings><servers>' + ''.join(
        f'<server><id>{host}</id><username>{escape(account["username"])}</username>'
        f'<password>{escape(account["password"])}</password></server>'
        for host in ['localhost:8082', 'host.docker.internal:8082']
    ) + '</servers></settings>'
    variable('ARTIFACTORY_MAVEN_SETTINGS', settings, file=True)
    variable('RELEASE_OCI_REPOSITORY', REPOSITORY, scope='*')
    variable('RELEASE_REGISTRY_URL', 'http://host.docker.internal:8082', scope='*')
    variable('MAVEN_PUBLISH_SETTINGS', '''<settings><servers><server>
<id>gitlab-maven</id><username>gitlab-ci-token</username>
<password>${env.CI_JOB_TOKEN}</password>
</server></servers></settings>''', scope='*', file=True)

    key_file = PRIVATE / 'release-deploy-key'
    if not key_file.exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'local-release', '-f', str(key_file)], check=True)
    public = key_file.with_suffix('.pub').read_text().strip()
    keys = gitlab.api(f'/projects/{gitlab.PROJECT}/deploy_keys')
    key = next((k for k in keys if k['key'].split()[:2] == public.split()[:2]), None)
    if key is None:
        key = gitlab.api(f'/projects/{gitlab.PROJECT}/deploy_keys', 'POST', {
            'title': 'Release tags only (main remains push-protected)', 'key': public, 'can_push': True,
        })
    protected = gitlab.api(f'/projects/{gitlab.PROJECT}/protected_tags')
    existing = next((t for t in protected if t['name'] == 'v*'), None)
    if existing is None:
        gitlab.api(f'/projects/{gitlab.PROJECT}/protected_tags', 'POST', {
            'name': 'v*', 'create_access_level': 0, 'allowed_to_create': [{'deploy_key_id': key['id']}],
        })
    else:
        levels = existing['create_access_levels']
        if not any(x.get('deploy_key_id') == key['id'] for x in levels) or any(
                not x.get('deploy_key_id') and x.get('access_level', 0) != 0 for x in levels):
            raise SystemExit('Existing v* tag protection differs from the release-key-only policy.')
    known_hosts = (PRIVATE.parent.parent / 'gitlab-ce/secrets/known_hosts').read_text()
    known_hosts = known_hosts.replace('[localhost]:2424', '[host.docker.internal]:2424')
    variable('RELEASE_GIT_KEY', key_file.read_text(), scope='release/reserve', file=True)
    variable('RELEASE_GIT_KNOWN_HOSTS', known_hosts, scope='release/reserve', file=True)
    variable('RELEASE_GIT_URL', 'ssh://git@host.docker.internal:2424/root/hello-world.git', scope='release/reserve')

    for project in [gitlab.PROJECT, gitlab.project_id('ci-components')]:
        branch = gitlab.api(f'/projects/{project}/protected_branches/main')
        backup = PRIVATE / ('main-protection.before-releases.json' if project == gitlab.PROJECT
                            else f'project-{project}-main-protection.before-releases.json')
        if not backup.exists():
            gitlab.save(backup, json.dumps(branch))
        gitlab.api(f'/projects/{project}/protected_branches/main', 'PATCH', {
            'allow_force_push': False,
            'allowed_to_push': [{'id': a['id'], '_destroy': True} for a in branch['push_access_levels']] + [{'access_level': 0}],
        })
        gitlab.api(f'/projects/{project}', 'PUT', {
            'only_allow_merge_if_pipeline_succeeds': True,
            'only_allow_merge_if_all_discussions_are_resolved': True,
            # Typed release job inputs remain available; arbitrary variable overrides do not.
            'ci_pipeline_variables_minimum_override_role': 'no_one_allowed',
        })
    request = Request(gitlab.API_URL + '/api/graphql', method='POST',
        headers={'PRIVATE-TOKEN': gitlab.TOKEN, 'Content-Type': 'application/json'},
        data=json.dumps({'query': '''mutation {
          updateNamespacePackageSettings(input: {namespacePath: "root",
            mavenDuplicatesAllowed: false, mavenDuplicateExceptionRegex: ""}) { errors }
        }'''}).encode())
    with gitlab.HTTP.open(request, timeout=30) as response:
        result = json.load(response)
    if result.get('errors') or result['data']['updateNamespacePackageSettings']['errors']:
        raise SystemExit('Could not disable duplicate Maven publication in the local namespace.')
    print('Local release repository, publisher, scoped credentials and Git protections configured.')
    print('Release publisher: Read + Deploy + Annotate; main: no direct pushes; v*: release deploy key only.')


if __name__ == '__main__':
    main()
