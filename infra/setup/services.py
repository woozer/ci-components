"""Configure local service accounts and their existing CI integrations."""
import json
import sys
from urllib.parse import quote
from urllib.request import Request

from common import INFRA, STATE, announce, compose, gitlab, load_json, load_module, project_id, run, save, save_json


def artifactory(accept_eula=False):
    sys.path.insert(0, str(INFRA / 'artifactory'))
    import bootstrap as registry
    registry.main()
    session = registry.ui_session(load_json(registry.PRIVATE / 'credentials.json')['admin'])
    endpoint = registry.ORIGIN + '/ui/api/v1/ui/jcr/eula'
    if not (STATE / 'jcr-eula-accepted.json').exists():
        with session.open(endpoint, timeout=30) as response:
            content = json.load(response)['content']
        save(INFRA / 'artifactory/eula.html', content)
        if not accept_eula:
            raise RuntimeError('Review infra/artifactory/eula.html. If you agree, rerun install --accept-jcr-eula.')
        request = Request(endpoint + '/accept', method='POST', data=b'{}', headers={
            'Origin': registry.ORIGIN, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'})
        with session.open(request, timeout=30):
            pass
        save_json(STATE / 'jcr-eula-accepted.json', {'version': '7.161.15', 'accepted': True})
    load_module('docker_hub', INFRA / 'artifactory/configure-docker-hub.py').main()


def sonar(images):
    module = load_module('sonar_bootstrap', INFRA / 'sonarqube/bootstrap.py')
    password = module.credentials()['database']
    save(INFRA / 'sonarqube/.env', f'SONARQUBE_IMAGE={images["sonarqube"]}\nPOSTGRES_IMAGE={images["postgres"]}\nSONAR_DB_PASSWORD={password}\n')
    compose('sonarqube', 'up', '-d', '--wait', '--wait-timeout', '600')
    for name, token in [('hello-world', 'gitlab-analysis-token'), ('ci-samples', 'samples-analysis-token')]:
        module.PROJECT = name
        module.TOKEN_NAME = token
        module.configure()


def runners(images):
    sys.path.insert(0, str(INFRA / 'gitlab-runner'))
    import configure
    configure.main()
    run(['python3', INFRA / 'gitlab-runner/configure-samples.py'])
    run(['python3', INFRA / 'gitlab-runner/configure-releases.py'])
    for project in ('hello-world', 'ci-samples'):
        configure.variable('SONAR_CI_IMAGE', images['sonar'], project=project_id(project))
        configure.variable('JAVA_CI_IMAGE', images['java'], project=project_id(project))
    samples = project_id('ci-samples')
    configure.variable('CI_VALIDATION_IMAGE', images['validation'], project=samples)
    configure.variable('MAVEN_SETTINGS_FILE', '<settings><servers><server><id>maven-repository</id>'
        '<username>gitlab-ci-token</username><password>${env.CI_JOB_TOKEN}</password>'
        '</server></servers></settings>', file=True, project=samples)
    configure.variable('CI_SAMPLES_PROJECT', 'root/ci-samples', project=project_id('ci-components'))
    # Native multi-project triggers need an allowlist entry for their CI_JOB_TOKEN.
    for target, source in [('ci-samples', 'ci-components'), ('ci-components', 'ci-samples'), ('ci-components', 'hello-world')]:
        pid, source_id = project_id(target), project_id(source)
        path = f'/projects/{pid}/job_token_scope/allowlist'
        if not any(item['id'] == source_id for item in gitlab(path + '?per_page=100')):
            gitlab(path, 'POST', {'target_project_id': source_id})
    sample_release_key()
    compose('gitlab-runner', 'up', '-d', 'runner')
    announce('Project runners and scoped CI credentials configured.')


def sample_release_key():
    import configure
    project = project_id('ci-samples')
    private = INFRA / 'gitlab-runner/secrets'
    key_path = private / 'samples-release-key'
    if not key_path.exists():
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'ci-samples-release', '-f', key_path])
    public = key_path.with_suffix('.pub').read_text().strip()
    key = next((k for k in gitlab(f'/projects/{project}/deploy_keys') if k['key'].split()[:2] == public.split()[:2]), None)
    if key is None:
        key = gitlab(f'/projects/{project}/deploy_keys', 'POST', {'title': 'Sample release tags only', 'key': public, 'can_push': True})
    tags = gitlab(f'/projects/{project}/protected_tags')
    protected = next((tag for tag in tags if tag['name'] == 'v*'), None)
    if protected is None:
        gitlab(f'/projects/{project}/protected_tags', 'POST', {'name': 'v*', 'create_access_level': 0,
            'allowed_to_create': [{'deploy_key_id': key['id']}]})
    else:
        access = protected['create_access_levels']
        if not any(item.get('deploy_key_id') == key['id'] for item in access) or any(
            item.get('deploy_key_id') not in (None, key['id']) or (not item.get('deploy_key_id') and item.get('access_level', 0) != 0)
            for item in access):
            raise RuntimeError('Sample release tag protection differs from the expected deploy-key-only policy.')
    configure.variable('RELEASE_GIT_KEY', key_path.read_text(), file=True, protected=True, project=project)
    configure.variable('RELEASE_GIT_KNOWN_HOSTS', (INFRA / 'gitlab-ce/secrets/known_hosts').read_text(), file=True, protected=True, project=project)
    configure.variable('RELEASE_GIT_URL', 'ssh://git@host.docker.internal:2424/root/ci-samples.git', protected=True, project=project)
