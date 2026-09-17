#!/usr/bin/env python3
"""Publish an analysis-bound Sonar summary as a GitLab commit discussion."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


METRICS = {
    'coverage': 'Testdekking (%)',
    'duplicated_lines_density': 'Duplicatie (%)',
    'software_quality_reliability_issues': 'Betrouwbaarheidsbevindingen',
    'software_quality_security_issues': 'Beveiligingsbevindingen',
    'software_quality_maintainability_issues': 'Onderhoudbaarheidsbevindingen',
}


class ReportError(Exception):
    """An unavailable or unverifiable report must not change the scanner result."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Credentials must remain with the configured server.
        return None


class Api:
    def __init__(self, base_url, token, header='Authorization'):
        self.base_url = http_url(base_url).rstrip('/')
        self.headers = {header: ('Bearer ' if header == 'Authorization' else '') + token}
        self.http = build_opener(NoRedirect())

    def request(self, path, method='GET', values=None):
        url, data = self.base_url + path, None
        if method == 'GET' and values:
            url += '?' + urlencode(values)
        elif values is not None:
            data = json.dumps(values).encode()
        request = Request(url, method=method, data=data,
                          headers={**self.headers, 'Content-Type': 'application/json'})
        try:
            with self.http.open(request, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            raise ReportError(f'Report API returned HTTP {error.code}.') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise ReportError('Report API is unavailable or returned invalid JSON.') from None


def http_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or re.search(r'[\x00-\x20\x7f]', value)):
        raise ReportError('Expected an HTTP(S) URL without credentials or whitespace.')
    return value


def markdown(value):
    return str(value).replace('\\', '\\\\').replace('`', '\\`').replace('|', '\\|').replace('\n', ' ')


def link(label, url):
    # Angle-bracket links preserve query strings and parentheses in dashboard URLs.
    target = quote(http_url(url), safe=":/?#[]@!$&'()+,;=%-._~")
    return f'[{label}](<{target}>)'


def latest_analysis(sonar, project, analysis_id, commit):
    analyses = sonar.request('/api/project_analyses/search', values={'project': project, 'ps': 1})['analyses']
    if not analyses or analyses[0]['key'] != analysis_id or analyses[0].get('revision') != commit:
        raise ReportError('Sonar analysis does not match this commit or a newer analysis is already available.')
    return analyses[0]


def collect(sonar, metadata, project, commit):
    if metadata.get('projectKey') != project or not metadata.get('ceTaskId'):
        raise ReportError('Scanner metadata is missing or belongs to another Sonar project.')
    task = sonar.request('/api/ce/task', values={'id': metadata['ceTaskId']})['task']
    if task.get('status') != 'SUCCESS' or task.get('componentKey') != project or not task.get('analysisId'):
        raise ReportError('The requested Sonar analysis has not completed successfully.')
    analysis_id = task['analysisId']
    analysis = latest_analysis(sonar, project, analysis_id, commit)
    gate = sonar.request('/api/qualitygates/project_status', values={'analysisId': analysis_id})['projectStatus']
    measures = sonar.request('/api/measures/component', values={
        'component': project, 'metricKeys': ','.join(METRICS)})['component']
    if measures.get('key') != project or gate.get('status') not in ('OK', 'ERROR', 'WARN', 'NONE'):
        raise ReportError('Sonar returned an unexpected project or quality gate status.')
    # Measures are the latest project values, unlike the analysis-specific gate.
    # Verify again after reading them so another analysis cannot be misattributed.
    latest_analysis(sonar, project, analysis_id, commit)
    return analysis, gate['status'], {m['metric']: m['value'] for m in measures['measures'] if 'value' in m}


