"""Verify portable architecture selection and private, reusable setup state."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'infra/setup'))
from common import architecture, ensure_env_password, load_module, save
from images import helper_image
import reset as demo_reset
import projects as demo_projects
sonar_bootstrap = load_module('sonar_setup_test', ROOT / 'infra/sonarqube/bootstrap.py')


class InstallerTests(unittest.TestCase):
    def test_sonar_passwords_always_meet_policy_and_survive_reinstall(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(sonar_bootstrap, 'PRIVATE', Path(directory)), \
             patch.object(sonar_bootstrap.secrets, 'token_urlsafe', return_value='x' * 32) as random:
            credentials = sonar_bootstrap.credentials()
            for account in ('admin', 'ci'):
                password = credentials[account]
                self.assertGreaterEqual(len(password), 12)
                for pattern in ('[a-z]', '[A-Z]', '[0-9]', '[^a-zA-Z0-9]'):
                    self.assertRegex(password, pattern)
            random.reset_mock()
            self.assertEqual(credentials, sonar_bootstrap.credentials())
            random.assert_not_called()
            self.assertEqual(0o600, (Path(directory) / 'credentials.json').stat().st_mode & 0o777)

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

    def test_generated_state_is_ignored_but_installer_sources_are_not(self):
        paths = ['infra/artifactory/secrets/credentials.json', 'infra/artifactory/.env',
                 'infra/gitlab-runner/secrets/config/config.toml', 'infra/.state/installation.json',
                 'infra/gitlab-ce/secrets/setup-key', 'infra/artifactory/ci-images.json']
        result = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], cwd=ROOT,
            input='\n'.join(paths), capture_output=True, text=True, check=True)
        self.assertEqual(set(paths), set(result.stdout.splitlines()))
        result = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], cwd=ROOT,
            input='infra/setup/main.py\ninfra/setup.sh\n.gitmodules\n', capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertEqual('', result.stdout)

    def test_installer_requires_initialized_sources_at_the_pinned_commit(self):
        for status in ('', '-abc java', '+abc java', 'Uabc java'):
            with self.subTest(status=status), patch.object(demo_projects, 'run', return_value=status):
                with self.assertRaisesRegex(RuntimeError, 'git submodule update --init --recursive'):
                    demo_projects.check_sources()
        with patch.object(demo_projects, 'run', return_value=' abc source'):
            demo_projects.check_sources()

    def test_catalog_registration_is_idempotent_and_preserves_existing_metadata(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as directory:
                private = Path(directory) / 'gitlab-ce/secrets'
                private.mkdir(parents=True)
                (private / 'provisioning-token').write_text('fixture-token')
                responses = [{'data': {'project': {'isCatalogResource': enabled}}},
                             {'data': {'catalogResourcesCreate': {'errors': []}}}]
                with patch.object(demo_projects, 'INFRA', Path(directory)), \
                     patch.object(demo_projects, 'load_json', return_value={'id': 2}), \
                     patch.object(demo_projects, 'gitlab', return_value={
                         'description': 'Existing description', 'path_with_namespace': 'team/components'}) as api, \
                     patch.object(demo_projects, 'request_json', side_effect=responses) as graphql, \
                     patch.object(demo_projects, 'announce'):
                    demo_projects.configure_catalog()
                api.assert_called_once_with('/projects/2')
                self.assertEqual(1 if enabled else 2, graphql.call_count)
                self.assertEqual({'path': 'team/components'}, graphql.call_args.kwargs['data']['variables'])

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
