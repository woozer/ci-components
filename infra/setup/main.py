"""Install the local demo from source; service orchestration stays in Compose."""
import argparse
import json
import os
import sys
import time

from common import (HTTP, INFRA, PROJECT_RECORDS, ROOT, STATE, announce, architecture, compose,
                    docker_architecture, ensure_env_password, gitlab, kubectl, load_json,
                    local_url, project_id, request_json, run, save_json, wait_ready)

STACKS = ('gitlab-ce', 'artifactory', 'sonarqube', 'gitlab-runner')


def check():
    from projects import check_sources
    check_sources()
    info = json.loads(run(['docker', 'info', '--format', '{{json .}}'], capture=True))
    arch = architecture(info['Architecture'])
    if info['OSType'] != 'linux':
        raise RuntimeError('The demo requires Docker Linux containers.')
    registries = info.get('RegistryConfig', {}).get('IndexConfigs', {})
    for registry in ('localhost:8082', 'host.docker.internal:8082'):
        if registries.get(registry, {}).get('Secure', True):
            raise RuntimeError(f'Add {registry} to insecure-registries in Docker Desktop Settings > Docker Engine, then Apply & restart.')
    nodes = json.loads(kubectl('get', 'nodes', '-o', 'json'))['items']
    if not nodes or any(not any(c['type'] == 'Ready' and c['status'] == 'True'
                              for c in node['status']['conditions']) for node in nodes):
        raise RuntimeError('Wait until Docker Desktop Kubernetes is ready.')
    if any(architecture(node['status']['nodeInfo']['architecture']) != arch for node in nodes):
        raise RuntimeError('Docker and Kubernetes architectures differ; use matching native nodes.')
    containerd = run(['docker', 'exec', 'desktop-control-plane', 'cat', '/etc/containerd/config.toml'], capture=True)
    if 'config_path = "/etc/containerd/certs.d"' not in containerd:
        raise RuntimeError('The Docker Desktop node does not enable the expected containerd registry configuration directory.')
    manifest = load_json(INFRA / 'seed/manifest.json')
    for version in manifest['component_versions']:
        run(['git', 'rev-parse', '--verify', f'refs/tags/{version}^{{commit}}'], capture=True)
    announce(f'Prerequisites ready: linux/{arch}, {len(nodes)} Kubernetes node(s), '
             f'{info["MemTotal"] / (1024 ** 3):.1f} GiB Docker memory.')
    return arch


def install(accept_eula):
    check()
    import images
    import kubernetes
    import projects
    import services
    ensure_env_password(INFRA / 'artifactory/.env', 'ARTIFACTORY_DB_PASSWORD')
    compose('gitlab-ce', 'up', '-d')
    compose('artifactory', 'up', '-d')
    def gitlab_ready():
        response = compose('gitlab-ce', 'exec', '-T', 'gitlab', 'curl', '--fail', '--silent',
                           'http://localhost:8929/-/readiness', capture=True)
        return json.loads(response).get('status') == 'ok'

    wait_ready('GitLab', gitlab_ready, timeout=1200)
    key = projects.configure_access()
    projects.ensure_projects()
    projects.seed_projects(key)
    projects.protect_projects()

    def registry_ready():
        with HTTP.open(local_url(8082, '/artifactory/api/system/ping'), timeout=10) as response:
            return response.status == 200

    wait_ready('Artifactory', registry_ready, timeout=900)
    services.artifactory(accept_eula)
    references = images.build_and_publish()
    os.environ['DOCKER_CONFIG'] = str(INFRA / 'artifactory/secrets/docker-publisher')
    kubernetes.configure()
    services.sonar(references)
    services.runners(references)
    save_json(STATE / 'installation.json', {'architecture': docker_architecture(), 'completed': True})
    announce('Installation configured. Run ./infra/setup.sh verify to execute the application and sample pipelines.')
    status()


def status():
    for stack in STACKS:
        project = {'gitlab-ce': 'organization-gitlab-ce', 'artifactory': 'organization-artifactory',
                   'sonarqube': 'organization-sonarqube', 'gitlab-runner': 'organization-gitlab-runner'}[stack]
        output = run(['docker', 'ps', '-a', '--filter', f'label=com.docker.compose.project={project}',
                      '--format', '{{.Names}}: {{.Status}}'], capture=True).strip()
        announce(output or f'{stack}: not installed')
    announce('GitLab: http://localhost:8929 (root); initial password: infra/gitlab-ce/secrets/initial_root_password')
    announce('Artifactory: http://localhost:8082 (admin); credentials: infra/artifactory/secrets/credentials.json')
    announce('SonarQube: http://localhost:9000 (admin); credentials: infra/sonarqube/secrets/credentials.json')


def verify():
    results = {}
    for name in ('hello-world', 'ci-samples'):
        pid = project_id(name)
        data = {'ref': 'main'}
        if name == 'ci-samples':
            data['inputs'] = {'sample': 'all'}
        pipeline = gitlab(f'/projects/{pid}/pipeline', 'POST', data)
        announce(f'Validating {name}: {pipeline["web_url"]}')
        deadline = time.monotonic() + 5400
        last = None
        while time.monotonic() < deadline:
            current = gitlab(f'/projects/{pid}/pipelines/{pipeline["id"]}')
            if current['status'] != last:
                last = current['status']
                announce(f'{name}: {last}')
            if last == 'success':
                results[name] = {'pipeline_id': pipeline['id'], 'sha': current['sha'], 'status': last}
                save_json(STATE / 'verification.json', results)
                break
            if last in ('failed', 'canceled', 'skipped', 'manual'):
                raise RuntimeError(f'{name} validation ended with {last}; inspect {pipeline["web_url"]}.')
            time.sleep(10)
        else:
            raise RuntimeError(f'{name} validation timed out; the pipeline was left running for inspection.')
    announce('Application and all selected sample pipelines succeeded.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'check', 'status', 'verify', 'reset'], nargs='?', default='install')
    parser.add_argument('--accept-jcr-eula', action='store_true', help='Explicitly accept the JCR EULA supplied by the local instance')
    parser.add_argument('--delete-data', action='store_true', help='Explicitly delete the data listed by reset')
    args = parser.parse_args()
    if args.command == 'install':
        install(args.accept_jcr_eula)
    elif args.command == 'reset':
        import reset
        reset.reset(args.delete_data)
    else:
        {'check': check, 'status': status, 'verify': verify}[args.command]()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, KeyError) as error:
        print(f'Installation stopped: {error}', file=sys.stderr)
        raise SystemExit(1) from None
