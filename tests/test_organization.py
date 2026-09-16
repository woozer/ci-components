"""Check that organization choices survive deployment and release children."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_contracts import PARSED, ROOT, pipeline_config


class OrganizationConfigurationTests(unittest.TestCase):
    def test_organization_settings_reach_every_consumer_and_child(self):
        settings = {
            'library-ref': '1.0.0',
            'release-line': '2.3',
            'runner-tags': ['organization-java'],
            'buildkit-runner-tags': ['organization-buildkit'],
            'registry-plain-http': False,
            'kubeconfig-variable': '',
            'clusters': ['openshift-dev', 'openshift-test'],
            'cluster': 'openshift-test',
            'user-configs': ['default', 'performance'],
            'user-config': 'performance',
            'maven-project': 'services/api',
            'application': 'orders',
            'chart': 'charts/api',
            'ui-directory': 'frontend',
            'ui-application': 'orders-ui',
            'ui-chart': 'charts/web',
            'namespace': 'orders-test',
        }
        parent = pipeline_config(overrides=settings)
        children = {}
        replacements = {'@CLUSTER@': 'openshift-test', '@USER_CONFIG@': 'performance',
                        '$SELECTION_CLUSTER': 'openshift-test', '$SELECTION_USER_CONFIG': 'performance',
                        '@RELEASE_VERSION@': '2.3.4', '@RELEASE_COMMIT@': 'a' * 40,
                        '$APP_VERSION': '0.0.0-dev.314.gabcdef12', '$CI_PIPELINE_ID': '314'}
        for entry in parent['include']:
            values = entry.get('inputs', {})
            if entry['local'] == '/templates/release-reserve.yml':
                self.assertEqual('2.3', values['release-line'])
            if 'pipeline-config' not in values:
                continue
            generated = values['pipeline-config']
            for key, value in replacements.items():
                generated = generated.replace(key, value)
            config = json.loads(subprocess.check_output(
                ['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.generate(YAML.load(STDIN.read))'],
                input=generated, text=True))['include'][0]
            self.assertEqual('1.0.0', config['ref'])
            children[Path(config['file']).stem] = pipeline_config(config['file'].lstrip('/'), config['inputs'])
        self.assertEqual({'java-deploy', 'java-release'}, set(children))
        for body in (parent, *children.values()):
            self.assertEqual(['organization-java'], body['default']['tags'])
            self.assertIs(body['variables']['HELM_REGISTRY_PLAIN_HTTP'], False)
            for entry in body['include']:
                values = entry.get('inputs', {})
                for option in ('plain-http', 'allow-insecure-registry'):
                    if option in values:
                        self.assertIs(values[option], False)
                if entry['local'] == '/templates/helm-deploy.yml':
                    self.assertEqual('', values['kubeconfig-variable'])
                    self.assertEqual('orders-test', values['namespace'])
                    self.assertEqual('environment/cluster/openshift-test.yaml', values['values-file'])
                    self.assertEqual('environment/user/performance.yaml', values['override-values-file'])
                if entry['local'] == '/templates/maven-publish.yml':
                    self.assertEqual('$MAVEN_PUBLISH_URL', values['repository-url'])
                    self.assertEqual('services/api', values['project-selector'])
        for body in (parent, children['java-release']):
            self.assertEqual(['organization-buildkit'], body['publish-ui-image']['tags'])
        deploy = children['java-deploy']
        self.assertEqual('dev/openshift-test', deploy['variables']['DEPLOY_ENVIRONMENT'])
        self.assertEqual('0.0.0-dev.314.gabcdef12', deploy['variables']['APP_VERSION'])
        self.assertEqual([{'pipeline': '314', 'job': 'publish-image'},
                          {'pipeline': '314', 'job': 'publish-chart'}], deploy['helm-deploy']['needs'])
        release = children['java-release']
        self.assertEqual('release/dev/openshift-test', release['variables']['DEPLOY_ENVIRONMENT'])
        self.assertEqual('2.3.4', release['variables']['APP_VERSION'])
        self.assertEqual('a' * 40, release['variables']['RELEASE_COMMIT'])
        self.assertEqual([{'job': 'publish-image', 'artifacts': True},
                          {'job': 'publish-chart', 'artifacts': True}], release['helm-deploy']['needs'])
        for job in ('build', 'test', 'build-ui', 'test-ui'):
            self.assertFalse(release[job]['interruptible'])

    def test_entrypoint_and_child_boundaries_preserve_deployment_locks(self):
        parent = pipeline_config(overrides={'application': 'orders'})
        self.assertEqual('dev-orders', parent['.delivery-trigger']['resource_group'])
        self.assertIs(parent['.delivery-trigger']['inherit']['variables'], False)
        for job in ('deploy-dev', 'release-delivery'):
            self.assertEqual('.delivery-trigger', parent[job]['extends'])
            self.assertEqual('mirror', parent[job]['trigger']['strategy'])
        self.assertEqual('deploy-dev', parent['start-release']['needs'][0]['job'])
        self.assertEqual('delayed', parent['configure-deploy']['rules'][0]['when'])
        self.assertEqual('10 seconds', parent['configure-deploy']['rules'][0]['start_in'])
        for path in ('java-deploy', 'java-release'):
            child = pipeline_config('pipelines/internal/' + path + '.yml')
            condition = child['workflow']['rules'][0]['if']
            self.assertIn('$CI_PIPELINE_SOURCE == "parent_pipeline"', condition)
            self.assertIn('$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH', condition)
            self.assertIn('$CI_COMMIT_REF_PROTECTED == "true"', condition)
            self.assertEqual('never', child['workflow']['rules'][-1]['when'])
            self.assertNotIn('start-release', child)
        public = PARSED[str(ROOT / 'pipelines/java-service.yml')][0]['spec']['inputs']
        self.assertEqual({'library-ref', 'maven-project'},
                         {name for name, value in public.items() if 'default' not in value})
        self.assertFalse({'flow', 'version', 'commit', 'publish-needs', 'ui-publish-needs'} & public.keys())
        deployment = PARSED[str(ROOT / 'pipelines/internal/java-deploy.yml')][0]['spec']['inputs']
        self.assertFalse({'maven-project', 'release-line', 'clusters', 'user-configs', 'buildkit-runner-tags'} & deployment.keys())

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
