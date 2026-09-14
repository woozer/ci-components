"""Build and publish native CI images using ordinary Docker commands."""
import base64
import re
from urllib.request import Request

from common import HTTP, INFRA, announce, docker_architecture, load_json, local_url, run, save_json

MAVEN = 'maven:3.9.12-eclipse-temurin-25@sha256:4f82a03a7d6679281952d628131299b1be88d7030a49c6a2b7d2ba2642e44e3e'
NODE = 'node:24-bookworm-slim@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553'
PUBLIC_IMAGES = {
    'node': (NODE, 'ci/node:24'),
    'nginx': ('nginxinc/nginx-unprivileged:stable-alpine@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce', 'base/nginx:stable-alpine'),
    'helm': ('alpine/helm:4.2.4', 'ci/helm:4.2.4'),
    'runtime': ('eclipse-temurin:25-jre@sha256:f9e65324a37f28209ce7dd0e5149a7aa954520ed936fb87813cf6ded2400a112', 'base/java:25-jre'),
    'sonarqube': ('sonarqube:26.9.0.129388-community', 'services/sonarqube:26.9.0.129388'),
    'postgres': ('postgres:17', 'services/postgres:17'),
}


def helper_image(arch):
    prefix = {'arm64': 'arm64', 'amd64': 'x86_64'}[arch]
    return f'gitlab/gitlab-runner-helper:{prefix}-v19.3.0'


def manifest_digest(suffix, auth):
    name, tag = suffix.rsplit(':', 1)
    request = Request(local_url(8082, f'/v2/docker-local/{name}/manifests/{tag}'), method='HEAD',
        headers={'Authorization': 'Basic ' + auth,
                 'Accept': 'application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
    with HTTP.open(request, timeout=30) as response:
        digest = response.headers.get('Docker-Content-Digest', '')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
        raise RuntimeError('Artifactory did not return a published image digest.')
    return f'localhost:8082/docker-local/{name}@{digest}'


def build_and_publish():
    arch = docker_architecture()
    platform = 'linux/' + arch
    credentials = load_json(INFRA / 'artifactory/secrets/credentials.json')['publisher']
    auth = base64.b64encode(f"{credentials['username']}:{credentials['password']}".encode()).decode()
    config = INFRA / 'artifactory/secrets/docker-publisher'
    save_json(config / 'config.json', {'auths': {'localhost:8082': {'auth': auth}}})
    docker = ['docker', '--config', config]
    references = {}

    def publish(key, source, suffix):
        target = 'localhost:8082/docker-local/' + suffix
        run([*docker, 'tag', source, target])
        run([*docker, 'push', '--quiet', '--platform', platform, target], capture=True)
        references[key] = manifest_digest(suffix, auth)
        save_json(INFRA / 'artifactory/ci-images.json', references)
        announce(f'Published {key} for {platform}.')

    sources = {**PUBLIC_IMAGES, 'helper': (helper_image(arch), f'ci/runner-helper:{arch}-v19.3.0')}
    for key, (source, suffix) in sources.items():
        run([*docker, 'pull', '--quiet', '--platform', platform, source], capture=True)
        publish(key, source, suffix)

    builds = [
        ('java', 'gitlab-runner/maven', 'ci-maven:local', 'ci/maven:3.9.12-java25-wrapper', {'MAVEN_IMAGE': MAVEN}),
        ('browser', 'gitlab-runner/browser', 'ci-browser:local', 'ci/browser:playwright1.62-java25', {}),
        ('buildkit', 'gitlab-runner/buildkit', 'ci-buildkit:local', 'ci/buildkit:rootless', {}),
        ('validation', 'gitlab-runner/validation-image', 'ci-validation:local', 'ci/validation:python-ruby-git', {}),
        ('sonar', 'sonarqube', 'ci-sonar:local', 'ci/sonar:maven-java25-node24', {'MAVEN_IMAGE': 'ci-maven:local', 'NODE_IMAGE': NODE}),
    ]
    for key, directory, source, suffix, arguments in builds:
        args = [*docker, 'build', '--platform', platform, '--tag', source]
        for name, value in arguments.items():
            args += ['--build-arg', f'{name}={value}']
        run([*args, INFRA / directory])
        publish(key, source, suffix)
    save_json(INFRA / 'gitlab-runner/validation-image.json', {'image': references['validation']})
    return references
