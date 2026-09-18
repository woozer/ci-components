#!/usr/bin/env python3
"""Exercise combined scanner jobs with controlled tool failures and reports."""
import json
from pathlib import Path
import tempfile
import unittest

from test_contracts import Harness, ROOT


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def sonar(self, **inputs):
        h = Harness(self.root, 'sonar', inputs=inputs, env={
            'SONAR_HOST_URL': 'https://sonar.example.com', 'SONAR_TOKEN': 'test-only',
            'SONAR_PROJECT_KEY': 'example'})
        h.env.pop('SONAR_REPORT_TOKEN', None)
        h.env.pop('GITLAB_REPORT_TOKEN', None)
        h.job['after_script'] = [command.replace('/opt/ci/sonar_report.py',
                                 str(ROOT / 'scripts/sonar_report.py')) for command in h.job['after_script']]
        h.write('bin/mvn', '''#!/bin/sh
printf '%s\n' "$@" > "$CI_PROJECT_DIR/maven-args"
printf 'scan\n' >> "$CI_PROJECT_DIR/events"
if [ "${FAKE_METADATA:-yes}" = yes ]; then
  printf 'ceTaskId=exact-task\n' > "$CI_MODULE_OUTPUT_DIR/report-task.txt"
  printf 'dashboardUrl=%s\n' "${FAKE_DASHBOARD_URL-https://sonar.example.com/dashboard?id=example}" >> "$CI_MODULE_OUTPUT_DIR/report-task.txt"
fi
exit "${FAKE_MAVEN_EXIT:-0}"
''')
        h.hook('post', 'printf "post\\n" >> "$CI_PROJECT_DIR/events"')
        h.hook('cleanup', 'printf "cleanup\\n" >> "$CI_PROJECT_DIR/events"')
        return h

    def test_sonar_waits_for_native_gate_and_publishes_task_after_success(self):
        h = self.sonar(**{'maven-executable': 'mvn', 'gate-timeout': '420', 'scanner-version': '5.5.0.6356'})
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        args = (self.root / 'maven-args').read_text().splitlines()
        self.assertIn('-Dsonar.qualitygate.wait=true', args)
        self.assertIn('-Dsonar.qualitygate.timeout=420', args)
        self.assertNotIn('clean', args)  # Preserve coverage artifacts from the test job.
        self.assertEqual(['scan', 'post', 'cleanup'], h.events())
        self.assertEqual('passed', h.outputs()['SONAR_STATUS'])
        self.assertIn('ceTaskId=exact-task', (self.root / h.outputs()['SONAR_TASK_FILE']).read_text())
        self.assertEqual(0, h.cleanup.returncode, h.cleanup.stderr)
        self.assertEqual({'sonar': [{'external_link': {
            'label': 'Open SonarQube', 'url': 'https://sonar.example.com/dashboard?id=example'}}]},
            json.loads((h.output_file.parent / 'annotations.json').read_text()))

    def test_sonar_scanner_or_gate_failure_blocks_post_hook_and_outputs(self):
        h = self.sonar(**{'maven-executable': 'mvn'})
        h.env['FAKE_MAVEN_EXIT'] = '1'
        self.assertNotEqual(0, h.run().returncode)
        self.assertEqual(['scan', 'cleanup'], h.events())
        self.assertTrue((h.output_file.parent / 'report-task.txt').exists())
        self.assertFalse(h.output_file.exists())
        self.assertEqual(0, h.cleanup.returncode, h.cleanup.stderr)
        self.assertTrue(json.loads((h.output_file.parent / 'annotations.json').read_text())['sonar'])

    def test_sonar_missing_metadata_is_not_success(self):
        h = self.sonar(**{'maven-executable': 'mvn'})
        h.env['FAKE_METADATA'] = 'no'
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())
        self.assertEqual(0, h.cleanup.returncode, h.cleanup.stderr)
        self.assertFalse((h.output_file.parent / 'annotations.json').exists())

    def test_sonar_dashboard_link_preserves_url_and_works_with_custom_job_and_workdir(self):
        h = self.sonar(**{'maven-executable': 'mvn', 'job-name': 'backend-sonar',
                         'working-directory': 'backend'})
        (self.root / 'backend').mkdir()
        url = 'https://sonar.example.com/dashboard?id=team:app&branch=main&extra="quoted"\\path'
        h.env['FAKE_DASHBOARD_URL'] = url
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(0, h.cleanup.returncode, h.cleanup.stderr)
        report = json.loads((h.output_file.parent / 'annotations.json').read_text())
        self.assertEqual(url, report['sonar'][0]['external_link']['url'])

    def test_sonar_metadata_without_dashboard_url_does_not_invent_a_link(self):
        for url in ('', 'javascript:alert(1)', 'https://sonar.example.com/invalid\tpath'):
            with self.subTest(url=url):
                h = self.sonar(**{'maven-executable': 'mvn'})
                h.env['FAKE_DASHBOARD_URL'] = url
                result = h.run()
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(0, h.cleanup.returncode, h.cleanup.stderr)
                self.assertEqual({'sonar': []},
                                 json.loads((h.output_file.parent / 'annotations.json').read_text()))

    def dependency_check(self):
        h = Harness(self.root, 'dependency-check', inputs={'maven-executable': 'mvn'}, env={
            'CI_PIPELINE_URL': 'https://gitlab.example/project/-/pipelines/99',
            'CI_JOB_URL': 'https://gitlab.example/project/-/jobs/42'})
        h.env.pop('NVD_API_KEY', None)
        h.env.pop('GITLAB_MR_REPORT_TOKEN', None)
        h.job['after_script'] = [command.replace('/opt/ci/dependency_report.py',
                                 str(ROOT / 'scripts/dependency_report.py')) for command in h.job['after_script']]
        h.write('bin/mvn', '''#!/bin/sh
printf '%s\n' "$@" > "$CI_PROJECT_DIR/maven-args"
if [ "${FAKE_REPORT:-yes}" = yes ]; then
  printf '{"scanInfo":{},"dependencies":[]}' > "$CI_MODULE_OUTPUT_DIR/dependency-check-report.json"
  if [ "${FAKE_JUNIT:-yes}" = yes ]; then
    printf '<testsuites/>\n' > "$CI_MODULE_OUTPUT_DIR/dependency-check-junit.xml"
  fi
fi
exit "${FAKE_MAVEN_EXIT:-0}"
''')
        return h

    def test_dependency_check_uses_keyless_feed_and_configured_report_directory(self):
        h = self.dependency_check()
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        args = (self.root / 'maven-args').read_text().splitlines()
        self.assertIn('-DnvdDatafeedUrl=https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{0}.json.gz', args)
        self.assertIn('-Dodc.outputDirectory=' + str(h.output_file.parent), args)
        self.assertIn('-DdataDirectory=' + str(self.root / '.cache/dependency-check'), args)
        self.assertIn('-DfailOnError=true', args)
        self.assertIn('-DfailBuildOnCVSS=7', args)
        self.assertIn('-DjunitFailOnCVSS=7', args)
        self.assertIn('-DossIndexAnalyzerEnabled=false', args)
        self.assertIn('-Dformats=HTML,JSON,JUNIT', args)
        self.assertFalse(any('ApiKey' in arg for arg in args))
        self.assertEqual('passed', h.outputs()['DEPENDENCY_CHECK_STATUS'])
        self.assertIn('**Geslaagd**', (h.output_file.parent / 'summary.md').read_text())

    def test_dependency_check_feed_or_scan_error_blocks_success(self):
        h = self.dependency_check()
        h.env['FAKE_MAVEN_EXIT'] = '1'
        self.assertNotEqual(0, h.run().returncode)
        self.assertTrue((h.output_file.parent / 'dependency-check-report.json').exists())
        self.assertFalse(h.output_file.exists())

    def test_dependency_check_requires_a_report(self):
        h = self.dependency_check()
        h.env['FAKE_REPORT'] = 'no'
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def test_dependency_check_requires_junit_for_the_promised_gitlab_report(self):
        h = self.dependency_check()
        h.env['FAKE_JUNIT'] = 'no'
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def fortify(self, receipt=None, policy=None):
        h = Harness(self.root, 'fortify', inputs={'scan-adapter': 'scan.sh', 'gate-adapter': 'gate.sh'})
        (self.root / 'receipt.json').write_text(json.dumps(receipt if receipt is not None else {
            'commit_sha': 'a' * 40, 'pipeline_id': '99', 'status': 'completed', 'scan_id': 'scan-1'}))
        (self.root / 'policy.json').write_text(json.dumps(policy if policy is not None else {
            'scan_id': 'scan-1', 'policy_version': 'policy-1', 'status': 'passed'}))
        h.write('scan.sh', '''#!/bin/sh
set -eu
printf 'scan\n' >> "$CI_PROJECT_DIR/events"
cp "$CI_PROJECT_DIR/receipt.json" "$2"
exit "${FAKE_SCAN_EXIT:-0}"
''')
        h.write('gate.sh', '''#!/bin/sh
set -eu
printf 'gate\n' >> "$CI_PROJECT_DIR/events"
cp "$CI_PROJECT_DIR/policy.json" "$4"
exit "${FAKE_GATE_EXIT:-0}"
''')
        h.hook('post', 'printf "post\\n" >> "$CI_PROJECT_DIR/events"')
        h.hook('cleanup', 'printf "cleanup\\n" >> "$CI_PROJECT_DIR/events"')
        return h

    def test_fortify_publishes_scan_and_policy_together(self):
        h = self.fortify()
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['scan', 'gate', 'post', 'cleanup'], h.events())
        self.assertEqual('passed', h.outputs()['FORTIFY_STATUS'])
        for name in ('FORTIFY_RECEIPT', 'FORTIFY_REPORT'):
            self.assertEqual('scan-1', json.loads((self.root / h.outputs()[name]).read_text())['scan_id'])

    def test_fortify_rejects_wrong_or_incomplete_receipt_before_gate(self):
        for field, value in [('commit_sha', 'wrong'), ('pipeline_id', '98'),
                             ('status', 'running'), ('scan_id', '')]:
            with self.subTest(field=field):
                h = self.fortify()
                receipt = json.loads((self.root / 'receipt.json').read_text())
                receipt[field] = value
                (self.root / 'receipt.json').write_text(json.dumps(receipt))
                h.env['PYTHONOPTIMIZE'] = '1'  # Validation must not rely on assert statements.
                h.write('events', '')
                self.assertNotEqual(0, h.run().returncode)
                self.assertEqual(['scan', 'cleanup'], h.events())
                self.assertFalse(h.output_file.exists())

    def test_fortify_rejects_mismatched_failed_or_missing_policy(self):
        for policy in [{'scan_id': 'wrong', 'policy_version': 'policy-1', 'status': 'passed'},
                       {'scan_id': 'scan-1', 'policy_version': '', 'status': 'passed'},
                       {'scan_id': 'scan-1', 'policy_version': 'policy-1', 'status': 'failed'}, {}]:
            with self.subTest(policy=policy):
                h = self.fortify(policy=policy)
                h.write('events', '')
                self.assertNotEqual(0, h.run().returncode)
                self.assertEqual(['scan', 'gate', 'cleanup'], h.events())
                self.assertFalse(h.output_file.exists())

    def test_fortify_adapter_errors_block_outputs_even_with_valid_reports(self):
        for stage in ('SCAN', 'GATE'):
            with self.subTest(stage=stage):
                h = self.fortify()
                h.env['FAKE_' + stage + '_EXIT'] = '2'
                h.write('events', '')
                self.assertNotEqual(0, h.run().returncode)
                self.assertNotIn('post', h.events())
                self.assertFalse(h.output_file.exists())

    def image_scan(self):
        h = Harness(self.root, 'image-scan', env={'IMAGE_BUILD_IMAGE_REF': 'registry.example.com/app@sha256:' + 'a' * 64})
        h.write('bin/trivy', '''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
root = pathlib.Path(os.environ['CI_PROJECT_DIR'])
with (root / 'trivy-calls').open('a') as stream:
    stream.write(json.dumps(args) + '\\n')
stage = 'scan' if args[0] == 'image' else ('sbom' if 'cyclonedx' in args else 'gate')
if '--output' in args:
    pathlib.Path(args[args.index('--output') + 1]).write_text('{}')
sys.exit(int(os.environ.get('FAKE_' + stage.upper() + '_EXIT', '0')))
''')
        return h

    def test_image_scan_uses_one_inventory_for_both_reports_then_enforces_gate(self):
        h = self.image_scan()
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        calls = [json.loads(line) for line in (self.root / 'trivy-calls').read_text().splitlines()]
        self.assertEqual(['image', 'convert', 'convert'], [args[0] for args in calls])
        self.assertIn('--list-all-pkgs', calls[0])
        self.assertIn('UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL', calls[0])
        report = str(self.root / h.outputs()['IMAGE_SCAN_REPORT'])
        self.assertEqual(report, calls[1][-1])
        self.assertEqual(report, calls[2][-1])
        self.assertIn('HIGH,CRITICAL', calls[2])
        self.assertEqual('1', calls[2][calls[2].index('--exit-code') + 1])
        self.assertTrue((self.root / h.outputs()['IMAGE_SCAN_SBOM']).exists())
        self.assertEqual('always', h.job['artifacts']['when'])
        self.assertIn('cyclonedx', h.job['artifacts']['reports'])

    def test_image_gate_failure_retains_both_reports_without_success_outputs(self):
        h = self.image_scan()
        h.env['FAKE_GATE_EXIT'] = '1'
        self.assertNotEqual(0, h.run().returncode)
        self.assertTrue((h.output_file.parent / 'image-scan.json').exists())
        self.assertTrue((h.output_file.parent / 'sbom.cdx.json').exists())
        self.assertFalse(h.output_file.exists())

    def test_image_scan_and_conversion_errors_stop_the_job(self):
        for stage, expected_calls in [('SCAN', 1), ('SBOM', 2)]:
            with self.subTest(stage=stage):
                h = self.image_scan()
                h.env['FAKE_' + stage + '_EXIT'] = '2'
                h.write('trivy-calls', '')
                self.assertNotEqual(0, h.run().returncode)
                self.assertEqual(expected_calls, len((self.root / 'trivy-calls').read_text().splitlines()))
                self.assertFalse(h.output_file.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
