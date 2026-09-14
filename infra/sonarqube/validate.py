#!/usr/bin/env python3
"""Run the actual scanner component against an isolated local application checkout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from test_contracts import render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scanner', choices=['sonar', 'dependency-check'])
    args = parser.parse_args()
    scratch = ROOT / '.ci-tmp' / 'scanner-validation'
    scratch.mkdir(parents=True, exist_ok=True)
    checkout = scratch / 'application'
    if not checkout.exists():
        subprocess.run(['git', 'clone', '--no-hardlinks', '--branch', 'main',
                        str(ROOT / 'java'), str(checkout)], check=True)
    sha = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    images = json.loads((ROOT / 'infra/artifactory/ci-images.json').read_text())
    image = images['sonar' if args.scanner == 'sonar' else 'java']
    inputs = {'maven-executable': 'mvn', 'image': image}
    if args.scanner == 'dependency-check':
        inputs['nvd-datafeed-url'] = 'https://dependency-check.github.io/DependencyCheck_Builder/nvd_cache/nvdcve-{0}.json.gz'
    name, job = render(args.scanner, inputs)
    script = scratch / (name + '.sh')
    script.write_text('\n'.join(job['before_script'] + job['script']) + '\n')
    cache = scratch / 'maven'
    cache.mkdir(exist_ok=True)
    environment = {**job['variables'], 'CI_PROJECT_DIR': '/workspace', 'CI_JOB_NAME': name,
                   'CI_COMMIT_SHA': sha, 'CI_PIPELINE_ID': 'local-validation',
                   'MAVEN_OPTS': '-Dmaven.repo.local=/cache/repository'}
    if args.scanner == 'sonar':
        environment.update({'SONAR_HOST_URL': 'http://sonarqube:9000', 'SONAR_PROJECT_KEY': 'hello-world',
            'SONAR_USER_HOME': '/workspace/.sonar',
            'SONAR_TOKEN': (ROOT / 'infra/sonarqube/secrets/gitlab-analysis-token').read_text().strip(),
            'MAVEN_ARGS': '-Dsonar.maven.scanAll=true -Dsonar.exclusions=**/node_modules/**,**/dist/**,.ci-output/**,.cache/**,.sonar/**'})
    env_file = ROOT / 'infra/sonarqube/secrets/validation.env'
    with os.fdopen(os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
        stream.write(''.join(f'{key}={value}\n' for key, value in environment.items()))
    try:
        log_path = scratch / (name + '.log')
        print('Running', name, '; log:', log_path, flush=True)
        command = ['docker', 'run', '--rm', '--name', 'organization-' + name + '-validation',
            '--network', 'kind', '--cpus', '2', '--memory', '2g', '--env-file', str(env_file),
            '--mount', f'type=bind,src={checkout},dst=/workspace',
            '--mount', f'type=bind,src={cache},dst=/cache',
            '--mount', f'type=bind,src={script},dst=/ci/scan.sh,readonly',
            '-w', '/workspace', '--entrypoint', 'sh', image, '/ci/scan.sh']
        with log_path.open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        print(name, 'exit code:', result.returncode, '; log:', log_path, flush=True)
        raise SystemExit(result.returncode)
    finally:
        env_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
