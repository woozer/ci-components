#!/usr/bin/env python3
"""Summarize the current Dependency-Check artifact in its merge request."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote

from report_api import Api, ReportError, link, markdown, publish_mr


def summary(env, report, marker):
    dependencies = report['dependencies']
    if not isinstance(dependencies, list) or not isinstance(report.get('scanInfo'), dict):
        raise ReportError('Dependency-Check report is incomplete.')
    findings, affected = {}, 0
    for dependency in dependencies:
        vulnerabilities = dependency.get('vulnerabilities', [])
        affected += bool(vulnerabilities)
        for finding in vulnerabilities:
            key = (finding.get('source', 'unknown'), finding['name'])
            entry = findings.setdefault(key, {'severity': finding.get('severity', 'UNKNOWN'), 'files': set()})
            entry['files'].add(dependency['fileName'])
    counts = Counter(str(f['severity']).upper() for f in findings.values())
    status = 'Geslaagd' if env.get('CI_JOB_STATUS') == 'success' else 'Niet geslaagd; bekijk de job voor de oorzaak'
    lines = [marker, '**OWASP Dependency-Check**', '', f'Jobresultaat: **{status}**',
             f"Commit: `{env['CI_COMMIT_SHA']}`", link('Pipeline ' + env['CI_PIPELINE_ID'], env['CI_PIPELINE_URL']), '',
             f"CVSS-grens voor blokkeren: **{markdown(env['DEPENDENCY_CHECK_CVSS'])}**.",
             f'Gecontroleerde dependencies: **{len(dependencies)}**; met bevindingen: **{affected}**.',
             f'Unieke kwetsbaarheden: **{len(findings)}**.', '',
             '| Ernst | Aantal |', '|---|---|']
    for severity in ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'):
        lines.append(f'| {severity} | {counts[severity]} |')
    if findings:
        lines.extend(['', '| Bevinding | Ernst | Dependency |', '|---|---|---|'])
        order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        rows = sorted(findings.items(), key=lambda row: (order.get(str(row[1]['severity']).upper(), 4), row[0]))
        for (_, name), finding in rows[:20]:
            files = ', '.join(sorted(finding['files']))
            lines.append(f"| {markdown(name)} | {markdown(finding['severity'])} | {markdown(files[:300])} |")
        if len(findings) > 20:
            lines.append('\nDe eerste twintig bevindingen staan hierboven; het volledige rapport bevat alle details.')
    else:
        lines.append('\nHet rapport bevat geen bekende kwetsbaarheden.')
    directory = quote(env['CI_JOB_NAME'], safe='')
    lines.extend(['', link('Testrapport', env['CI_PIPELINE_URL'] + '/test_report'),
                  link('Volledige rapporten', env['CI_JOB_URL'] + '/artifacts/browse/.ci-output/' + directory + '/'),
                  '', 'Onderdrukte bevindingen en feedinformatie staan in het volledige rapport.'])
    return '\n'.join(lines) + '\n'


def run(env):
    directory = Path(env['CI_PROJECT_DIR']) / '.ci-output' / env['CI_JOB_NAME']
    path = directory / 'dependency-check-report.json'
    if not path.is_file():
        print('No Dependency-Check report; no summary to publish.')
        return
    identity = json.dumps([env['CI_PIPELINE_ID'], env['CI_JOB_NAME']])
    marker = '<!-- ci-dependency-report:' + hashlib.sha256(identity.encode()).hexdigest() + ' -->'
    body = summary(env, json.loads(path.read_text()), marker)
    (directory / 'summary.md').write_text(body)
    if not env.get('CI_MERGE_REQUEST_IID') or not env.get('GITLAB_MR_REPORT_TOKEN'):
        print('Dependency summary saved; no MR or GITLAB_MR_REPORT_TOKEN configured.')
        return
    project = env['CI_PROJECT_ID']
    if env.get('CI_MERGE_REQUEST_SOURCE_PROJECT_ID') != project:
        raise ReportError('MR reporting is limited to branches in the same project.')
    api = Api(env.get('GITLAB_REPORT_API_URL') or env['CI_API_V4_URL'], env['GITLAB_MR_REPORT_TOKEN'], 'PRIVATE-TOKEN')
    mr = api.request(f"/projects/{quote(project, safe='')}/merge_requests/{int(env['CI_MERGE_REQUEST_IID'])}")
    if mr.get('state') != 'opened' or mr.get('sha') != env['CI_COMMIT_SHA']:
        print('MR has changed or closed; outdated summary is not posted.')
        return
    result = publish_mr(api, project, env['CI_MERGE_REQUEST_IID'], body, marker)
    print(f'Dependency-Check MR summary {result}.')


def main():
    try:
        run(os.environ)
    except (ReportError, KeyError, TypeError, ValueError, OSError) as error:
        message = str(error) if isinstance(error, ReportError) else 'Missing or invalid reporting configuration or response.'
        print('Dependency reporting: ' + message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
