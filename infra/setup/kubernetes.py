"""Configure namespace-scoped access for the local Docker Desktop demo."""
import base64
import json

from common import INFRA, kubectl, load_json, run, save_json, wait_ready


def configure():
    registry = 'host.docker.internal:8082'
    folder = '/etc/containerd/certs.d/' + registry
    run(['docker', 'exec', 'desktop-control-plane', 'mkdir', '-p', folder])
    run(['docker', 'exec', '-i', 'desktop-control-plane', 'tee', folder + '/hosts.toml'],
        input=f'server = "http://{registry}"\n[host."http://{registry}"]\n  capabilities = ["pull", "resolve"]\n', capture=True)
    auth = (INFRA / 'artifactory/secrets/docker-read.json').read_bytes()
    for namespace, filename in [('hello-world', 'kubeconfig.json'), ('ci-samples', 'samples-kubeconfig.json')]:
        kubectl('apply', '-f', '-', input=json.dumps({'apiVersion': 'v1', 'kind': 'Namespace',
                                                     'metadata': {'name': namespace}}))
        rbac = (INFRA / 'gitlab-runner/kubernetes.yaml').read_text().replace('namespace: hello-world', 'namespace: ' + namespace)
        kubectl('apply', '-f', '-', input=rbac)
        kubectl('apply', '-f', '-', input=json.dumps({'apiVersion': 'v1', 'kind': 'Secret',
            'metadata': {'name': 'local-artifactory', 'namespace': namespace},
            'type': 'kubernetes.io/dockerconfigjson',
            'data': {'.dockerconfigjson': base64.b64encode(auth).decode()}}))

        def read_token():
            return json.loads(kubectl('-n', namespace, 'get', 'secret', 'gitlab-deployer-token', '-o', 'json')).get('data', {})

        wait_ready(namespace + ' deployment account', lambda: read_token().get('token'), timeout=60)
        data = read_token()
        config = {'apiVersion': 'v1', 'kind': 'Config',
            'clusters': [{'name': 'local', 'cluster': {'server': 'https://desktop-control-plane:6443',
                                                     'certificate-authority-data': data['ca.crt']}}],
            'users': [{'name': 'deployer', 'user': {'token': base64.b64decode(data['token']).decode()}}],
            'contexts': [{'name': 'local', 'context': {'cluster': 'local', 'user': 'deployer', 'namespace': namespace}}],
            'current-context': 'local'}
        save_json(INFRA / 'gitlab-runner/secrets' / filename, config)
