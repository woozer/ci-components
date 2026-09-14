#!/usr/bin/env python3
"""Configure isolated project runners for the local application and components."""
import base64
import json
import os
from pathlib import Path
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
CI = ROOT.parent.parent
PRIVATE = ROOT / "secrets"
PRIVATE.mkdir(mode=0o700, exist_ok=True)
PRIVATE.chmod(0o700)
HTTP = build_opener(ProxyHandler({}))
TOKEN = (ROOT.parent / "gitlab-ce/secrets/provisioning-token").read_text().strip()
PROJECT = json.loads((ROOT.parent / "gitlab-ce/secrets/project.json").read_text())["id"]
API_URL = "http://" + os.environ.get("DEMO_ADMIN_HOST", "127.0.0.1") + ":8929"


def project_id(name):
    records = {
        "hello-world": ROOT.parent / "gitlab-ce/secrets/project.json",
        "ci-components": ROOT.parent / "gitlab-ce/secrets/components-project.json",
        "ci-samples": PRIVATE / "samples-project.json",
    }
    return json.loads(records[name].read_text())["id"]


def save(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(value)
    path.chmod(0o600)


def api(path, method="GET", value=None):
    request = Request(API_URL + "/api/v4" + path, method=method,
                      headers={"PRIVATE-TOKEN": TOKEN, "Content-Type": "application/json"},
                      data=None if value is None else json.dumps(value).encode())
    try:
        with HTTP.open(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        # Never print a variable or runner authentication token from an API body.
        raise SystemExit(f"Local GitLab {method} {path}: HTTP {error.code}") from None


def variable(key, value, file=False, protected=False, masked=False, project=PROJECT):
    variables = api(f"/projects/{project}/variables?per_page=100")
    existing = any(item["key"] == key and item["environment_scope"] == "*" for item in variables)
    api(f"/projects/{project}/variables" + ("/" + key + "?filter%5Benvironment_scope%5D=%2A" if existing else ""),
        "PUT" if existing else "POST", {
            "key": key, "environment_scope": "*", "value": value, "variable_type": "file" if file else "env_var",
            "protected": protected, "masked": masked, "raw": True,
        })


def image_digest(name):
    result = json.loads(subprocess.check_output(["docker", "image", "inspect", name], text=True))[0]
    return result["RepoDigests"][0]


def runner_config(project, record, description, helper=None, tag="local-docker", seccomp=None):
    if not record.exists():
        runner = api("/user/runners", "POST", {
            "runner_type": "project_type", "project_id": project,
            "description": description, "tag_list": [tag],
            "run_untagged": False, "locked": True, "maximum_timeout": 3600,
        })
        save(record, json.dumps(runner))
    runner = json.loads(record.read_text())
    config = f'''
[[runners]]
  name = "{description}"
  url = "http://host.docker.internal:8929"
  clone_url = "http://host.docker.internal:8929"
  id = {runner['id']}
  token = "{runner['token']}"
  executor = "docker"
  request_concurrency = 2
  [runners.docker]
    image = "maven:3.9.12-eclipse-temurin-25"
    privileged = false
    network_mode = "kind"
    memory = "2g"
    cpus = "2"
    volumes = ["/cache"]
    pull_policy = ["always"]
'''
    if seccomp:
        config += f'    security_opt = ["seccomp={seccomp}"]\n'
    if helper:
        config += f'    helper_image = "{helper}"\n'
    print(f"Local runner {runner['id']} configured for project {project}; credentials saved privately.")
    return config


def main():
    mirrors_path = ROOT.parent / "artifactory/ci-images.json"
    mirrors = json.loads(mirrors_path.read_text()) if mirrors_path.exists() else {}
    hub_path = ROOT.parent / "artifactory/docker-hub.json"
    if hub_path.exists():
        virtual = json.loads(hub_path.read_text())["virtual_repository"]
        mirrors = {name: ref.replace("/docker-local/", f"/{virtual}/", 1)
                   for name, ref in mirrors.items()}
    config = "concurrent = 1\ncheck_interval = 3\nshutdown_timeout = 30\n"
    config += runner_config(PROJECT, PRIVATE / "runner.json",
                            "Local Docker Desktop", mirrors.get("helper"))
    if mirrors.get("buildkit"):
        save(PRIVATE / "config/buildkit-seccomp.json", (ROOT / "buildkit/seccomp.json").read_text())
        config += runner_config(PROJECT, PRIVATE / "buildkit-runner.json",
                                "Local rootless BuildKit", mirrors.get("helper"),
                                tag="local-buildkit", seccomp="/etc/gitlab-runner/buildkit-seccomp.json")
    for key, image_key in (("NODE_CI_IMAGE", "node"), ("BUILDKIT_CI_IMAGE", "buildkit"), ("BROWSER_CI_IMAGE", "browser")):
        if image_key in mirrors:
            variable(key, mirrors[image_key])
    if "nginx" in mirrors:
        variable("NGINX_RUNTIME_IMAGE", mirrors["nginx"].replace("localhost:8082", "host.docker.internal:8082"))
    variable("JAVA_CI_IMAGE", mirrors.get("java") or image_digest("maven:3.9.12-eclipse-temurin-25"))
    variable("HELM_CI_IMAGE", mirrors.get("helm") or image_digest("alpine/helm:4.2.4"))
    runtime = mirrors.get("runtime", "eclipse-temurin:25-jre@sha256:f9e65324a37f28209ce7dd0e5149a7aa954520ed936fb87813cf6ded2400a112")
    variable("JAVA_RUNTIME_IMAGE", runtime.replace("localhost:8082", "host.docker.internal:8082"))
    settings = ROOT.parent / "artifactory/secrets/maven-settings.xml"
    if settings.exists():
        variable("ARTIFACTORY_MAVEN_SETTINGS", settings.read_text(), file=True, protected=True)
        credentials = json.loads((settings.parent / "credentials.json").read_text())
        variable("ARTIFACTORY_USERNAME", credentials["publisher"]["username"], protected=True)
        variable("ARTIFACTORY_PASSWORD_FILE", credentials["publisher"]["password"], file=True, protected=True, masked=True)
    auth = settings.parent / "docker-read.json"
    if auth.exists():
        variable("DOCKER_AUTH_CONFIG", auth.read_text(), masked=True)
    kube = PRIVATE / "kubeconfig.json"
    if kube.exists():
        variable("LOCAL_KUBECONFIG", kube.read_text(), file=True, protected=True)
    components = ROOT.parent / "gitlab-ce/secrets/components-project.json"
    validation = ROOT / "validation-image.json"
    if components.exists() and validation.exists():
        component_project = json.loads(components.read_text())["id"]
        config += runner_config(component_project, PRIVATE / "components-runner.json",
                                "Local CI component validation", mirrors.get("helper"))
        variable("CI_VALIDATION_IMAGE", json.loads(validation.read_text())["image"],
                 project=component_project)
        if auth.exists():
            variable("DOCKER_AUTH_CONFIG", auth.read_text(), masked=True,
                     project=component_project)
    samples = PRIVATE / "samples-project.json"
    if samples.exists():
        sample_project = json.loads(samples.read_text())["id"]
        config += runner_config(sample_project, PRIVATE / "samples-runner.json",
                                "Local module sample validation", mirrors.get("helper"))
        config += runner_config(sample_project, PRIVATE / "samples-buildkit-runner.json",
                                "Local module sample BuildKit", mirrors.get("helper"),
                                tag="local-buildkit", seccomp="/etc/gitlab-runner/buildkit-seccomp.json")
    save(PRIVATE / "config/config.toml", config)


if __name__ == "__main__":
    main()
