"""Verify shared organization settings used by component examples."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_contracts import PARSED, ROOT

class OrganizationConfigurationTests(unittest.TestCase):
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