def summary(env, metadata, analysis, gate, measures, marker):
    gate_label = {'OK': 'Geslaagd', 'ERROR': 'Afgekeurd', 'WARN': 'Waarschuwing', 'NONE': 'Niet beschikbaar'}[gate]
    lines = [marker, '**SonarQube — commitanalyse**', '',
             f"Commit: `{env['CI_COMMIT_SHA']}`",
             link('Pipeline ' + env['CI_PIPELINE_ID'], env['CI_PIPELINE_URL']),
             f"Jobstatus: `{markdown(env.get('CI_JOB_STATUS', 'unknown'))}`",
             f"Quality gate: **{gate_label}**", '',
             '| Metriek | Gehele project |', '|---|---|']
    for key, label in METRICS.items():
        lines.append(f'| {label} | {markdown(measures.get(key, "Niet beschikbaar"))} |')
    if metadata.get('dashboardUrl'):
        lines.extend(['', link('Open SonarQube', metadata['dashboardUrl'])])
    lines.extend(['', f"Analyse: `{markdown(analysis['key'])}` · {markdown(analysis['date'])}", '',
                  'Dit overzicht hoort bij de genoemde commit; het is geen analyse van een open merge request.'])
    return '\n'.join(lines) + '\n'


def publish(gitlab, project_id, commit, body, marker):
    author = gitlab.request('/user')['id']
    path = f'/projects/{quote(project_id, safe="")}/repository/commits/{commit}/discussions'
    page = 1
    while True:
        discussions = gitlab.request(path, values={'per_page': 100, 'page': page})
        for discussion in discussions:
            for note in discussion['notes']:
                if note['author']['id'] == author and note['body'].startswith(marker + '\n'):
                    if note['body'] != body:
                        gitlab.request(f"{path}/{discussion['id']}/notes/{note['id']}", 'PUT', {'body': body})
                        return 'updated'
                    return 'unchanged'
        if len(discussions) < 100:
            break
        page += 1
    gitlab.request(path, 'POST', {'body': body})
    return 'created'


def run(env):
    directory = Path(env['CI_PROJECT_DIR']) / '.ci-output' / env['CI_JOB_NAME']
    task_file = directory / 'report-task.txt'
    if not task_file.is_file():
        print('No Sonar task metadata; no summary to publish.')
        return
    metadata = dict(line.split('=', 1) for line in task_file.read_text().splitlines() if '=' in line)
    annotations = {'sonar': []}
    if metadata.get('dashboardUrl'):
        try:
            annotations['sonar'].append({'external_link': {
                'label': 'Open SonarQube', 'url': http_url(metadata['dashboardUrl'])}})
        except ReportError:
            pass
    (directory / 'annotations.json').write_text(json.dumps(annotations) + '\n')
    if not env.get('SONAR_REPORT_TOKEN'):
        print('SONAR_REPORT_TOKEN is not configured; only the dashboard link is published.')
        return
    commit = env['CI_COMMIT_SHA']
    if not re.fullmatch(r'[0-9a-f]{40,64}', commit):
        raise ReportError('CI_COMMIT_SHA must contain the full analyzed commit SHA.')
    project = env['SONAR_PROJECT_KEY']
    sonar = Api(env['SONAR_HOST_URL'], env['SONAR_REPORT_TOKEN'])
    analysis, gate, measures = collect(sonar, metadata, project, commit)
    identity = json.dumps([project, env['CI_PIPELINE_ID'], env['CI_JOB_NAME']])
    marker = '<!-- ci-sonar-report:' + hashlib.sha256(identity.encode()).hexdigest() + ' -->'
    body = summary(env, metadata, analysis, gate, measures, marker)
    (directory / 'summary.md').write_text(body)
    if not env.get('GITLAB_REPORT_TOKEN'):
        print('Sonar summary saved; GITLAB_REPORT_TOKEN is not configured for commit comments.')
        return
    gitlab = Api(env.get('GITLAB_REPORT_API_URL') or env['CI_API_V4_URL'],
                 env['GITLAB_REPORT_TOKEN'], 'PRIVATE-TOKEN')
    result = publish(gitlab, env['CI_PROJECT_ID'], commit, body, marker)
    print(f'Sonar commit summary {result}.')


def main():
    try:
        run(os.environ)
    except (ReportError, KeyError, TypeError, ValueError, OSError) as error:
        message = str(error) if isinstance(error, ReportError) else 'Missing or invalid reporting configuration or response.'
        print('Sonar reporting: ' + message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
