"""Verify commit attribution, API failures and idempotent Sonar comments."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sonar_report as report


COMMIT = 'a' * 40
ANALYSIS = {'key': 'analysis-1', 'revision': COMMIT, 'date': '2026-09-17T12:00:00+0000'}


class SonarReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / '.ci-output' / 'sonar'
        self.directory.mkdir(parents=True)
        self.metadata = {'projectKey': 'example', 'ceTaskId': 'task-1',
                         'dashboardUrl': 'https://sonar.example/dashboard?id=example'}
        (self.directory / 'report-task.txt').write_text('\n'.join(f'{k}={v}' for k, v in self.metadata.items()))
        self.env = {'CI_PROJECT_DIR': str(self.root), 'CI_JOB_NAME': 'sonar',
                    'CI_COMMIT_SHA': COMMIT, 'CI_PIPELINE_ID': '123', 'CI_PROJECT_ID': '7',
                    'CI_PIPELINE_URL': 'https://gitlab.example/team/app/-/pipelines/123',
                    'CI_API_V4_URL': 'https://gitlab.example/api/v4', 'CI_JOB_STATUS': 'success',
                    'SONAR_HOST_URL': 'https://sonar.example', 'SONAR_PROJECT_KEY': 'example',
                    'SONAR_REPORT_TOKEN': 'read-only-test-token', 'GITLAB_REPORT_TOKEN': 'report-test-token'}
        self.responses = {
            '/api/ce/task': {'task': {'status': 'SUCCESS', 'componentKey': 'example', 'analysisId': 'analysis-1'}},
            '/api/project_analyses/search': {'analyses': [ANALYSIS.copy()]},
            '/api/qualitygates/project_status': {'projectStatus': {'status': 'OK'}},
            '/api/measures/component': {'component': {'key': 'example', 'measures': [
                {'metric': 'coverage', 'value': '83.2'}, {'metric': 'duplicated_lines_density', 'value': '0.0'}]}},
        }
        self.sonar = Mock()
        self.sonar.request.side_effect = lambda path, **kwargs: self.responses[path]
        self.gitlab = Mock()
        self.gitlab.request.side_effect = lambda path, method='GET', values=None: (
            {'id': 42} if path == '/user' else [] if method == 'GET' else {'id': 'thread-1'})

    def run_report(self):
        with patch.object(report, 'Api', side_effect=[self.sonar, self.gitlab]), patch('sys.stdout', new=io.StringIO()):
            report.run(self.env)

    def test_summary_uses_exact_analysis_and_keeps_missing_metrics_explicit(self):
        self.run_report()
        body = (self.directory / 'summary.md').read_text()
        for expected in (COMMIT, 'Pipeline 123', 'Geslaagd', '83.2', 'Niet beschikbaar', 'analysis-1',
                         'geen analyse van een open merge request'):
            self.assertIn(expected, body)
        self.sonar.request.assert_any_call('/api/qualitygates/project_status', values={'analysisId': 'analysis-1'})
        post = self.gitlab.request.call_args
        self.assertEqual('POST', post.args[1])
        self.assertEqual(body, post.args[2]['body'])
        self.assertIn('/commits/' + COMMIT + '/discussions', post.args[0])
        self.assertEqual(self.metadata['dashboardUrl'],
                         json.loads((self.directory / 'annotations.json').read_text())['sonar'][0]['external_link']['url'])

    def test_failed_gate_is_reported_as_failed_without_losing_summary(self):
        self.responses['/api/qualitygates/project_status']['projectStatus']['status'] = 'ERROR'
        self.env['CI_JOB_STATUS'] = 'failed'
        self.run_report()
        body = (self.directory / 'summary.md').read_text()
        self.assertIn('**Afgekeurd**', body)
        self.assertIn('Jobstatus: `failed`', body)

    def test_wrong_commit_or_newer_analysis_is_never_posted(self):
        for field, value in (('revision', 'b' * 40), ('key', 'newer-analysis')):
            with self.subTest(field=field):
                self.responses['/api/project_analyses/search']['analyses'] = [{**ANALYSIS, field: value}]
                with self.assertRaises(report.ReportError):
                    self.run_report()
                self.gitlab.request.assert_not_called()
                self.assertFalse((self.directory / 'summary.md').exists())

    def test_analysis_finishing_during_measure_read_is_detected(self):
        def response(path, **kwargs):
            if path == '/api/measures/component':
                self.responses['/api/project_analyses/search']['analyses'] = [{**ANALYSIS, 'key': 'newer-analysis'}]
            return self.responses[path]
        self.sonar.request.side_effect = response
        with self.assertRaises(report.ReportError):
            self.run_report()
        self.gitlab.request.assert_not_called()

    def test_unfinished_or_wrong_project_task_cannot_publish(self):
        for update in ({'status': 'PENDING'}, {'status': 'FAILED'}, {'componentKey': 'other'}, {'analysisId': None}):
            with self.subTest(update=update):
                self.responses['/api/ce/task']['task'] = {'status': 'SUCCESS', 'componentKey': 'example',
                                                        'analysisId': 'analysis-1', **update}
                with self.assertRaises(report.ReportError):
                    self.run_report()
                self.gitlab.request.assert_not_called()

    def test_missing_tokens_keep_artifacts_without_posting(self):
        self.env.pop('GITLAB_REPORT_TOKEN')
        self.run_report()
        self.assertTrue((self.directory / 'summary.md').exists())
        self.gitlab.request.assert_not_called()
        self.env.pop('SONAR_REPORT_TOKEN')
        with patch.object(report, 'Api') as api, patch('sys.stdout', new=io.StringIO()):
            report.run(self.env)
        api.assert_not_called()
        self.assertTrue((self.directory / 'annotations.json').exists())

    def test_no_metadata_does_not_call_either_api(self):
        (self.directory / 'report-task.txt').unlink()
        with patch.object(report, 'Api') as api, patch('sys.stdout', new=io.StringIO()):
            report.run(self.env)
        api.assert_not_called()
        self.assertFalse((self.directory / 'summary.md').exists())

    def test_gitlab_failure_preserves_local_summary(self):
        self.gitlab.request.side_effect = report.ReportError('Report API returned HTTP 403.')
        with self.assertRaises(report.ReportError):
            self.run_report()
        self.assertTrue((self.directory / 'summary.md').exists())
        self.assertTrue((self.directory / 'annotations.json').exists())

    def test_existing_own_comment_is_updated_or_left_unchanged(self):
        marker = '<!-- ci-sonar-report:test -->'
        body = marker + '\nCurrent summary'
        for previous, expected in ((marker + '\nOld summary', 'updated'), (body, 'unchanged')):
            with self.subTest(expected=expected):
                api = Mock()
                api.request.side_effect = [{'id': 42}, [{'id': 'thread', 'notes': [
                    {'id': 3, 'author': {'id': 42}, 'body': previous}]}], {}]
                self.assertEqual(expected, report.publish(api, '7', COMMIT, body, marker))
                if expected == 'updated':
                    self.assertEqual('PUT', api.request.call_args.args[1])
                    self.assertTrue(api.request.call_args.args[0].endswith('/thread/notes/3'))
                else:
                    self.assertEqual(2, api.request.call_count)

    def test_pagination_and_other_authors_do_not_create_duplicate_or_edit_user_comment(self):
        marker, body = '<!-- ci-sonar-report:test -->', '<!-- ci-sonar-report:test -->\nSummary'
        api = Mock()
        other = {'id': 'other', 'notes': [{'id': 1, 'author': {'id': 99}, 'body': body}]}
        own = {'id': 'own', 'notes': [{'id': 2, 'author': {'id': 42}, 'body': body}]}
        api.request.side_effect = [{'id': 42}, [other] * 100, [own]]
        self.assertEqual('unchanged', report.publish(api, '7', COMMIT, body, marker))
        self.assertEqual({'per_page': 100, 'page': 2}, api.request.call_args.kwargs['values'])
        self.assertEqual(3, api.request.call_count)

    def test_http_failures_do_not_expose_credentials_or_response_body(self):
        api = report.Api('https://sonar.example', 'secret-token')
        error = HTTPError('https://sonar.example/?token=secret-token', 401, 'secret-token', {},
                          io.BytesIO(b'secret-response'))
        with patch.object(api.http, 'open', side_effect=error):
            with self.assertRaisesRegex(report.ReportError, '^Report API returned HTTP 401\.$'):
                api.request('/api/ce/task', values={'id': 'task'})
        self.assertIsNone(report.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example'))

    def test_main_analysis_only_comments_on_matching_merged_requests(self):
        self.env.update(CI_COMMIT_BRANCH='main', CI_DEFAULT_BRANCH='main')
        api = Mock()
        base = {'state': 'merged', 'target_project_id': 7, 'target_branch': 'main', 'merge_commit_sha': COMMIT}
        api.request.return_value = [
            {**base, 'iid': 1}, {**base, 'iid': 2, 'state': 'opened'},
            {**base, 'iid': 3, 'merge_commit_sha': 'b' * 40},
            {**base, 'iid': 4, 'target_branch': 'other'}, {**base, 'iid': 5, 'target_project_id': 99}]
        with patch.object(report, 'publish_mr') as publish, patch('sys.stdout', new=io.StringIO()):
            report.publish_merged_mrs(api, self.env, 'body', 'marker')
        publish.assert_called_once_with(api, '7', 1, 'body', 'marker')

    def test_branch_analysis_does_not_post_a_merge_result(self):
        api = Mock()
        self.env.update(CI_COMMIT_BRANCH='feature', CI_DEFAULT_BRANCH='main')
        report.publish_merged_mrs(api, self.env, 'body', 'marker')
        api.request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
