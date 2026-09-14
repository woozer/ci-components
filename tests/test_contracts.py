#!/usr/bin/env python3
"""Validate YAML and exercise the contract without network or real scanners."""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUBY_YAML = '''require "yaml"; require "json"
YAML.add_domain_type("", "reference") { |_, value| {"$reference" => value} }
puts JSON.generate(ARGV.to_h { |p| [p, YAML.load_stream(File.read(p))] })'''
MODULE_FILES = sorted(ROOT.glob("templates/*.yml")) + sorted(ROOT.glob("modules/todo/*.yml"))
FILES = MODULE_FILES + sorted(ROOT.glob("config/*.yml")) + sorted(ROOT.glob("pipelines/*.yml")) + [ROOT / "examples/full-pipeline/profile.yml"] + sorted(ROOT.glob("shared/*.yml")) + [ROOT / "examples/full-pipeline/application.gitlab-ci.yml", ROOT / ".gitlab-ci.yml"]
FILES += sorted(ROOT.glob("examples/samples/*.yml")) + sorted(ROOT.glob("examples/modules/*.yml")) + sorted(ROOT.glob("tests/samples/*.yml"))
PARSED = json.loads(subprocess.check_output(["ruby", "-e", RUBY_YAML, *map(str, FILES)], text=True))
COMPONENTS = {path.stem: PARSED[str(path)] for path in MODULE_FILES}


def interpolate(documents, overrides=None):
    """Small fixture expander; GitLab CI Lint remains the authoritative validator."""
    header, body = copy.deepcopy(documents)
    inputs = {key: spec.get("default", "test-value") for key, spec in header["spec"]["inputs"].items()}
    assert not (set(overrides or {}) - inputs.keys()), "Unknown input"
    inputs.update(overrides or {})
    def substitute(value):
        if isinstance(value, dict):
            return {substitute(key): substitute(item) for key, item in value.items()}
        if isinstance(value, list):
            return [substitute(item) for item in value]
        if isinstance(value, str):
            whole = re.fullmatch(r"\$\[\[ inputs\.([a-z-]+) \]\]", value)
            if whole:
                return inputs[whole[1]]
            return re.sub(r"\$\[\[ inputs\.([a-z-]+) \]\]",
                          lambda match: str(inputs[match[1]]).lower() if isinstance(inputs[match[1]], bool)
                          else str(inputs[match[1]]), value)
        return value
    return substitute(body)


def render(name, overrides=None):
    body = interpolate(COMPONENTS[name], overrides)
    shared = {}
    for include in body.pop("include"):
        shared.update(PARSED[str(ROOT / include["local"].lstrip("/"))][0])

    def commands(value):
        if isinstance(value, dict):
            target = shared
            for key in value["$reference"]:
                target = target[key]
            return commands(target)
        if isinstance(value, list):
            return [command for item in value for command in commands(item)]
        if isinstance(value, str):
            value = re.sub(r"\$\{\{ job\.inputs\.([a-z_]+) \}\}",
                           lambda match: str(job["inputs"][match[1]]["default"]), value)
        return [value]

    job_name, job = next(iter(body.items()))
    for phase in ("before_script", "script", "after_script"):
        job[phase] = commands(job[phase])
    return job_name, job


def profile_includes(overrides=None):
    return interpolate(PARSED[str(ROOT / "examples/full-pipeline/profile.yml")], overrides)["include"]


