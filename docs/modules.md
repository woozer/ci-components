# Make your own pipeline

Include only the modules you need. Your `.gitlab-ci.yml` owns stages, job dependencies, conditions and additional jobs. No organization profile or standard Java pipeline is required. Every module has its own image and outputs; shared hook handling is included automatically.

## Choose a module

Each example is real YAML declaring the required stage and including one module. Set its required library revision, provide the image and runtime prerequisites, and adapt the application paths. Complete input types/defaults live in the linked module's `spec:inputs`; inputs without a default are required. See [required inputs](inputs.md).

| Module | Minimal example | Runtime prerequisites |
|---|---|---|
| [maven-build](../templates/maven-build.yml) | [YAML](../examples/modules/maven-build.yml) | POM, Java/Maven image; packages with tests skipped |
| [cucumber-test](../templates/cucumber-test.yml) | [YAML](../examples/modules/cucumber-test.yml) | Cucumber/Failsafe tests; this example starts its own application |
| [npm-build](../templates/npm-build.yml) | [YAML](../examples/modules/npm-build.yml) | Lockfile and `build` script in `ui/` |
| [npm-test](../templates/npm-test.yml) | [YAML](../examples/modules/npm-test.yml) | Lockfile and `test:ci` script producing `reports/junit.xml` |
| [maven-publish](../templates/maven-publish.yml) | [YAML](../examples/modules/maven-publish.yml) | Repository URL and authenticated Maven settings file |
| [jib-build](../templates/jib-build.yml) | [YAML](../examples/modules/jib-build.yml) | Jib plugin, registry Maven settings, target repository, digest-pinned Java base |
| [image-build](../templates/image-build.yml) | [YAML](../examples/modules/image-build.yml) | Dockerfile, suitable rootless BuildKit runner; defaults to GitLab Registry credentials |
| [helm-publish](../templates/helm-publish.yml) | [YAML](../examples/modules/helm-publish.yml) | Chart, SemVer, OCI repository and registry login |
| [helm-deploy](../templates/helm-deploy.yml) | [YAML](../examples/modules/helm-deploy.yml) | Image digest, chart reference/version, values, kubeconfig, target URL and registry login |
| [deployment-select](../templates/deployment-select.yml) | [YAML](../examples/modules/deployment-select.yml) | Consumer's `deploy.yml` accepting cluster/user-config; a separate native trigger consumes the generated YAML |
| [release-reserve](../templates/release-reserve.yml) | [YAML](../examples/modules/release-reserve.yml) | Protected branch and release Git URL, deploy-key file and known-hosts file |
| [release-check](../templates/release-check.yml) | [YAML](../examples/modules/release-check.yml) | Reserved tag/commit and authenticated release-registry access |
| [gitlab-release](../templates/gitlab-release.yml) | [YAML](../examples/modules/gitlab-release.yml) | Existing tag and published image/chart outputs, `CI_JOB_TOKEN` |

`JAVA_CI_IMAGE`, `NODE_CI_IMAGE`, `HELM_CI_IMAGE` and `BUILDKIT_CI_IMAGE` are the examples' approved tool-image variables. Maven modules default to `./mvnw`; its prerequisites must be in the image. Set `maven-executable: mvn` only when deliberately using installed Maven, as the runnable samples do. Every module's job name and stage can be overridden; declare those stages in your pipeline.

Release examples demonstrate individual operations, not a complete approval or release policy. Do not infer that including a module provisions server permissions or that a manual job qualifies a release. The optional [standard release strategy](releases.md) shows how those operations are composed and protected.

## Connect outputs with needs

Start with the [runnable examples](../examples/samples/README.md), which use these exact relationships:

| Producer output | Consumer input | Dependency |
|---|---|---|
| `JIB_BUILD_IMAGE_REF` | Helm `image-ref-variable: JIB_BUILD_IMAGE_REF` | Helm needs the Jib job with artifacts |
| `HELM_PUBLISH_REF`, `HELM_PUBLISH_VERSION` | Helm `chart-variable` and `chart-version-variable` | Helm needs the chart publication job with artifacts |
| `HELM_DEPLOY_URL` | Cucumber's default `target-url-variable` | Cucumber needs the Helm job with artifacts |
| A module's artifact files | Normal files in the next job's workspace | The consuming job needs the producer with artifacts |

GitLab imports dotenv values through the artifact dependency. Inputs ending in `-variable` hold a variable **name**, not its value. Runtime outputs cannot select `rules`, stages or includes, which GitLab evaluates before jobs run. [GitLab dotenv documentation](https://docs.gitlab.com/ci/variables/dotenv_variables/).

`helm-deploy` requires the image-variable name explicitly. It does not assume an image-signing/verification chain. For two instances of the same module, choose distinct `job-name` and `output-prefix` values and reference those exact producer names. Use one library revision throughout a pipeline because modules share their lifecycle implementation. The [two-deployable example](../examples/samples/two-deployables.yml) shows this in executable YAML.

## Add your own behavior

Use an ordinary job with its own image and `needs` for an extra check or transformation. Use `pre-hook` or `post-hook` for a small addition within a module's job. `cleanup-hook` runs in `after_script`. Hooks are optional; consumers do not need to configure or understand the internal `MODULE_*` variables. See [hook examples and failure behavior](hooks.md).

Temporary test dependencies also use existing mechanisms. Java tests can use [Spring Boot Testcontainers](https://docs.spring.io/spring-boot/reference/testing/testcontainers.html) locally and in CI when the runner supplies a supported Docker environment. Our ordinary runner currently exposes no Docker daemon to jobs. A dedicated suitable runner is required for that approach. Alternatively attach native [GitLab services](https://docs.gitlab.com/ci/services/) such as PostgreSQL to the test job and provide its connection settings. The module still just runs tests; it needs no custom dependency manager. Neither approach has been added to the sample application yet.

## Optional standard pipeline

[java-service.yml](../pipelines/java-service.yml) is a ready composition of these same modules. It supports a single Java application or a Maven reactor with one deployable Java module, optionally accompanied by an Angular UI. Multiple Maven modules do not necessarily mean multiple deployables. For more deployables, compose explicit module instances as in the examples; arbitrary automatic fan-out is not implemented.

The standard pipeline's delayed Helm selection, dev locking and manual patch release are optional organization policy. They are not requirements of the individual modules. [GitLab component guidance](https://docs.gitlab.com/ci/components/#write-a-component) recommends configurable jobs, small dependencies and clear usage examples; that is the basis for this library.
