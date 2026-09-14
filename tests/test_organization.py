"""Check that organization choices survive deployment and release children."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_contracts import PARSED, ROOT, interpolate


class OrganizationConfigurationTests(unittest.TestCase):
    def test_organization_settings_reach_every_consumer_and_child(self):
        settings = {
            'release-line': '2.3',
            'runner-tags': ['organization-java'],
            'buildkit-runner-tags': ['organization-buildkit'],
            'registry-plain-http': False,
            'kubeconfig-variable': '',
            'clusters': ['openshift-dev', 'openshift-test'],
            'cluster': 'openshift-test',
            'user-configs': ['default', 'performance'],
            'user-config': 'performance',
        }
        body = interpolate(PARSED[str(ROOT / 'pipelines/java-service.yml')], settings)
        self.assertEqual(['organization-java'], body['default']['tags'])
        self.assertEqual(['organization-buildkit'], body['publish-ui-image']['tags'])
        self.assertEqual('dev/openshift-test', body['variables']['DEPLOY_ENVIRONMENT'])
        self.assertIs(body['variables']['HELM_REGISTRY_PLAIN_HTTP'], False)
        includes = body['include']
        children = []
        for entry in includes:
            values = entry.get('inputs', {})
            for option in ('plain-http', 'allow-insecure-registry'):
                if option in values:
                    self.assertIs(values[option], False)
            if entry['local'] == '/templates/release-reserve.yml':
                self.assertEqual('2.3', values['release-line'])
            if entry['local'] == '/templates/helm-deploy.yml':
                self.assertEqual('', values['kubeconfig-variable'])
            if 'pipeline-config' in values:
                children.append(values['pipeline-config'])
            if entry['local'] == '/templates/maven-publish.yml':
                self.assertEqual('$MAVEN_PUBLISH_URL', values['repository-url'])
        self.assertEqual(2, len(children))
        for child in children:
            for option in ('release-line', 'runner-tags', 'buildkit-runner-tags', 'registry-plain-http',
                           'kubeconfig-variable', 'clusters', 'user-configs'):
                self.assertIn(option + ':', child)
            self.assertIn('openshift-test', child)
            self.assertIn('organization-buildkit', child)
            self.assertIn('registry-plain-http: false', child)
            self.assertIn("kubeconfig-variable: ''", child)

    def test_sample_helm_login_uses_the_local_registry_transport_default(self):
        config = PARSED[str(ROOT / 'config/organization.yml')][0]['variables']
        command = PARSED[str(ROOT / 'shared/helm.yml')][0]['.helm-login']['before_script'][1]
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            password = folder / 'password'
            password.write_text('fixture-password')
            helm = folder / 'helm'
            helm.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            helm.chmod(0o755)
            env = {**os.environ, 'PATH': directory + os.pathsep + os.environ['PATH'],
                   'OCI_REGISTRY': config['OCI_REGISTRY'], 'ARTIFACTORY_USERNAME': 'fixture',
                   'ARTIFACTORY_PASSWORD_FILE': str(password),
                   'HELM_REGISTRY_PLAIN_HTTP': config.get('HELM_REGISTRY_PLAIN_HTTP', '')}
            result = subprocess.run(['sh', '-eu', '-c', command], env=env, capture_output=True, text=True, check=True)
        self.assertIn('--plain-http', result.stdout.splitlines())


if __name__ == '__main__':
    unittest.main()
