# Application and platform setup

## Dedicated images

There is no global image and no shared image required across components. Every module's `image` input is mandatory. The optional organization profile supplies separate image-variable defaults and allows explicit input overrides; images may be reused when tool requirements match. Set each variable to your approved image pinned with `@sha256:<64 hexadecimal characters>`. See [defaults and profiles](defaults.md) for configuration ownership. The repository validation job has its own image variable outside that profile.

| Example variable | Required contents |
|---|---|
| `MAVEN_BUILD_IMAGE` | Approved JDK, Maven Wrapper prerequisites, `sh` |
| `MAVEN_TEST_IMAGE` | Matching JDK and Maven Wrapper prerequisites, `sh` |
| `NPM_BUILD_IMAGE` | Approved Node.js and npm, `sh` |
| `NPM_TEST_IMAGE` | Node/npm and browser libraries if the selected test runner needs them |
| `SONAR_SCANNER_IMAGE` | JDK, Maven Wrapper prerequisites, Git; Node if required by your JS/TS analysis setup |
| `SONAR_GATE_IMAGE` | Python 3, CA certificates, `sh` |
| `DEPENDENCY_CHECK_IMAGE` | JDK compatible with the approved plugin, Maven Wrapper prerequisites |
| `NPM_AUDIT_IMAGE` | Node/npm, `sh` |
| `FORTIFY_SCAN_IMAGE` | Licensed scanner/client for your Fortify edition, language prerequisites, Python 3, `sh` |
| `FORTIFY_GATE_IMAGE` | Fortify policy client, Python 3, `sh` |
| `IMAGE_BUILD_IMAGE` | Rootless BuildKit including `buildctl-daemonless.sh`, Python 3, `sh` |
| `IMAGE_SCAN_IMAGE` | Trivy, CA certificates, `sh` |
| `SBOM_IMAGE` | Trivy, CA certificates, `sh` |
| `IMAGE_SIGN_IMAGE` | Cosign, KMS authentication support, CA certificates, `sh` |
| `IMAGE_VERIFY_IMAGE` | Cosign, CA certificates, `sh` |
| `HELM_TEST_IMAGE` | Selected Helm major version, kubectl, CA certificates, `sh` |
| `HELM_PRODUCTION_IMAGE` | Selected Helm major version, kubectl, CA certificates, `sh` |
| `CUCUMBER_IMAGE` | JDK, Maven Wrapper prerequisites, browser libraries if the suite requires them |
| `ZAP_IMAGE` | ZAP's packaged `zap-baseline.py`, writable `/zap/wrk`, `sh` |
| `CI_VALIDATION_IMAGE` | Python 3, Ruby with standard YAML library, `sh`; used only by this component repository |

All images also need basic POSIX utilities (`awk`, `grep`, `wc`, `printenv`, `cat`, `cp`, `mv`, `rm`, `mkdir`). Minimal/distroless upstream images may need a small internal wrapper image to add the shell. No image needs tools for unrelated building blocks. Bake tools into maintained images instead of downloading arbitrary binaries in hooks.

