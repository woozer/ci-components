"""Check that organization choices survive deployment and release children."""
import unittest

from test_contracts import PARSED, ROOT, interpolate


class OrganizationConfigurationTests(unittest.TestCase):
    def test_organization_settings_reach_every_consumer_and_child(self):
        settings = {
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
        includes = body['include']
        children = []
        for entry in includes:
            values = entry.get('inputs', {})
            for option in ('plain-http', 'allow-insecure-registry'):
                if option in values:
                    self.assertIs(values[option], False)
            if entry['local'] == '/templates/helm-deploy.yml':
                self.assertEqual('', values['kubeconfig-variable'])
            if 'pipeline-config' in values:
                children.append(values['pipeline-config'])
            if entry['local'] == '/templates/maven-publish.yml':
                self.assertEqual('$MAVEN_PUBLISH_URL', values['repository-url'])
        self.assertEqual(2, len(children))
        for child in children:
            for option in ('runner-tags', 'buildkit-runner-tags', 'registry-plain-http',
                           'kubeconfig-variable', 'clusters', 'user-configs'):
                self.assertIn(option + ':', child)
            self.assertIn('openshift-test', child)
            self.assertIn('organization-buildkit', child)
            self.assertIn('registry-plain-http: false', child)
            self.assertIn("kubeconfig-variable: ''", child)


if __name__ == '__main__':
    unittest.main()
