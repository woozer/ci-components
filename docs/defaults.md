# Settings used by the demo

The organization file is [config/organization.yml](../config/organization.yml). It contains server addresses and image selections; including it adds no jobs. The application chooses modules and their order.

| Setting | Purpose |
|---|---|
| `GITLAB_INTERNAL_URL` | GitLab address reachable from job containers |
| `OCI_REGISTRY` | Registry address used by Jib and Helm |
| `OCI_REPOSITORY` | Artifactory repository receiving images and charts |
| `MAVEN_BUILD_IMAGE`, `MAVEN_PUBLISH_IMAGE` | Images for the two Maven tasks |
| `CUCUMBER_TEST_IMAGE`, `JIB_BUILD_IMAGE` | Images for HTTP tests and Jib |
| `HELM_PUBLISH_IMAGE`, `HELM_DEPLOY_IMAGE` | Images for chart publishing and deployment |
| `JIB_BASE_IMAGE` | Java runtime used inside the application image |

The image selections currently refer to three digest-pinned GitLab project variables: `JAVA_CI_IMAGE`, `HELM_CI_IMAGE`, and `JAVA_RUNTIME_IMAGE`. They are already configured in this lab. Change a task's mapping to select another approved image, or use a literal digest-pinned image reference. Group/project variables can override YAML defaults.

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

**Application choices** stay in its pipeline: source and chart paths, image name, Helm release and namespace, endpoint URL, stages, dependencies and hook paths.

**Module defaults** stay in each module's `spec:inputs`. The demo uses the existing 30-minute job timeout and seven-day artifact retention; override `job-timeout` or `artifact-expire-in` only when needed. There is no additional defaults loader.

The optional [full pipeline example](../examples/full-pipeline/application.gitlab-ci.yml) and its [profile documentation](organization-profile.md) are reference material for adding scanners and other modules later. They are not included by the demo.
