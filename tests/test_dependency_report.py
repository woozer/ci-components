"""Verify useful MR summaries without turning incomplete scans into success."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import dependency_report as report
from report_api import publish_mr


class DependencyReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / '.ci-output/dependency-check'
        self.directory.mkdir(parents=True)
        self.env = {'CI_PROJECT_DIR': str(self.root), 'CI_JOB_NAME': 'dependency-check',
                    'CI_PIPELINE_ID': '123', 'CI_COMMIT_SHA': 'a' * 40, 'CI_JOB_STATUS': 'success',
                    'CI_PIPELINE_URL': 'https://gitlab.example/project/-/pipelines/123',
                    'CI_JOB_URL': 'https://gitlab.example/project/-/jobs/456',
                    'CI_API_V4_URL': 'https://gitlab.example/api/v4',
                    'CI_PROJECT_ID': '7', 'CI_MERGE_REQUEST_SOURCE_PROJECT_ID': '7',
                    'CI_MERGE_REQUEST_IID': '2', 'GITLAB_MR_REPORT_TOKEN': 'fixture-token',
                    'DEPENDENCY_CHECK_CVSS': '7'}
        self.data = {'scanInfo': {}, 'dependencies': [
            {'fileName': 'first.jar', 'vulnerabilities': [{'source': 'NVD', 'name': 'CVE-2026-1234', 'severity': 'HIGH'}]},
            {'fileName': 'second.jar', 'vulnerabilities': [{'source': 'NVD', 'name': 'CVE-2026-1234', 'severity': 'HIGH'}]}]}
        self.api = Mock()
        self.api.request.return_value = {'state': 'opened', 'sha': 'a' * 40}

    def run_report(self):
        (self.directory / 'dependency-check-report.json').write_text(json.dumps(self.data))
        with patch.object(report, 'Api', return_value=self.api), patch.object(report, 'publish_mr') as publish, \
                patch('sys.stdout', new=io.StringIO()):
            report.run(self.env)
        return publish

    def test_summary_counts_unique_findings_and_shows_affected_dependencies(self):
        publish = self.run_report()
        body = (self.directory / 'summary.md').read_text()
        for expected in ('Unieke kwetsbaarheden: **1**', 'met bevindingen: **2**', 'CVE-2026-1234',
                         'first.jar, second.jar', '| HIGH | 1 |', '/pipelines/123/test_report'):
            self.assertIn(expected, body)
        publish.assert_called_once()

    def test_failed_job_is_not_reported_as_green_even_with_no_findings(self):
        self.env['CI_JOB_STATUS'] = 'failed'
        self.data['dependencies'] = []
        self.run_report()
        body = (self.directory / 'summary.md').read_text()
        self.assertIn('Niet geslaagd', body)
        self.assertNotIn('**Geslaagd**', body)

    def test_incomplete_report_is_rejected(self):
        self.data = {'dependencies': []}
        with self.assertRaises(report.ReportError):
            self.run_report()
        self.assertFalse((self.directory / 'summary.md').exists())

    def test_stale_or_closed_merge_request_does_not_get_a_comment(self):
        for mr in ({'state': 'closed', 'sha': 'a' * 40}, {'state': 'opened', 'sha': 'b' * 40}):
            self.api.request.return_value = mr
            self.run_report().assert_not_called()

    def test_fork_is_not_a_report_target(self):
        self.env['CI_MERGE_REQUEST_SOURCE_PROJECT_ID'] = '99'
        with self.assertRaises(report.ReportError):
            self.run_report()
        self.api.request.assert_not_called()

    def test_missing_token_keeps_summary_artifact(self):
        self.env.pop('GITLAB_MR_REPORT_TOKEN')
        self.run_report().assert_not_called()
        self.assertTrue((self.directory / 'summary.md').exists())
        self.api.request.assert_not_called()

    def test_notes_are_updated_only_for_the_reporter_and_same_marker(self):
        api = Mock()
        marker, body = '<!-- report -->', '<!-- report -->\nUpdated'
        api.request.side_effect = [{'id': 42}, [
            {'id': 1, 'author': {'id': 99}, 'body': marker + '\nUser comment'},
            {'id': 2, 'author': {'id': 42}, 'body': marker + '\nOld'}], {}]
        self.assertEqual('updated', publish_mr(api, '7', '2', body, marker))
        api.request.assert_called_with('/projects/7/merge_requests/2/notes/2', 'PUT', {'body': body})


if __name__ == '__main__':
    unittest.main()
