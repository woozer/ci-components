# Shared release strategy

Applications import the [pipeline form](../config/pipeline-inputs.yml) and [java-service.yml](../pipelines/java-service.yml) directly. They supply the required app settings (`library-ref` and `maven-project`) and forward the selected cluster, user configuration and pipeline mode. The same central file defines the ordinary pipeline, deployment child and release child, selected by its internal `flow` input. The library owns the jobs, scripts, release button, checks and dev deployment. Applications do not copy or maintain a release pipeline.

The application name and namespace default to the GitLab project name; the chart defaults to `helm/<project-name>`. Helm values come from `environment/cluster/<cluster>.yaml`, followed by `environment/user/<user-config>.yaml`. The central configuration selects the cluster credentials, dev URLs and HTTP registry access. Generic components retain secure protocol defaults. Change local infrastructure settings centrally in the configuration. Optional inputs belong in app configuration only when needed; this demo enables its separate UI with `ui-directory: ui`.

The strategy supports a multi-module Maven reactor with one deployable Java module and an optional separate Angular UI. Libraries and tests build from the root POM. Both deployables share one repository tag and release version. More Java deployables require explicit additional image/chart/deployment jobs with isolated names and outputs; arbitrary fan-out is not implemented.

The Java strategy composes independent Maven, Jib, Helm and release components. Other stacks can reuse the same release components with their own build modules. Organization URLs and task images remain in [organization settings](../config/organization.yml); credentials belong in GitLab variables.

## Start and publish a release

