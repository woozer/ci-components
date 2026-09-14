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
        inputs = {'release-branch': 'main', 'version': '1.2.3'}
        if name == 'release-reserve':
            inputs.update({
                'release-line': '1.2',
                'git-url': 'ssh://git@gitlab.invalid/group/service.git',
                'git-key-file': str(self.root / 'key'),
                'git-known-hosts-file': str(self.root / 'known-hosts'),
                'pipeline-config': 'version: "@RELEASE_VERSION@"\ncommit: "@RELEASE_COMMIT@"',
            })
        else:
            inputs.update({
                'commit': 'a' * 40, 'image-path': 'releases/service',
                'chart-path': 'releases/charts/service', 'registry-url': 'https://registry.invalid',
                'registry-username': 'publisher', 'registry-password-file': str(self.root / 'password'),
            })
        inputs.update(overrides)
        h = Harness(self.root, name, inputs=inputs, env={
            'CI_COMMIT_BRANCH': 'main', 'CI_DEFAULT_BRANCH': 'main',
            'CI_COMMIT_REF_PROTECTED': 'true', 'CI_COMMIT_TAG': '',
            'CI_PIPELINE_URL': 'https://gitlab.invalid/group/service/-/pipelines/99',
        })
        if name == 'release-check':
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

    def test_release_records_all_deployable_digests_and_rejects_mismatched_versions(self):
        for extra_version, expected_success in [('1.2.3', True), ('1.2.4', False)]:
            with self.subTest(extra_version=extra_version):
                h = Harness(self.root, 'gitlab-release', inputs={
                    'version': '1.2.3', 'api-url': 'https://gitlab.invalid/api/v4',
                    'additional-artifact-prefixes': 'UI_IMAGE:UI_CHART',
                    'artifact-base-url': 'http://public-artifactory/artifactory/',
                }, env={
                    'JIB_IMAGE_REF': 'registry.invalid/api@sha256:' + 'a' * 64,
                    'CHART_REF': 'oci://registry.invalid/charts/api', 'CHART_VERSION': '1.2.3',
                    'UI_IMAGE_IMAGE_REF': 'registry.invalid/ui@sha256:' + 'b' * 64,
                    'UI_CHART_REF': 'oci://registry.invalid/charts/ui', 'UI_CHART_VERSION': extra_version,
                    'CI_PROJECT_URL': 'https://gitlab.invalid/group/app', 'CI_PROJECT_ID': '1',
                    'CI_PIPELINE_URL': 'https://gitlab.invalid/group/app/-/pipelines/99',
                    'CI_JOB_TOKEN': 'test-token',
                })
                calls = self.root / 'release-api-called'
                calls.unlink(missing_ok=True)
                h.write('bin/curl', '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/release-api-called"\n')
                result = h.run()
                self.assertEqual(expected_success, result.returncode == 0, result.stderr)
                self.assertEqual(expected_success, calls.exists())
                self.assertEqual(expected_success, h.output_file.exists())
                if expected_success:
                    body = (h.output_file.parent / 'release.md').read_text()
                    self.assertIn('registry.invalid/api@sha256:' + 'a' * 64, body)
                    self.assertIn('registry.invalid/ui@sha256:' + 'b' * 64, body)
                    self.assertIn('oci://registry.invalid/charts/ui', body)
                    request = calls.read_text().splitlines()
                    urls = [arg.split('=', 1)[1] for arg in request if arg.startswith('assets[links][][url]=')]
                    self.assertEqual([
                        'https://gitlab.invalid/group/app/-/packages',
                        'https://gitlab.invalid/group/app/-/pipelines/99',
                        'http://public-artifactory/artifactory/api/1.2.3/manifest.json',
                        'http://public-artifactory/artifactory/charts/api/1.2.3/manifest.json',
                        'http://public-artifactory/artifactory/ui/1.2.3/manifest.json',
                        'http://public-artifactory/artifactory/charts/ui/1.2.3/manifest.json',
                    ], urls)
                    names = [arg for arg in request if arg.startswith('assets[links][][name]=')]
                    self.assertEqual(6, len(set(names)))

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
        self.assertFalse((self.root / 'http-calls').exists())
        self.assertFalse((self.root / 'password').exists())

    def test_auto_starts_at_initial_version_without_existing_tags(self):
        h = self.harness(version='auto', **{'release-line': '0.1'})
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('0.1.0', h.outputs()['RELEASE_VERSION'])
        self.assertIn('--sort=-version:refname', self.calls())

    def test_auto_increments_highest_reserved_patch_within_the_configured_line(self):
        h = self.harness(version='auto', **{'release-line': '2.0'})
        # Git returns version-sorted refs; reserved tags count without a release record.
        h.env['FAKE_REMOTE_TAGS'] = '\n'.join('a'*40 + '\trefs/tags/' + tag for tag in
            ['v9.0.0-rc1', 'v8.0.100', 'v2.10.99', 'v2.0.11-rc1', 'v2.0.9', 'v2.0.8', 'v1.100.0'])
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('2.0.10', h.outputs()['RELEASE_VERSION'])

    def test_new_minor_or_major_line_starts_at_patch_zero(self):
        for line in ('2.4', '3.0'):
            with self.subTest(line=line):
                h = self.harness(version='auto', **{'release-line': line})
                h.env['FAKE_REMOTE_TAGS'] = '\n'.join('a'*40 + '\trefs/tags/' + tag for tag in
                    ['v8.0.0', 'v2.40.99', 'v2.3.123'])
                result = h.run()
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(line + '.0', h.outputs()['RELEASE_VERSION'])

    def test_invalid_release_lines_fail_before_git_access(self):
        for line in ('', 'v2.3', '2', '2.03', '2.3.0', '2.3-rc', '2.3\n4.5'):
            with self.subTest(line=line):
                h = self.harness(version='auto', **{'release-line': line})
                self.assertNotEqual(0, h.run().returncode)
                self.assertEqual('', self.calls())
                self.assertFalse(h.output_file.exists())

    def test_manual_version_cannot_change_the_reviewed_release_line(self):
        h = self.harness(version='3.0.0', **{'release-line': '2.3'})
        result = h.run()
        self.assertNotEqual(0, result.returncode)
        self.assertIn('must belong to release-line 2.3', result.stderr)
        self.assertEqual('', self.calls())
        self.assertFalse(h.output_file.exists())

    def test_auto_does_not_guess_initial_version_when_tag_listing_fails(self):
        h = self.harness(version='auto')
        h.env['FAKE_TAG_LIST_EXIT'] = '128'
        self.assertNotEqual(0, h.run().returncode)
        self.assertNotIn('push ', self.calls())
        self.assertFalse(h.output_file.exists())

    def test_auto_rejects_arithmetic_overflow(self):
        h = self.harness(version='auto', **{'release-line': '1.0'})
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

    def test_existing_image_blocks_release_check_before_building(self):
        h = self.harness('release-check')
        h.env['FAKE_HTTP_STATUS'] = '200'
        result = h.run()
        self.assertNotEqual(0, result.returncode)
        self.assertIn('already has a published artifact', result.stderr)
        self.assertNotIn('push ', self.calls())
        self.assertFalse(h.output_file.exists())

    def test_repository_errors_block_publication(self):
        for status in ['401', '403', '500']:
            with self.subTest(status=status):
                h = self.harness('release-check')
                h.env['FAKE_HTTP_STATUS'] = status
                self.assertNotEqual(0, h.run().returncode)
                self.assertNotIn('push ', self.calls())
                self.assertFalse(h.output_file.exists())

    def test_network_failure_blocks_publication(self):
        h = self.harness('release-check')
        h.env['FAKE_HTTP_EXIT'] = '7'
        self.assertNotEqual(0, h.run().returncode)
        self.assertNotIn('push ', self.calls())
        self.assertFalse(h.output_file.exists())

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
        self.assertIn('assets[links][][url]=https://registry.invalid/v2/releases/service/manifests/sha256:' + 'b' * 64, request)
        self.assertIn('assets[links][][url]=https://registry.invalid/v2/charts/service/manifests/1.2.3', request)
        self.assertIn(image, (h.output_file.parent / 'release.md').read_text())
        self.assertEqual('http://public-gitlab/group/service/-/releases/v1.2.3', h.outputs()['GITLAB_RELEASE_URL'])

    def test_release_asset_base_url_cannot_publish_credentials(self):
        for url in ['https://user:password@registry.invalid/artifactory', 'https://registry.invalid?token=secret']:
            with self.subTest(url=url):
                h = Harness(self.root, 'gitlab-release', inputs={
                    'version': '1.2.3', 'artifact-base-url': url})
                h.write('bin/curl', '#!/bin/sh\n: > "$CI_PROJECT_DIR/release-api-called"\n')
                self.assertNotEqual(0, h.run().returncode)
                self.assertFalse((self.root / 'release-api-called').exists())
                self.assertFalse(h.output_file.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