class Harness:
    def __init__(self, root, name="maven-build", inputs=None, env=None):
        self.root = root
        self.name, self.job = render(name, inputs)
        self.env = {**os.environ, **{k: str(v) for k, v in self.job["variables"].items()},
                    "CI_PROJECT_DIR": str(root), "CI_JOB_NAME": self.name,
                    "CI_JOB_ID": "42", "CI_COMMIT_SHA": "a" * 40,
                    "CI_COMMIT_SHORT_SHA": "a" * 8, "CI_PIPELINE_ID": "99"}
        self.env.update(env or {})
        self.env["PATH"] = str(root / "bin") + os.pathsep + self.env["PATH"]
        (root / "bin").mkdir(exist_ok=True)
        self.write("mvnw", '#!/bin/sh\nprintf "core\\n" >> "$CI_PROJECT_DIR/events"\nexit "${FAKE_MAVEN_EXIT:-0}"\n')

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        target.chmod(0o755)
        return target

    def hook(self, kind, content):
        path = "hooks/" + kind + ".sh"
        self.write(path, "#!/bin/sh\nset -eu\n" + content + "\n")
        self.env["MODULE_" + kind.upper() + "_HOOK"] = path

    def run(self):
        main = "\n".join(self.job["before_script"] + self.job["script"])
        result = subprocess.run(["sh", "-c", main], cwd=self.root, env=self.env, capture_output=True, text=True)
        cleanup_env = {**self.env, "CI_JOB_STATUS": "success" if result.returncode == 0 else "failed"}
        self.cleanup = subprocess.run(["sh", "-c", "\n".join(self.job["after_script"])], cwd=self.root,
                                      env=cleanup_env, capture_output=True, text=True)
        return result

    @property
    def output_file(self):
        return self.root / ".ci-output" / self.name / "outputs.env"

    def outputs(self):
        return dict(line.split("=", 1) for line in self.output_file.read_text().splitlines())

    def events(self):
        path = self.root / "events"
        return path.read_text().splitlines() if path.exists() else []


class ComponentContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_default_input_bindings_do_not_reference_their_own_job_variable(self):
        for component in COMPONENTS:
            _, job = render(component)
            for name, value in job['variables'].items():
                with self.subTest(component=component, variable=name):
                    self.assertNotIn(value, ('$' + name, '${' + name + '}'))
            for name in job.get('inputs', {}):
                self.assertRegex(name, r'^[a-z_][a-z0-9_]*$')

    def test_pipeline_rules_do_not_depend_on_disabled_variable_inheritance(self):
        for path in ROOT.glob('pipelines/*.yml'):
            body = PARSED[str(path)][-1]
            for name, job in body.items():
                if not isinstance(job, dict) or job.get('inherit', {}).get('variables') is not False:
                    continue
                unavailable = set(body.get('variables', {})) - set(job.get('variables', {}))
                for rule in job.get('rules', []):
                    referenced = set(re.findall(r'\$([A-Z][A-Z0-9_]*)', rule.get('if', '')))
                    with self.subTest(pipeline=path.name, job=name):
                        self.assertFalse(unavailable & referenced,
                                         f'Rule reads excluded variables: {unavailable & referenced}')

    def test_every_component_is_one_job_with_an_explicit_image_and_output_contract(self):
        for name, (header, body) in COMPONENTS.items():
            with self.subTest(name=name):
                self.assertEqual({"include", "$[[ inputs.job-name ]]"}, set(body))
                self.assertNotIn("default", header["spec"]["inputs"]["image"])
                _, job = render(name)
                self.assertFalse(job["allow_failure"])
                self.assertIn("dotenv", job["artifacts"]["reports"])
                for phase in ("before_script", "script", "after_script"):
                    result = subprocess.run(["sh", "-n"], input="\n".join(job[phase]), capture_output=True, text=True)
                    self.assertEqual(0, result.returncode, result.stderr)
                for script in job["script"]:
                    for code in re.findall(r"python3 - <<'PY'\n(.*?)\nPY", script, re.S):
                        compile(code, name, "exec")

    def test_hooks_order_and_custom_output_transfer(self):
        h = Harness(self.root, inputs={"output-prefix": "SERVICE_A"})
        h.hook("pre", 'printf "pre\\n" >> "$CI_PROJECT_DIR/events"')
        h.hook("post", 'printf "post\\n" >> "$CI_PROJECT_DIR/events"\nprintf "SERVICE_A_CUSTOM_VERSION=1.2.3\\n" >> "$CI_MODULE_EXTRA_OUTPUTS"')
        h.hook("cleanup", 'printf "cleanup\\n" >> "$CI_PROJECT_DIR/events"')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["pre", "core", "post", "cleanup"], h.events())
        values = h.outputs()
        self.assertEqual("1.2.3", values["SERVICE_A_CUSTOM_VERSION"])
        self.assertEqual("passed", values["SERVICE_A_STATUS"])
        downstream = subprocess.check_output(["sh", "-c", 'printf "%s" "$SERVICE_A_CUSTOM_VERSION"'],
                                             env={**os.environ, **values}, text=True)
        self.assertEqual("1.2.3", downstream)

    def test_build_can_use_maven_installed_in_the_image(self):
        h = Harness(self.root, inputs={"maven-executable": "mvn"})
        h.write("bin/mvn", '#!/bin/sh\nprintf "installed-maven\\n" >> "$CI_PROJECT_DIR/events"\n')
        self.assertEqual(0, h.run().returncode)
        self.assertEqual(["installed-maven"], h.events())

    def test_build_runs_unit_tests_and_does_not_publish_success_after_a_test_failure(self):
        h = Harness(self.root)
        h.write('mvnw', '''#!/bin/sh
printf '%s\\n' "$@" > "$CI_PROJECT_DIR/maven-arguments"
case " $* " in
  *-Dmaven.test.skip*|*-DskipTests*|*-DskipUnitTests*) exit 0 ;;
esac
exit 1
''')
        result = h.run()
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(h.output_file.exists())
        args = (self.root / 'maven-arguments').read_text().splitlines()
        self.assertIn('package', args)
        self.assertIn('-DskipITs', args)
        self.assertEqual(['./**/target/surefire-reports/TEST-*.xml'], h.job['artifacts']['reports']['junit'])

    def test_cucumber_can_start_its_own_application_without_an_upstream_url(self):
        h = Harness(self.root, "cucumber-test", inputs={"target-url-variable": ""})
        h.write("mvnw", '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/maven-args"\n')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        args = (self.root / "maven-args").read_text().splitlines()
        self.assertIn("verify", args)
        self.assertFalse(any(arg.startswith("-P") or arg.startswith("-Dcucumber.base-url=") for arg in args))
        self.assertNotIn("CUCUMBER_TEST_TARGET_URL", h.outputs())

    def test_cucumber_accepts_an_explicit_profile_and_deployment_url(self):
        h = Harness(self.root, "cucumber-test", inputs={"profile": "acceptance"},
                    env={"HELM_DEPLOY_URL": "http://application:8080"})
        h.write("mvnw", '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/maven-args"\n')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        args = (self.root / "maven-args").read_text().splitlines()
        self.assertIn("-Pacceptance", args)
        self.assertIn("-Dcucumber.base-url=http://application:8080", args)
        self.assertEqual("http://application:8080", h.outputs()["CUCUMBER_TEST_TARGET_URL"])

    def test_jib_publishes_only_a_valid_immutable_image_reference(self):
        h = Harness(self.root, "jib-build", inputs={"image-repository": "registry.example/app",
                    "image-tag": "release-1.2.3",
                    "base-image": "registry.example/java@sha256:" + "a" * 64,
                    "allow-insecure-registry": True})
        h.write("mvnw", '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/maven-args"\n')
        h.write("target/jib-image.digest", "sha256:" + "c" * 64 + "\n")
        self.assertEqual(0, h.run().returncode)
        self.assertEqual("registry.example/app@sha256:" + "c" * 64, h.outputs()["JIB_BUILD_IMAGE_REF"])
        args = (self.root / "maven-args").read_text().splitlines()
        self.assertIn("-DsendCredentialsOverHttp=true", args)
        self.assertIn("-Djib.to.image=registry.example/app:release-1.2.3", args)
        self.assertIn("-Djib.from.image=registry.example/java@sha256:" + "a" * 64, args)
        self.assertFalse(any(arg.startswith("-Dcontainer.") for arg in args))
        h.write("target/jib-image.digest", "latest\n")
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def test_failed_chart_publication_emits_no_success_outputs(self):
        h = Harness(self.root, "helm-publish")
        h.write("bin/helm", '#!/bin/sh\nif [ "$1" = push ]; then exit 12; fi\n')
        self.assertEqual(12, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def test_maven_publication_preserves_repository_arguments_and_outputs(self):
        h = Harness(self.root, "maven-publish", inputs={"project-selector": "hello-app",
                    "settings-file": "settings file.xml", "repository-id": "gitlab-maven",
                    "repository-url": "https://gitlab.example/packages/maven"})
        h.write("mvnw", '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/maven-args"\n')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        args = (self.root / "maven-args").read_text().splitlines()
        self.assertIn("settings file.xml", args)
        self.assertIn("-DaltDeploymentRepository=gitlab-maven::https://gitlab.example/packages/maven", args)
        self.assertEqual("https://gitlab.example/packages/maven", h.outputs()["MAVEN_PUBLISH_REPOSITORY_URL"])

    def test_oci_deployment_uses_published_version_and_scoped_kubeconfig(self):
        h = Harness(self.root, "helm-deploy", inputs={"image-ref-variable": "IMAGE_VERIFY_IMAGE_REF", "chart-variable": "CHART_REF",
                    "chart-version-variable": "CHART_VERSION", "kubeconfig-variable": "LOCAL_KUBECONFIG",
                    "create-namespace": False, "plain-http": True},
                    env={"IMAGE_VERIFY_IMAGE_REF": "registry.example/app@sha256:" + "d" * 64,
                         "CHART_REF": "oci://registry.example/charts/app", "CHART_VERSION": "1.2.3",
                         "LOCAL_KUBECONFIG": str(self.root / "kubeconfig")})
        h.write("kubeconfig", "test configuration")
        h.write("bin/helm", '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/helm-args"\n')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        args = (self.root / "helm-args").read_text().splitlines()
        self.assertEqual("upgrade", args[0])
        self.assertIn("1.2.3", args)
        self.assertIn("--plain-http", args)
        self.assertIn(str(self.root / "kubeconfig"), args)
        self.assertNotIn("--create-namespace", args)

    def test_pre_failure_prevents_operation_and_outputs(self):
        h = Harness(self.root)
        h.hook("pre", "exit 4")
        h.hook("cleanup", 'printf "cleanup\\n" >> "$CI_PROJECT_DIR/events"')
        self.assertNotEqual(0, h.run().returncode)
        self.assertEqual(["cleanup"], h.events())
        self.assertFalse(h.output_file.exists())

    def test_operation_failure_skips_post_but_runs_cleanup(self):
        h = Harness(self.root, env={"FAKE_MAVEN_EXIT": "7"})
        h.hook("post", 'printf "post\\n" >> "$CI_PROJECT_DIR/events"')
        h.hook("cleanup", 'printf "cleanup\\n" >> "$CI_PROJECT_DIR/events"')
        self.assertEqual(7, h.run().returncode)
        self.assertEqual(["core", "cleanup"], h.events())
        self.assertFalse(h.output_file.exists())

    def test_post_failure_prevents_success_outputs(self):
        h = Harness(self.root)
        h.hook("post", "exit 8")
        self.assertEqual(8, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def test_cleanup_failure_does_not_change_operation_exit_status(self):
        h = Harness(self.root)
        h.hook("cleanup", "exit 9")
        self.assertEqual(0, h.run().returncode)
        self.assertEqual(9, h.cleanup.returncode)
        self.assertEqual("passed", h.outputs()["MAVEN_BUILD_STATUS"])

    def test_image_build_removes_credentials_before_shared_cleanup_on_failure(self):
        h = Harness(self.root, "image-build")
        credentials = h.write(".ci-tmp/42/config.json", "temporary test credential")
        h.hook("pre", "exit 4")
        h.hook("cleanup", 'test ! -f "$CI_PROJECT_DIR/.ci-tmp/$CI_JOB_ID/config.json"\n'
               'printf "cleanup\\n" >> "$CI_PROJECT_DIR/events"')
        self.assertEqual(4, h.run().returncode)
        self.assertFalse(credentials.exists())
        self.assertEqual(0, h.cleanup.returncode)
        self.assertEqual(["cleanup"], h.events())
        self.assertFalse(h.output_file.exists())

    def test_image_build_publishes_artifactory_digest_and_cleans_auth(self):
        h = Harness(self.root, "image-build", inputs={
            "image-repository": "registry.invalid/dev/ui", "image-tag": "1.2.3",
            "registry": "registry.invalid", "registry-username": "publisher",
            "registry-password-file": str(self.root / "password"),
            "plain-http": True, "base-image": "registry.invalid/base/nginx@sha256:" + "a" * 64,
        })
        # Runtime GitLab boolean inputs are lowercase strings.
        h.env['BUILD_PLAIN_HTTP'] = 'true'
        h.env['DOCKER_AUTH_CONFIG'] = json.dumps({'auths': {'base.invalid': {'auth': 'read-only-fixture'}}})
        h.write("password", "test-secret")
        h.write("bin/buildctl-daemonless.sh", """#!/bin/sh
set -eu
printf '%s\\n' "$*" > "$CI_PROJECT_DIR/buildkit-args"
python3 - <<'PYTHON'
import json, os, pathlib
config = pathlib.Path(os.environ['DOCKER_CONFIG'])
assert 'DOCKER_AUTH_CONFIG' not in os.environ
assert json.loads((config / 'config.json').read_text())['auths']['registry.invalid']['password'] == 'test-secret'
assert json.loads((config / 'config.json').read_text())['auths']['base.invalid']['auth'] == 'read-only-fixture'
assert 'http = true' in (config / 'buildkitd.toml').read_text()
output = pathlib.Path(os.environ['CI_MODULE_OUTPUT_DIR'])
(output / 'build-metadata.json').write_text(json.dumps({'containerimage.digest': 'sha256:' + 'b' * 64}))
PYTHON
""")
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('registry.invalid/dev/ui@sha256:' + 'b' * 64, h.outputs()['IMAGE_BUILD_IMAGE_REF'])
        args = (self.root / 'buildkit-args').read_text()
        self.assertIn('name=registry.invalid/dev/ui:1.2.3,push=true,registry.insecure=true', args)
        self.assertIn('build-arg:BASE_IMAGE=registry.invalid/base/nginx@sha256:', args)
        self.assertNotIn('test-secret', args + result.stdout + h.output_file.read_text())
        self.assertFalse((self.root / '.ci-tmp/42/config.json').exists())

    def test_duplicate_custom_outputs_are_rejected(self):
        h = Harness(self.root)
        h.hook("post", 'printf "MAVEN_BUILD_CUSTOM_A=one\\nMAVEN_BUILD_CUSTOM_A=two\\n" > "$CI_MODULE_EXTRA_OUTPUTS"')
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def test_custom_hook_cannot_replace_builtin_output(self):
        h = Harness(self.root)
        h.hook("post", 'printf "MAVEN_BUILD_STATUS=passed\\n" > "$CI_MODULE_EXTRA_OUTPUTS"')
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def test_missing_output_and_mutable_image_tag_are_rejected(self):
        for value in (None, "registry.example.com/app:latest"):
            with self.subTest(value=value):
                env = {"COSIGN_PUBLIC_KEY": "approved.pub"}
                if value:
                    env["IMAGE_SIGN_IMAGE_REF"] = value
                h = Harness(self.root, "image-verify", env=env)
                h.write("bin/cosign", "#!/bin/sh\nexit 0\n")
                self.assertNotEqual(0, h.run().returncode)
                self.assertFalse(h.output_file.exists())

    def test_deployment_passes_same_digest_and_url_to_next_stage(self):
        image_ref = "registry.example.com/app@sha256:" + "b" * 64
        h = Harness(self.root, "helm-deploy", inputs={"image-ref-variable": "IMAGE_VERIFY_IMAGE_REF", "chart": "helm/app", "values-file": "helm/test.yaml",
                    "namespace": "pipeline-99", "release": "app", "environment": "test/99",
                    "target-url": "https://99.test.example.com", "output-prefix": "TEST_DEPLOY"},
                    env={"IMAGE_VERIFY_IMAGE_REF": image_ref, "KUBE_CONTEXT": "test-agent"})
        h.write("bin/kubectl", '#!/bin/sh\nprintf "%s\\n" "$@" >> "$CI_PROJECT_DIR/kube-args"\n')
        h.write("bin/helm", '#!/bin/sh\nprintf "%s\\n" "$@" >> "$CI_PROJECT_DIR/helm-args"\n')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(image_ref, h.outputs()["TEST_DEPLOY_IMAGE_REF"])
        self.assertEqual("https://99.test.example.com", h.outputs()["TEST_DEPLOY_URL"])
        self.assertIn("--rollback-on-failure", (self.root / "helm-args").read_text())
        self.assertIn("image.digest=sha256:" + "b" * 64, (self.root / "helm-args").read_text())

    def test_helm_user_values_follow_cluster_values_and_image_digest_stays_final(self):
        image_ref = 'registry.example.com/app@sha256:' + 'b' * 64
        h = Harness(self.root, 'helm-deploy', inputs={
            'image-ref-variable': 'IMAGE_VERIFY_IMAGE_REF',
            'chart': 'helm/app', 'values-file': 'environment/cluster/local.yaml',
            'override-values-file': 'environment/user/two-replicas.yaml'},
            env={'IMAGE_VERIFY_IMAGE_REF': image_ref, 'KUBE_CONTEXT': 'local'})
        h.write('bin/helm', '#!/bin/sh\nprintf "%s\\n" "$@" >> "$CI_PROJECT_DIR/helm-args"\n')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        args = (self.root / 'helm-args').read_text().splitlines()
        values = [args[i+1] for i, arg in enumerate(args) if arg == '--values']
        self.assertEqual(['environment/cluster/local.yaml', 'environment/user/two-replicas.yaml'], values)
        self.assertGreater(args.index('image.digest=sha256:' + 'b' * 64), args.index(values[-1]))

    def test_failed_helm_wait_does_not_publish_success_or_run_post_hook(self):
        for major in (3, 4):
            with self.subTest(helm=major), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                h = Harness(root, 'helm-deploy', inputs={
                    'image-ref-variable': 'IMAGE_VERIFY_IMAGE_REF',
                    'chart': 'oci://registry.example/charts/app', 'timeout': '25s',
                    'helm-major': major}, env={
                    'IMAGE_VERIFY_IMAGE_REF': 'registry.example/app@sha256:' + 'b' * 64,
                    'KUBE_CONTEXT': 'local'})
                h.write('bin/helm', '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/helm-args"\nexit 1\n')
                h.hook('post', 'echo post >> "$CI_PROJECT_DIR/events"')
                self.assertNotEqual(0, h.run().returncode)
                args = (root / 'helm-args').read_text().splitlines()
                self.assertEqual('25s', args[args.index('--timeout') + 1])
                self.assertIn('--wait' if major == 3 else '--wait=watcher', args)
                self.assertFalse(h.output_file.exists())
                self.assertEqual([], h.events())

    def test_deployed_integration_suites_wait_for_every_deployable(self):
        body = interpolate(PARSED[str(ROOT / 'pipelines/java-service.yml')],
                           {'deployment-timeout': '8m'})
        for name in ('cucumber-dev', 'cucumber-ui'):
            needs = {need['job']: need for need in body[name]['needs']}
            self.assertEqual({'helm-deploy', 'helm-deploy-ui'}, set(needs))
            self.assertFalse(needs['helm-deploy'].get('optional', False))
        self.assertTrue(body['cucumber-dev']['needs'][1]['optional'])
        for include in body['include']:
            if include['local'] == '/templates/helm-deploy.yml':
                self.assertEqual('8m', include['inputs']['timeout'])
            if include['local'] in ('/templates/deployment-select.yml', '/templates/release-reserve.yml'):
                self.assertIn("deployment-timeout: '8m'", include['inputs']['pipeline-config'])

    def test_selection_defaults_emit_settings_and_bind_the_next_pipeline(self):
        h = Harness(self.root, 'deployment-select', inputs={
            'pipeline-config': 'cluster: @CLUSTER@\nuser: @USER_CONFIG@'})
        self.assertEqual('delayed', h.job['rules'][0]['when'])
        self.assertEqual('10 seconds', h.job['rules'][0]['start_in'])
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('local', h.outputs()['SELECTION_CLUSTER'])
        self.assertEqual('cluster: local\nuser: default\n',
                         (h.output_file.parent / 'pipeline.yml').read_text())

    def test_pipeline_form_selections_become_the_deployment_job_defaults(self):
        h = Harness(self.root, 'deployment-select', inputs={
            'default-user-config': 'two-replicas',
            'pipeline-config': 'user: @USER_CONFIG@'})
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('two-replicas', h.outputs()['SELECTION_USER_CONFIG'])
        self.assertEqual('user: two-replicas\n', (h.output_file.parent / 'pipeline.yml').read_text())

    def test_deployment_selection_rejects_paths_before_publishing(self):
        h = Harness(self.root, 'deployment-select', inputs={
            'default-user-config': '../secret', 'pipeline-config': 'user: @USER_CONFIG@'})
        self.assertNotEqual(0, h.run().returncode)
        self.assertFalse(h.output_file.exists())

    def test_cucumber_records_the_actual_selection_with_the_result(self):
        h = Harness(self.root, 'cucumber-test', inputs={
            'tags': '@smoke', 'profile': 'integration', 'target-url-variable': ''})
        h.write('mvnw', '#!/bin/sh\nprintf "%s\\n" "$@" > "$CI_PROJECT_DIR/maven-args"\n')
        result = h.run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('@smoke', h.outputs()['CUCUMBER_TEST_TAGS'])
        self.assertEqual('integration', h.outputs()['CUCUMBER_TEST_PROFILE'])
        args = (self.root / 'maven-args').read_text().splitlines()
        self.assertIn('-Dcucumber.filter.tags=@smoke', args)
        self.assertIn('-Pintegration', args)

    def test_example_production_depends_on_all_required_checks(self):
        example = PARSED[str(ROOT / "examples/full-pipeline/application.gitlab-ci.yml")][0]
        profile = example["include"][0]
        self.assertEqual("/examples/full-pipeline/profile.yml", profile["file"])
        required = {key for key, spec in PARSED[str(ROOT / "examples/full-pipeline/profile.yml")][0]["spec"]["inputs"].items()
                    if "default" not in spec}
        self.assertTrue(required <= profile["inputs"].keys())
        includes = {}
        prefixes = set()
        for item in profile_includes(profile["inputs"]):
            component = Path(item["local"]).stem
            name, job = render(component, item["inputs"])
            self.assertNotIn(name, includes)
            includes[name] = job
            prefix = job["variables"]["MODULE_OUTPUT_PREFIX"]
            self.assertNotIn(prefix, prefixes)
            prefixes.add(prefix)
            self.assertIn(job["stage"], example["stages"])
            required = {key for key, spec in COMPONENTS[component][0]["spec"]["inputs"].items() if "default" not in spec}
            self.assertTrue(required <= item["inputs"].keys())
        def ancestors(name, visiting=None):
            visiting = set(visiting or ())
            self.assertNotIn(name, visiting, "Dependency cycle")
            visiting.add(name)
            result = set()
            for edge in example.get(name, {}).get("needs", []):
                self.assertFalse(edge.get("optional", False))
                self.assertIn(edge["job"], includes)
                result.add(edge["job"])
                result |= ancestors(edge["job"], visiting)
            return result
        self.assertEqual(set(includes) - {"deploy-production"}, ancestors("deploy-production"))
        self.assertFalse(example["deploy-production"]["allow_failure"])
        self.assertEqual("manual", example["deploy-production"]["when"])

    def test_modules_keep_standalone_defaults_and_accept_explicit_overrides(self):
        for component in COMPONENTS:
            with self.subTest(component=component):
                _, default = render(component)
                self.assertEqual({"dependency-check": "1h", "fortify": "2h"}.get(component, "30m"), default["timeout"])
                self.assertEqual("7 days", default["artifacts"]["expire_in"])
                _, changed = render(component, {"job-timeout": "45m", "artifact-expire-in": "30 days"})
                self.assertEqual("45m", changed["timeout"])
                self.assertEqual("30 days", changed["artifacts"]["expire_in"])

    def test_profile_passes_overrides_without_affecting_other_images_or_owning_order(self):
        image_ref = "registry.example.com/maven@sha256:" + "a" * 64
        jobs = dict(render(Path(item["local"]).stem, item["inputs"]) for item in profile_includes({
            "maven-build-image": image_ref, "maven-directory": "service", "npm-directory": "web",
            "job-timeout": "45m", "artifact-expire-in": "30 days", "dependency-check-fail-cvss": 9,
        }))
        self.assertEqual(15, len(jobs))
        self.assertEqual(image_ref, jobs["maven-build"]["image"]["name"])
        self.assertEqual("$NPM_BUILD_IMAGE", jobs["npm-build"]["image"]["name"])
        self.assertEqual("service", jobs["maven-build"]["variables"]["MODULE_WORKDIR"])
        self.assertEqual("web", jobs["npm-test"]["variables"]["MODULE_WORKDIR"])
        self.assertEqual("45m", jobs["maven-build"]["timeout"])
        self.assertEqual("1h", jobs["dependency-check"]["timeout"])
        self.assertEqual("2h", jobs["fortify"]["timeout"])
        self.assertEqual(9, next(item["inputs"]["fail-cvss"] for item in profile_includes({"dependency-check-fail-cvss": 9})
                                 if item["local"] == "/templates/dependency-check.yml"))
        self.assertEqual({"include"}, set(PARSED[str(ROOT / "examples/full-pipeline/profile.yml")][1]))
        for job in jobs.values():
            self.assertNotIn("needs", job)
            self.assertEqual("30 days", job["artifacts"]["expire_in"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
