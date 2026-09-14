"""Explicitly reset demo-owned data while retaining source code and Git history."""
import shutil

from common import INFRA, STATE, announce, compose, kubectl, load_json, run

STACKS = ('gitlab-runner', 'sonarqube', 'artifactory', 'gitlab-ce')
FILES = ('artifactory/ci-images.json', 'artifactory/docker-hub.json', 'artifactory/eula.html',
         'gitlab-runner/validation-image.json')


def reset(delete_data=False):
    announce('Reset targets: the four organization-* Compose stacks and their volumes;')
    announce('Kubernetes namespaces hello-world and ci-samples; infra secrets, .env and generated state.')
    announce('Source code, Git history, Docker Desktop Kubernetes and unrelated workloads are retained.')
    if not delete_data:
        announce('Preview only. Use reset --delete-data to execute this reset.')
        return
    # Ensure source and released component objects survive removal of local GitLab.
    check = run(['git', 'status', '--porcelain'], capture=True)
    if check.strip():
        raise RuntimeError('Commit the source changes before resetting the demo.')
    for version in load_json(INFRA / 'seed/manifest.json')['component_versions']:
        run(['git', 'rev-parse', '--verify', f'refs/tags/{version}^{{commit}}'], capture=True)
    compose('gitlab-runner', 'stop', 'runner')
    for namespace in ('hello-world', 'ci-samples'):
        kubectl('delete', 'namespace', namespace, '--ignore-not-found', '--timeout=120s')
    for stack in STACKS:
        compose(stack, 'down', '--volumes', '--remove-orphans')
    for stack in STACKS:
        shutil.rmtree(INFRA / stack / 'secrets', ignore_errors=True)
        (INFRA / stack / '.env').unlink(missing_ok=True)
    for name in FILES:
        (INFRA / name).unlink(missing_ok=True)
    shutil.rmtree(STATE, ignore_errors=True)
    announce('Demo data removed. Run ./infra/setup.sh install to create a fresh installation.')