Use matching Java/Node versions across build and test images. Configure internal CA certificates, registry access, and proxies. Rootless BuildKit still needs a runner permitting its required user namespace/mount system calls; validate that with your runner team. [GitLab BuildKit setup](https://docs.gitlab.com/ci/docker/using_buildkit/)

## Service configuration

- Set `SONAR_HOST_URL` to HTTPS, `SONAR_PROJECT_KEY`, and a scoped `SONAR_TOKEN`; select an exact `SONAR_MAVEN_PLUGIN_VERSION`. The scan job exports its CE task metadata. The gate waits on that task and queries the resulting analysis ID, not the latest project analysis. [Sonar analysis and quality gates](https://docs.sonarsource.com/sonarqube-cloud/advanced-setup/ci-based-analysis/gitlab-ci)
- Select an exact `DEPENDENCY_CHECK_PLUGIN_VERSION` and provide `NVD_API_KEY` securely. The plugin reads the key by environment-variable name. Configure your central feed cache, freshness checks, and suppression policy before scaling to many concurrent projects.
- Configure Fortify through the adapters in `fortify-adapters.md`; the scan and gate credentials should have only their required privileges.
- Enable the GitLab container registry. Configure registry authentication for Trivy/Cosign through their supported credentials or a pre-hook. The BuildKit component creates its own ephemeral registry config using the GitLab job credential and removes it in `after_script`; it is outside the artifact directory.
- Set `COSIGN_KEY_URI` to the approved KMS URI and obtain short-lived KMS credentials for the sign job. Set `COSIGN_PUBLIC_KEY` to an approved public-key file or verification URI. Configure the transparency log/trust arrangement appropriate for the organization. The starter signs images; Maven repository publishing may also require a separate detached GPG signing/publish component, depending on the repository's contract.
- Set `KUBE_CONTEXT` using environment-scoped variables for test and production. Use the GitLab Kubernetes agent or a pre-hook that obtains a short-lived kubeconfig. Configure namespace-scoped RBAC. A platform controller can pre-create namespaces when application jobs should not have that permission; set the `helm-deploy` input `create-namespace: false`. A file variable can be selected with `kubeconfig-variable`, without requiring a context override.
- Configure protected environments, approvals, and authorized production deployers. The example's manual job is a pipeline pause; actual approval/authorization policies are GitLab settings and depend on your edition.

## Maven and npm contracts

By default, Maven components use an executable Maven Wrapper in the configured working directory. `maven-build`, `maven-publish`, `jib-build`, and `cucumber-test` also accept `maven-executable: mvn` to use Maven installed in the approved image. Commit its version and checksum configuration. Pin Surefire, Failsafe, JaCoCo, and scanner plugin versions in your parent POM or component inputs.

`ci-unit` must activate JaCoCo's `prepare-agent` before tests and configure Surefire. The test component runs `test jacoco:report`; make the report XML available to Sonar. `sonar-scan` preserves imported coverage artifacts and installs reactor artifacts with tests skipped to resolve multi-module dependencies. These preparation phases may compile/package again; the release OCI image is still built only once from the build jobs' artifacts.

Configure the POM to bind Failsafe's `integration-test` and `verify` goals, discover a real Cucumber test suite, write JUnit XML to `target/failsafe-reports`, and read `cucumber.base-url` in application test code. Configure Surefire's `skipTests` from a custom `skipUnitTests` property; do not set global `skipTests` for Cucumber because that can skip Failsafe too. Fail the suite if its configured tag filter selects no scenarios. Java multi-module projects with intentionally testless modules need a reviewed per-module discovery configuration. [Cucumber with Failsafe](https://maven.apache.org/components/surefire/maven-failsafe-plugin/examples/cucumber.html)

Cucumber activates no Maven profile by default. If Failsafe is configured in a profile, pass its name explicitly, for example `profile: cucumber-ci`. The optional full pipeline example selects that profile explicitly. Set `target-url-variable: ""` when the test suite starts its own application; otherwise pass the name of a URL output from an upstream deployment.

`package-lock.json` and the approved npm configuration must be committed. `build` must write the configured output directory (`dist` by default). `test:ci` must run non-interactively, fail when no tests are discovered, produce `reports/junit.xml`, and write `coverage/lcov.info` if Sonar consumes JavaScript/TypeScript coverage. The npm build, test, and audit components each install their own dependencies from the same lockfile.

The Sonar scan in this starter uses the Maven scanner. Configure the application's POM/Sonar project to include the frontend sources and imported LCOV if Java and npm are one analyzed project. For independently analyzed frontend projects, use a dedicated Sonar CLI component with the same output contract and give its gate a unique task-variable input and output prefix.

## Deployment contract

For Java applications using Jib, select `jib-build`, supply a digest-pinned base image and registry Maven settings, and consume its `IMAGE_REF` output. The component uses Jib’s standard `jib.to.image` and `jib.from.image` properties; it does not require application-specific image properties in the POM. Registry HTTP requires an explicit opt-in for the local lab. `maven-publish` handles Maven repository deployment independently.

When using the general `image-build` component, the Dockerfile should copy `backend/**/target` artifacts and `frontend/dist` from the producer jobs instead of fetching unversioned build outputs. Pin base images. Put downloaded caches, credentials, and unrelated files in `.dockerignore`.

`helm-publish` packages a versioned chart and publishes it to an OCI repository. Pass its `REF` and `VERSION` outputs to `helm-deploy` through `chart-variable` and `chart-version-variable`. A registry login hook runs in each Helm job that needs authentication. `plain-http` defaults to false.

Commit `Chart.lock` for dependency reproducibility. The chart must render the exact repository and digest passed by the component:

```yaml
# Helm template fragment inside the chart's container definition
image: "{{ .Values.image.repository }}@{{ required \"image.digest is required\" .Values.image.digest }}"
```

Supply values files that configure the ingress host to match `target-url`; the component cannot infer a chart-specific ingress field. Configure readiness probes and service dependencies. The default Helm major is 4; set `helm-major: 3` for a Helm 3 image. The flags differ: Helm 4 uses `--rollback-on-failure`, while Helm 3 uses `--atomic`. [Helm 4 upgrade](https://docs.helm.sh/docs/helm/helm_upgrade/), [Helm 3 upgrade](https://docs.helm.sh/docs/v3/helm/helm_upgrade/)

The consumer example uses a unique test namespace and URL per pipeline so another deployment cannot replace the application while Cucumber and ZAP run. Install an expiry controller or schedule cleanup for these namespaces. A job-level `resource_group` only serializes individual deployments; it does not protect a shared environment across subsequent test jobs.

Provide a reviewed `ci/zap/rules.tsv`. By default ZAP baseline uses passive checks and reports findings as warnings; this starter blocks exit statuses 1, 2, and 3. Use explicit, reviewed rule exceptions. Add authenticated active/API scans as separate components when required. [ZAP baseline behavior](https://www.zaproxy.org/docs/docker/baseline-scan/)

Production imports the same digest output from the test deployment and waits for both integration checks. Configure admission signature verification and prevent stale pipeline deployments in GitLab; review any rollback as a separate deployment decision. Retain release evidence in durable storage for your required audit period: the component artifact default is seven days and should be overridden for release evidence.

## Extending a module

Copy example hooks into the consuming application repository, then pass their paths:

```yaml
include:
  - component: $CI_SERVER_FQDN/platform/ci-components/maven-build@REPLACE_WITH_COMMIT_SHA
    inputs:
      image: $MAVEN_BUILD_IMAGE
      working-directory: backend
      output-prefix: SERVICE_A_BUILD
      pre-hook: ci/hooks/pre-build.sh
      post-hook: ci/hooks/post-build.sh
      cleanup-hook: ci/hooks/cleanup.sh
```

The sample post hook exports `SERVICE_A_BUILD_CUSTOM_BUILD_LABEL`. A downstream job with an artifact-enabled `needs` edge can read it along with the built-in outputs. Custom output keys must begin with `<PREFIX>_CUSTOM_`, values must be nonempty single lines, and the total dotenv file must remain within 5 KB. Keep the number of inherited variables within your instance's dotenv limit. Use a JSON artifact for large or structured output.
