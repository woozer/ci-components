# Settings used by the demo

The organization file is [config/organization.yml](../config/organization.yml). It contains shared server addresses and image selections; including it adds no jobs. The application imports [java-service.yml](../pipelines/java-service.yml) directly. That single composition owns modules, job order and project-name defaults.

| Setting | Purpose |
|---|---|
| `GITLAB_INTERNAL_URL` | GitLab address reachable from job containers |
| `ARTIFACTORY_PUBLIC_URL` | Browser address for release asset links; no credentials |
| `OCI_REGISTRY` | Registry address used by Jib and Helm |
| `DEV_TARGET_URL`, `DEV_PUBLIC_URL` | Development URL for CI and the GitLab UI |
| `HELM_REGISTRY_PLAIN_HTTP` | Explicit local-lab HTTP access for Helm registry login |
| `OCI_REPOSITORY` | Artifactory repository receiving images and charts |
| `MAVEN_BUILD_IMAGE`, `MAVEN_PUBLISH_IMAGE` | Images for the two Maven tasks |
| `CUCUMBER_TEST_IMAGE`, `JIB_BUILD_IMAGE` | Images for HTTP tests and Jib |
| `HELM_PUBLISH_IMAGE`, `HELM_DEPLOY_IMAGE` | Images for chart publishing and deployment |
| `JIB_BASE_IMAGE` | Java runtime used inside the application image |

Task images use digest-pinned GitLab variables for Java/Maven, Node, BuildKit, Helm and Playwright; runtime variables select Java and Nginx images. They are already configured in this lab. Change a task's mapping to select another approved image, or use a literal digest-pinned image reference. Group/project variables can override YAML defaults.

**Credentials and environments** belong in GitLab's CI/CD variable settings:

| Variable | How it is stored and used |
|---|---|
| `LOCAL_KUBECONFIG` | Protected file variable: Kubernetes API URL, CA and deployment credential |
| `ARTIFACTORY_MAVEN_SETTINGS` | Protected file variable: Maven/Jib registry credentials |
| `ARTIFACTORY_USERNAME` | Protected variable: registry publisher account |
| `ARTIFACTORY_PASSWORD_FILE` | Protected, masked file variable: publisher password |
| `DOCKER_AUTH_CONFIG` | Masked variable: runner registry read/cache credentials |
| `CI_JOB_TOKEN` | Supplied automatically by GitLab for Maven package publishing |

The sample deploys to local Kubernetes. OpenShift can use the same `helm-deploy` module with an OpenShift kubeconfig. Scope deployment credentials to the matching GitLab environment, such as `local`, `test` or `production`, and grant access to the required namespace. Registry credentials used by publish jobs must also be available to those jobs. Do not put credential values in the organization YAML, hook parameters or output artifacts.

**The static app settings are the required central pipeline inputs:** `library-ref` and `maven-project`. The demo enables its separate UI with `ui-directory: ui`. The application also forwards runtime choices from the shared New pipeline form. The profile defaults application name and namespace to `$CI_PROJECT_NAME`, chart path to `helm/$CI_PROJECT_NAME`, and environment directory to `environment/`. Local endpoint URLs, HTTP registry access and the cluster-to-kubeconfig mapping are organization settings in the central configuration. Default values are not repeated in the application. Stages, dependencies and hooks belong to the central strategy.

The `configure-deploy` job selects `cluster` and `user_config` after publication, with a ten-second default delay. `pipeline_mode` is selected before pipeline creation. The optional `test-custom` job accepts a Cucumber tag selection; mandatory tests keep their fixed configuration. See [pipeline choices](pipeline-options.md).

**Module defaults** stay in each module's `spec:inputs`. Consumers can omit these inputs:

| Input | Default for the demo modules |
|---|---|
| `artifact-expire-in` | `7 days` |
| `job-timeout` | `30m` |
| `working-directory` | `.` |
| `output-prefix` | Module-specific, for example `MAVEN_BUILD` |
| `maven-executable` | `./mvnw` in Maven/Jib/Cucumber modules |
| `pre-hook`, `post-hook`, `cleanup-hook` | Empty: no hook |
| `hook-parameters-json` | `{}` |
| Cucumber `profile` | Empty: no Maven profile |

For example, set `artifact-expire-in: 30 days` only when that job needs longer retention. The `image` input remains required so each module explicitly selects its tool image. See [required inputs per module](inputs.md) for the complete overview and runtime prerequisites.

The declarations repeat in each component because inputs are scoped to the declaring file. GitLab's `spec:include` supports shared pipeline input definitions, but not component input definitions. Shared hook code lives in `shared/module.yml`; the typed input contract stays with each module. There is no additional defaults loader or generation step. [GitLab input scope](https://docs.gitlab.com/ci/inputs/), [shared input limitations](https://docs.gitlab.com/ci/inputs/#define-pipeline-inputs-in-external-files).

The optional [full pipeline example](../examples/full-pipeline/application.gitlab-ci.yml) and its [profile documentation](organization-profile.md) are reference material for adding scanners and other modules later. They are not included by the demo.

For Dockerfile publication, `image-build` copies the runner's pull credentials into a temporary Docker configuration, then overrides the target registry with the explicit publisher credentials. It unsets `DOCKER_AUTH_CONFIG` inside the job before BuildKit runs: newer Docker clients give that environment variable precedence over `config.json`. The runner can still pull the job image with its read-only account; credentials for other base-image registries are preserved. Temporary publisher credentials are removed in `after_script`. [Docker credential selection](https://github.com/docker/cli/blob/master/cli/config/configfile/file.go).
