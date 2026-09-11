# Shared release strategy

Applications import the [pipeline form](../config/pipeline-inputs.yml) and [java-service.yml](../pipelines/java-service.yml) directly. They supply the required app settings (`library-ref` and `maven-project`) and forward the selected cluster, user configuration and pipeline mode. The same central file defines the ordinary pipeline, deployment child and release child, selected by its internal `flow` input. The library owns the jobs, scripts, release button, checks and dev deployment. Applications do not copy or maintain a release pipeline.

The application name and namespace default to the GitLab project name; the chart defaults to `helm/<project-name>`. Helm values come from `environment/cluster/<cluster>.yaml`, followed by `environment/user/<user-config>.yaml`. The central configuration selects the cluster credentials, dev URLs and HTTP registry access. Generic components retain secure protocol defaults. Change local infrastructure settings centrally in the configuration. Optional inputs belong in app configuration only when a project deliberately departs from those conventions; the demo sets none.

The current strategy supports a multi-module Maven reactor with one deployable module. Libraries and tests are built from the root POM. Multiple deployables would require an explicit module list and separate image/chart/deployment jobs, with names and outputs isolated per deployable. The KISS release policy would keep one repository tag and version across them; this fan-out is not implemented in the current demo.

The Java strategy composes independent Maven, Jib, Helm and release components. Other stacks can reuse the same release components with their own build modules. Organization URLs and task images remain in [organization settings](../config/organization.yml); credentials belong in GitLab variables.

## Everyday flow

1. Push a feature branch and open a merge request. Build and mandatory Cucumber tests run immediately in the main graph. The optional **test-custom** job allows additional scenario selections. See [pipeline choices](pipeline-options.md).
2. Merge to the protected default branch after review and successful checks. In this demo that branch is `main`.
3. The main pipeline automatically publishes development artifacts. **configure-deploy** allows ten seconds to stop the timer and choose cluster/user values. **deploy-dev** then runs Helm and Cucumber together.
4. To create an official release, run **release** in that successful main pipeline. Its default `version: auto` selects `0.1.0` for the first release and increments the highest reserved release's patch number thereafter. To choose a minor or major version, open the job and override `version`, for example with `1.0.0`. The release button is available only after the full `deploy` mode; reduced modes do not qualify for a release.
5. Follow **release-delivery** to see validation, Maven publication, Jib image publication, Helm publication, dev deployment and the final Cucumber test. A successful run creates the GitLab release with its commit, image digest and chart version.

There is no separate tag approval. Clicking **release** is the release decision; code review happens before the merge. The local demo has one user, so that user also merges the merge request. In the real organization, require another person's review before merging into protected branches. A manual button alone does not enforce two-person approval.

A release creates immutable artifacts. Those artifacts may be deployed to dev. Future production deployment through Argo CD must select the existing release image digest and chart version; it must not rebuild the application. Argo CD production delivery is outside this local demo.

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

With `ui-directory`, a reserved release covers both deployables at the same version. Separate `check-release` and `check-ui-release` jobs reject existing image/chart coordinates before building. Both test suites must pass before publication. The backend uses Jib; the UI uses rootless BuildKit. Both publish to the immutable release repository, deploy to dev, and pass HTTP/browser Cucumber tests before `finish-release` records both image digests and both chart references. Production must promote both recorded images without rebuilding. Helm releases are separate: a failed UI deployment does not automatically roll back an already successful backend deployment; keep API changes backward compatible.
