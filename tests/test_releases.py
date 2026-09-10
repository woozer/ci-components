"""Exercise release refusal paths without touching GitLab or a registry."""
import os
from pathlib import Path
import tempfile
import unittest

from test_contracts import Harness


class ReleaseContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def harness(self, name='release-reserve', **overrides):
        inputs = {
            'release-branch': 'main', 'image-path': 'releases/service',
            'chart-path': 'releases/charts/service', 'registry-url': 'https://registry.invalid',
            'registry-username': 'publisher', 'registry-password-file': str(self.root / 'password'),
            'version': '1.2.3',
        }
        if name == 'release-reserve':
            inputs.update({
                'git-url': 'ssh://git@gitlab.invalid/group/service.git',
                'git-key-file': str(self.root / 'key'),
                'git-known-hosts-file': str(self.root / 'known-hosts'),
                'pipeline-config': 'version: "@RELEASE_VERSION@"\ncommit: "@RELEASE_COMMIT@"',
            })
        else:
            inputs['commit'] = 'a' * 40
        inputs.update(overrides)
        h = Harness(self.root, name, inputs=inputs, env={
            'CI_COMMIT_BRANCH': 'main', 'CI_DEFAULT_BRANCH': 'main',
            'CI_COMMIT_REF_PROTECTED': 'true', 'CI_COMMIT_TAG': '',
            'CI_PIPELINE_URL': 'https://gitlab.invalid/group/service/-/pipelines/99',
        })
        h.write('password', 'secret-password')
        h.write('key', 'private-key-fixture')
        h.write('known-hosts', 'public-key-fixture')
        h.write('bin/git', '''#!/bin/sh
printf '%s\n' "$*" >> "$CI_PROJECT_DIR/git-calls"
case "$1" in
  rev-parse)
    if [ "$2" = HEAD ]; then printf '%s\n' "${FAKE_HEAD:-$CI_COMMIT_SHA}"
    else printf '%s\n' "${FAKE_TAG_COMMIT:-$CI_COMMIT_SHA}"; fi ;;
  merge-base) exit "${FAKE_ANCESTOR_EXIT:-0}" ;;
  ls-remote)
    if [ "$2" = --tags ]; then
      printf '%s\n' "${FAKE_REMOTE_TAGS:-}"
      exit "${FAKE_TAG_LIST_EXIT:-0}"
    fi
    exit "${FAKE_TAG_LOOKUP_EXIT:-2}" ;;
  push) exit "${FAKE_PUSH_EXIT:-0}" ;;
esac
''')
        h.write('bin/curl', '''#!/bin/sh
printf 'request\n' >> "$CI_PROJECT_DIR/http-calls"
printf '%s' "${FAKE_HTTP_STATUS:-404}"
exit "${FAKE_HTTP_EXIT:-0}"
''')
        return h

    def calls(self):
        p = self.root / 'git-calls'
        return p.read_text() if p.exists() else ''

    def test_reserve_emits_version_and_binds_child_to_exact_commit(self):
        h = self.harness()
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('1.2.3', h.outputs()['RELEASE_VERSION'])
        self.assertEqual('v1.2.3', h.outputs()['RELEASE_TAG'])
        child = (h.output_file.parent / 'pipeline.yml').read_text()
        self.assertIn('version: "1.2.3"', child)
        self.assertIn('a' * 40, child)
        self.assertNotIn('secret-password', child)
        self.assertIn('refs/tags/v1.2.3:refs/tags/v1.2.3', self.calls())
        self.assertNotIn('--force', self.calls())

    def test_auto_starts_at_initial_version_without_existing_tags(self):
        h = self.harness(version='auto')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('0.1.0', h.outputs()['RELEASE_VERSION'])
        self.assertIn('--sort=-version:refname', self.calls())

    def test_auto_increments_highest_reserved_stable_version(self):
        h = self.harness(version='auto')
        # Git returns version-sorted refs; reserved tags count without a release record.
        h.env['FAKE_REMOTE_TAGS'] = '\n'.join('a'*40 + '\trefs/tags/' + tag for tag in
            ['v9.0.0-rc1', 'v2.0.9', 'v2.0.8', 'v1.100.0'])
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('2.0.10', h.outputs()['RELEASE_VERSION'])

    def test_auto_does_not_guess_initial_version_when_tag_listing_fails(self):
        h = self.harness(version='auto')
        h.env['FAKE_TAG_LIST_EXIT'] = '128'
        self.assertNotEqual(0, h.run().returncode)
        self.assertNotIn('push ', self.calls())
        self.assertFalse(h.output_file.exists())

    def test_auto_rejects_arithmetic_overflow(self):
        h = self.harness(version='auto')
        h.env['FAKE_REMOTE_TAGS'] = 'a'*40 + '\trefs/tags/v1.0.99999999999999999999'
        self.assertNotEqual(0, h.run().returncode)
        self.assertNotIn('push ', self.calls())

    def test_invalid_versions_fail_before_git_or_registry_access(self):
        for version in ['', 'v1.2.3', '1.02.3', '1.2.3-SNAPSHOT', '1.2.3; touch bad', '1.2.3\n4.5.6']:
            with self.subTest(version=version):
                h = self.harness(version=version)
                result = h.run()
                self.assertNotEqual(0, result.returncode)
                self.assertFalse(h.output_file.exists())
                self.assertEqual('', self.calls())

    def test_protected_feature_branch_cannot_release(self):
        h = self.harness()
        h.env['CI_COMMIT_BRANCH'] = 'feature/change'
        self.assertNotEqual(0, h.run().returncode)
        self.assertEqual('', self.calls())

    def test_unprotected_main_cannot_release(self):
        h = self.harness()
        h.env['CI_COMMIT_REF_PROTECTED'] = 'false'
        self.assertNotEqual(0, h.run().returncode)
        self.assertEqual('', self.calls())

    def test_tag_pipeline_cannot_reserve_release(self):
        h = self.harness()
        h.env['CI_COMMIT_TAG'] = 'v1.2.3'
        self.assertNotEqual(0, h.run().returncode)
        self.assertEqual('', self.calls())

    def test_checkout_must_match_pipeline_commit(self):
        h = self.harness()
        h.env['FAKE_HEAD'] = 'b' * 40
        self.assertNotEqual(0, h.run().returncode)
        self.assertNotIn('push ', self.calls())

    def test_commit_must_be_in_release_branch_history(self):
        h = self.harness()
        h.env['FAKE_ANCESTOR_EXIT'] = '1'
        self.assertNotEqual(0, h.run().returncode)
        self.assertNotIn('push ', self.calls())

    def test_existing_tag_is_never_reused(self):
        h = self.harness()
        h.env['FAKE_TAG_LOOKUP_EXIT'] = '0'
        result = h.run()
        self.assertNotEqual(0, result.returncode)
        self.assertIn('already reserves', result.stderr)
        self.assertNotIn('push ', self.calls())

    def test_failed_tag_lookup_does_not_mean_version_is_free(self):
        h = self.harness()
        h.env['FAKE_TAG_LOOKUP_EXIT'] = '128'
        self.assertNotEqual(0, h.run().returncode)
        self.assertNotIn('push ', self.calls())

    def test_existing_image_blocks_reservation(self):
        h = self.harness()
        h.env['FAKE_HTTP_STATUS'] = '200'
        result = h.run()
        self.assertNotEqual(0, result.returncode)
        self.assertIn('already has a published artifact', result.stderr)
        self.assertNotIn('push ', self.calls())

    def test_repository_errors_block_publication(self):
        for status in ['401', '403', '500']:
            with self.subTest(status=status):
                h = self.harness()
                h.env['FAKE_HTTP_STATUS'] = status
                self.assertNotEqual(0, h.run().returncode)
                self.assertNotIn('push ', self.calls())

    def test_network_failure_blocks_publication(self):
        h = self.harness()
        h.env['FAKE_HTTP_EXIT'] = '7'
        self.assertNotEqual(0, h.run().returncode)
        self.assertNotIn('push ', self.calls())

    def test_racing_tag_creation_does_not_publish_child_configuration(self):
        h = self.harness()
        h.env['FAKE_PUSH_EXIT'] = '1'
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())
        self.assertFalse((h.output_file.parent / 'pipeline.yml').exists())

    def test_check_accepts_reserved_commit(self):
        h = self.harness('release-check')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('1.2.3', h.outputs()['RELEASE_CHECK_VERSION'])

    def test_check_rejects_changed_tag_target(self):
        h = self.harness('release-check')
        h.env['FAKE_TAG_COMMIT'] = 'b' * 40
        result = h.run()
        self.assertNotEqual(0, result.returncode)
        self.assertIn('different commit', result.stderr)

    def test_check_rejects_retry_after_publication(self):
        h = self.harness('release-check')
        h.env['FAKE_HTTP_STATUS'] = '200'
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def test_release_record_uses_reachable_api_and_verified_artifact_outputs(self):
        image = 'registry.invalid/releases/service@sha256:' + 'b' * 64
        h = Harness(self.root, 'gitlab-release', inputs={
            'version': '1.2.3', 'api-url': 'http://internal-gitlab:8929/api/v4/'}, env={
            'JIB_IMAGE_REF': image, 'CHART_REF': 'oci://registry.invalid/charts/service',
            'CHART_VERSION': '1.2.3', 'CI_PROJECT_ID': '7', 'CI_JOB_TOKEN': 'fixture-token',
            'CI_PROJECT_URL': 'http://public-gitlab/group/service',
            'CI_PIPELINE_URL': 'http://public-gitlab/group/service/-/pipelines/99'})
        h.write('bin/curl', '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/release-request"\n')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        request = (self.root / 'release-request').read_text().splitlines()
        self.assertEqual('http://internal-gitlab:8929/api/v4/projects/7/releases', request[-1])
        self.assertIn(image, (h.output_file.parent / 'release.md').read_text())
        self.assertEqual('http://public-gitlab/group/service/-/releases/v1.2.3', h.outputs()['GITLAB_RELEASE_URL'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