Daily operation is covered by the [three actions](../README.md#standard-pipeline-for-the-java-sample). After a full, successful protected-main pipeline, **start-release** reserves the version and tag. Its `version: auto` starts at `0.1.0` and increments the highest reserved patch number. Open the job to override it, for example with `1.0.0`. Reduced `validate`/`publish` modes do not qualify for release.

**release-delivery** starts `Release — <version>`. It rebuilds, tests and publishes the reserved version, deploys it to dev and runs API/browser tests. **publish-release** is the last job: it creates the actual GitLab Release after all required validation succeeds. Reserving a tag alone does not create that release record. Existing pinned consumers keep the old job names until they update their library revision.

There is no separate tag approval. Clicking **start-release** is the release decision; code review happens before the merge. The local demo has one user, so that user also merges the merge request. In the real organization, require another person's review before merging into protected branches. A manual button alone does not enforce two-person approval.

A release creates immutable artifacts. Those artifacts may be deployed to dev. Future production deployment through Argo CD must select the existing release image digest and chart version; it must not rebuild the application. Argo CD production delivery is outside this local demo.

## Release assets

**publish-release** uses the supported [GitLab Releases API](https://docs.gitlab.com/api/releases/#create-a-release) to create notes and `assets.links` in one request. The assets contain an image manifest and Helm manifest for each deployable, a Maven package-list link and the validation pipeline. The notes retain exact image digests and OCI chart references for deployment.

GitLab asset URLs must be HTTP(S) or FTP; Docker pull references and `oci://` references are not clickable release assets. In this Artifactory demo, `ARTIFACTORY_PUBLIC_URL` centrally supplies the browser address. Manifest links point to the reserved version directory in the repository that denies overwrite. They describe registry artifacts, not downloadable Docker image archives. Maven's link opens the project's package list, not a single JAR. Registry authentication still applies; links contain no credentials. [GitLab release asset fields](https://docs.gitlab.com/user/project/releases/release_fields/#release-assets).

The standalone module's optional `artifact-base-url` accepts a public Artifactory `/artifactory` root. Without it, links use HTTPS OCI Distribution manifest endpoints (image digest and chart version); some registries require authentication and an OCI `Accept` header for chart manifests. The Artifactory override avoids that browser header requirement. An ordinary module consumer can omit this setting; the demo composition supplies it centrally.

Assets are links to the existing storage, not another artifact copy. Server permissions enforce immutability; a GitLab Release record alone does not. This change applies to future releases and does not rewrite existing releases.

## Versions and repeated attempts

| Build | Version |
|---|---|
| Standalone `./mvnw verify` | `1.0.0-SNAPSHOT` by default |
| Development pipeline | `0.0.0-dev.<pipeline-number>.g<commit>` |
| Official release | `auto`: first `0.1.0`, then next patch; explicit SemVer override supported; Git tag `v<version>` |

Maven, the image tag and the Helm chart use the same resolved version. A new development pipeline gets a new number. A release number is never reused for another commit or image. Automatic selection reads version-sorted remote `vX.Y.Z` tags while holding the reservation lock. Tags from failed releases still count. A tag lookup failure blocks publication rather than guessing a version. Override the default patch bump when [Semantic Versioning](https://semver.org/) calls for a minor or major release.

Maven uses `${revision}` and the standard Flatten Maven Plugin. CI supplies the version through `MAVEN_ARGS`; no release commit or release branch is needed. Outside CI, `./mvnw -Drevision=1.2.3 verify` builds and tests that version without publishing anything. [Maven CI Friendly Versions](https://maven.apache.org/guides/mini/guide-maven-ci-friendly.html)

The reservation job creates the Git tag atomically on the exact commit of the selected main pipeline, even if main has since advanced. The tag permanently reserves the number. If release creation fails, the tag stays and the number is not recycled. An existing image blocks another release build; deploying the already published digest again remains possible.

`release-reserve` only needs Git access: it selects the version and reserves the tag. `release-check` checks Artifactory once, before the release build starts. An unavailable registry or an existing image/chart stops that child pipeline; the tag remains reserved. Registry credentials and artifact paths are therefore inputs to `release-check` only.

## Where the behavior lives

| File | Responsibility |
|---|---|
| [organization.yml](../config/organization.yml) | Shared server addresses and task images |
| [java-service.yml](../pipelines/java-service.yml) | Complete composition: ordinary pipeline, serialized deployment and release |
| [deployment-select.yml](../templates/deployment-select.yml) | Choose cluster/user values and record the deployment configuration |
| [release-reserve.yml](../templates/release-reserve.yml) | Select the version and reserve its Git tag; publish version/commit inputs |
| [release-check.yml](../templates/release-check.yml) | Check tag, commit and existing artifacts before the release build |
| [gitlab-release.yml](../templates/gitlab-release.yml) | Record the tested artifacts as a GitLab release |
| [shared/release.yml](../shared/release.yml) | Shared validation functions used by those components |

The reservation job writes a small child-pipeline configuration artifact. Its central template and application settings are fixed when the parent pipeline is created; the selected version, exact commit and successful deployment choices are resolved at runtime. Job implementations stay in the library. This keeps a later retry tied to the original inputs and pinned library revision.

## Enforcement in GitLab and Artifactory

- Protect `main`: allow merge requests, deny direct pushes and force pushes, including CI identities.
- Protect `v*`: only the release deploy key can create release tags. Tag pipelines do not publish; the protected branch pipeline owns publication.
- Restrict release credentials to protected refs and `release/*` environments. The Git deploy key is limited to `release/reserve`. Use typed job inputs and disallow arbitrary pipeline-variable overrides.
- Publish images and OCI charts to `docker-releases-local` with a dedicated account having Read, Deploy and Annotate, without Delete/Overwrite, Manage or administrator rights. Annotate lets Artifactory record OCI media-type properties; without it, Helm publication can fail with an incorrect manifest Content-Type. It does not grant artifact overwrite. The development publisher has no write access to this repository.
- Disable Maven duplicate publication in the namespace package settings. Each pipeline receives a unique development version; official versions are reserved by Git tag.
- Serialize reservation jobs. Serialize the delivery child pipeline through the final dev test, using the same dev lock as ordinary development delivery. Registry permissions remain necessary in addition to pipeline checks.

GitLab/Artifactory administrators can change permissions; CI must never use their credentials. Protected tags control tag permissions, not which branch a commit belongs to: the release components also validate branch protection and commit ancestry. [GitLab tags](https://docs.gitlab.com/user/project/protected_tags/), [resource groups](https://docs.gitlab.com/ci/resource_groups/), [Artifactory permissions](https://docs.jfrog.com/administration/docs/permissions).

These components are shared, but including YAML does not configure server permissions. The local setup is applied by `infra/gitlab-runner/configure-releases.py`, outside the application. Provision equivalent permissions for every consuming project and release repository in the organization.

The local free-edition lab stores Maven packages in GitLab and images/charts in Artifactory JCR. Test reports stay in GitLab. JCR does not support native Maven repositories; moving Maven packages into Artifactory requires an appropriate edition. [JFrog editions](https://docs.jfrog.com/artifactory/docs/jfrog-container-registry)

## Repositories with the optional UI

With `ui-directory`, a reserved release covers both deployables at the same version. Separate `check-release` and `check-ui-release` jobs reject existing image/chart coordinates before building. Both test suites must pass before publication. The backend uses Jib; the UI uses rootless BuildKit. Both publish to the immutable release repository, deploy to dev, and pass HTTP/browser Cucumber tests before `publish-release` records both image digests and both chart references. Production must promote both recorded images without rebuilding. Helm releases are separate: a failed UI deployment does not automatically roll back an already successful backend deployment; keep API changes backward compatible.
