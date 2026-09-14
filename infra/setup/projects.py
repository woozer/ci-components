"""Initialize empty local GitLab projects without replacing existing history."""
import json
from pathlib import Path
import shlex
import shutil
import tempfile
from urllib.parse import quote

from common import INFRA, PROJECT_RECORDS, ROOT, STATE, announce, compose, gitlab, load_json, run, save, save_json


def configure_access():
    private = INFRA / 'gitlab-ce/secrets'
    token = private / 'provisioning-token'
    if not token.exists() or not gitlab('/user', allowed=(401,)):
        compose('gitlab-ce', 'cp', INFRA / 'gitlab-ce/provision-token.rb', 'gitlab:/tmp/provision-token.rb')
        compose('gitlab-ce', 'exec', '-T', 'gitlab', 'gitlab-rails', 'runner', '/tmp/provision-token.rb')
        save(token, compose('gitlab-ce', 'exec', '-T', 'gitlab', 'cat', '/tmp/hello-world-provisioning-token', capture=True))
        compose('gitlab-ce', 'exec', '-T', 'gitlab', 'rm', '/tmp/hello-world-provisioning-token')
    password = private / 'initial_root_password'
    if not password.exists():
        value = compose('gitlab-ce', 'exec', '-T', 'gitlab', 'sh', '-c',
                        'test ! -f /etc/gitlab/initial_root_password || cat /etc/gitlab/initial_root_password', capture=True)
        if value:
            save(password, value)
    key = private / 'setup-key'
    if not key.exists():
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'local-demo-setup', '-f', key])
    public = key.with_suffix('.pub').read_text().strip()
    existing = gitlab('/user/keys?per_page=100')
    if not any(item['key'].split()[:2] == public.split()[:2] for item in existing):
        gitlab('/user/keys', 'POST', {'title': 'Local demo setup', 'key': public})
    host_key = compose('gitlab-ce', 'exec', '-T', 'gitlab', 'cat', '/etc/gitlab/ssh_host_ed25519_key.pub', capture=True).strip()
    # Trust the key read from our own container, not an unauthenticated network scan.
    save(private / 'known_hosts', ''.join(f'[{host}]:2424 {host_key}\n' for host in ('localhost', 'host.docker.internal')))
    # Refresh local-demo access after a reset; external remotes keep their own authentication.
    remotes = run(['git', 'remote', '-v'], capture=True).splitlines()
    local_origins = ('ssh://git@localhost:2424/root/ci-components.git',
                     'ssh://git@host.docker.internal:2424/root/ci-components.git')
    if any(line.startswith('origin\t' + url + ' ') for line in remotes for url in local_origins):
        run(['git', 'config', 'core.sshCommand', ssh_command(key)])
    return key


def ssh_command(key):
    return ' '.join(shlex.quote(str(arg)) for arg in ['ssh', '-i', key, '-o', 'IdentitiesOnly=yes',
        '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={INFRA / "gitlab-ce/secrets/known_hosts"}'])


def ensure_projects():
    for name, record in PROJECT_RECORDS.items():
        project = gitlab('/projects/' + quote('root/' + name, safe=''), allowed=(404,))
        if project is None:
            project = gitlab('/projects', 'POST', {'name': name, 'path': name, 'visibility': 'private',
                'initialize_with_readme': False, 'default_branch': 'main'})
        previous = load_json(record)
        if previous and previous['id'] != project['id']:
            raise RuntimeError(f'{name}: local state belongs to another GitLab; restore it or use a complete demo reset.')
        save_json(record, {'id': project['id'], 'path_with_namespace': project['path_with_namespace']})


def seed_projects(key):
    env = {'GIT_SSH_COMMAND': ssh_command(key)}
    manifest = load_json(INFRA / 'seed/manifest.json')
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, record in PROJECT_RECORDS.items():
        project = gitlab(f'/projects/{load_json(record)["id"]}')
        if not project['empty_repo']:
            announce(f'Keeping existing repository root/{name}.')
            continue
        if run(['git', 'status', '--porcelain'], capture=True).strip():
            raise RuntimeError('Commit the source changes before seeding an empty GitLab repository.')
        with tempfile.TemporaryDirectory(prefix='seed-', dir=STATE) as directory:
            target = Path(directory)
            run(['git', 'init', '-q', '--initial-branch=main', target])
            run(['git', 'config', 'user.name', 'Local demo setup'], cwd=target)
            run(['git', 'config', 'user.email', 'demo@localhost.invalid'], cwd=target)
            if name == 'ci-components':
                # Fetch local objects only. Published versions keep their original commits.
                refs = ['HEAD:refs/heads/seed-source'] + [f'refs/tags/{version}:refs/tags/{version}'
                                                        for version in manifest['component_versions']]
                run(['git', 'fetch', '--quiet', ROOT, *refs], cwd=target)
                run(['git', 'checkout', '-q', '-B', 'main', 'seed-source'], cwd=target)
            else:
                # git ls-files respects the source checkout's ignore rules; no caches or keys.
                files = run(['git', 'ls-files', '-z', '--', 'java'], capture=True).split('\0')
                if not any(files):
                    raise RuntimeError('Commit the java/ source before installing a fresh demo.')
                for relative in filter(None, files):
                    source = ROOT / relative
                    destination = target / source.relative_to(ROOT / 'java')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                if name == 'ci-samples':
                    shutil.copytree(INFRA / 'seed/ci-samples', target, dirs_exist_ok=True)
                run(['git', 'add', '.'], cwd=target)
                run(['git', 'commit', '-q', '-m', 'Initialize local demo application [skip ci]'], cwd=target)
            remote = f'ssh://git@host.docker.internal:2424/root/{name}.git'
            run(['git', 'push', '-o', 'ci.skip', remote, 'main'], cwd=target, env=env)
            if name == 'ci-components':
                run(['git', 'push', '-o', 'ci.skip', remote, *[f'refs/tags/{v}' for v in manifest['component_versions']]], cwd=target, env=env)
            announce(f'Initialized root/{name}.')


def protect_projects():
    for record in PROJECT_RECORDS.values():
        project = load_json(record)['id']
        path = f'/projects/{project}/protected_branches/main'
        branch = gitlab(path, allowed=(404,))
        if branch:
            gitlab(path, 'PATCH', {'allow_force_push': False, 'allowed_to_push':
                [{'id': access['id'], '_destroy': True} for access in branch['push_access_levels']] + [{'access_level': 0}]})
        else:
            gitlab(f'/projects/{project}/protected_branches', 'POST', {
                'name': 'main', 'push_access_level': 0, 'merge_access_level': 40, 'allow_force_push': False})
        gitlab(f'/projects/{project}', 'PUT', {'only_allow_merge_if_pipeline_succeeds': True,
            'only_allow_merge_if_all_discussions_are_resolved': True,
            'ci_pipeline_variables_minimum_override_role': 'no_one_allowed'})
    project = load_json(PROJECT_RECORDS['ci-components'])['id']
    if not any(tag['name'] == '*' for tag in gitlab(f'/projects/{project}/protected_tags')):
        gitlab(f'/projects/{project}/protected_tags', 'POST', {'name': '*', 'create_access_level': 40})
