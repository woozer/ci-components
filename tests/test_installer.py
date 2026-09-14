"""Verify portable architecture selection and private, reusable setup state."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'infra/setup'))
from common import architecture, ensure_env_password, save
from images import helper_image
import reset as demo_reset


class InstallerTests(unittest.TestCase):
    def test_architecture_aliases_select_the_matching_runner_helper(self):
        for alias in ('x86_64', 'amd64'):
            self.assertEqual('gitlab/gitlab-runner-helper:x86_64-v19.3.0', helper_image(architecture(alias)))
        for alias in ('aarch64', 'arm64'):
            self.assertEqual('gitlab/gitlab-runner-helper:arm64-v19.3.0', helper_image(architecture(alias)))
        with self.assertRaises(RuntimeError):
            architecture('unsupported-cpu')

    def test_reinstall_preserves_database_password_and_private_file_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            ensure_env_password(path, 'DEMO_DB_PASSWORD')
            original = path.read_text()
            ensure_env_password(path, 'DEMO_DB_PASSWORD')
            self.assertEqual(original, path.read_text())
            self.assertTrue(original.startswith('DEMO_DB_PASSWORD='))
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            path.chmod(0o644)
            save(path, original)
            self.assertEqual(0o600, path.stat().st_mode & 0o777)

    def test_generated_state_is_ignored_but_installer_and_application_sources_are_not(self):
        paths = ['infra/artifactory/secrets/credentials.json', 'infra/artifactory/.env',
                 'infra/gitlab-runner/secrets/config/config.toml', 'infra/.state/installation.json',
                 'infra/gitlab-ce/secrets/setup-key', 'infra/artifactory/ci-images.json']
        result = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], cwd=ROOT,
            input='\n'.join(paths), capture_output=True, text=True, check=True)
        self.assertEqual(set(paths), set(result.stdout.splitlines()))
        result = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], cwd=ROOT,
            input='infra/setup/main.py\ninfra/setup.sh\njava/hello-app/pom.xml\n', capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertEqual('', result.stdout)

    def test_reset_preview_never_runs_destructive_commands(self):
        with patch.object(demo_reset, 'run') as command, patch.object(demo_reset, 'compose') as compose, \
             patch.object(demo_reset, 'kubectl') as kubectl, patch.object(demo_reset, 'announce'):
            demo_reset.reset()
        command.assert_not_called()
        compose.assert_not_called()
        kubectl.assert_not_called()

    def test_reset_refuses_uncommitted_sources_before_deleting_data(self):
        with patch.object(demo_reset, 'run', return_value=' M java/pom.xml'), \
             patch.object(demo_reset, 'compose') as compose, patch.object(demo_reset, 'kubectl') as kubectl, \
             patch.object(demo_reset, 'announce'):
            with self.assertRaisesRegex(RuntimeError, 'Commit the source'):
                demo_reset.reset(delete_data=True)
        compose.assert_not_called()
        kubectl.assert_not_called()


if __name__ == '__main__':
    unittest.main()
