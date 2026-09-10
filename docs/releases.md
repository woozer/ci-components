# Shared release strategy

Applications import the [pipeline form](../config/pipeline-inputs.yml) and [organization profile](../config/java-service.yml). They supply the required app settings (`library-ref` and `maven-project`) and forward the selected cluster, user configuration and pipeline mode. The profile applies organization conventions, then starts [pipelines/java-service.yml](../pipelines/java-service.yml). The library owns the jobs, scripts, release button, checks and dev deployment. Applications do not copy or maintain a release pipeline.

The application name and namespace default to the GitLab project name; the chart defaults to `helm/<project-name>`. Helm values come from `environment/cluster/<cluster>.yaml`, followed by `environment/user/<user-config>.yaml`. The local profile selects the cluster credentials, dev URLs and HTTP registry access. Generic components retain secure protocol defaults. Change local infrastructure settings centrally in the profile. Optional inputs belong in app configuration only when a project deliberately departs from those conventions; the demo sets none.

The current strategy supports a multi-module Maven reactor with one deployable module. Libraries and tests are built from the root POM. Multiple deployables would require an explicit module list and separate image/chart/deployment jobs, with names and outputs isolated per deployable. The KISS release policy would keep one repository tag and version across them; this fan-out is not implemented in the current demo.

The Java strategy composes independent Maven, Jib, Helm and release components. Other stacks can reuse the same release components with their own build modules. Organization URLs and task images remain in [organization settings](../config/organization.yml); credentials belong in GitLab variables.

## Everyday flow

1. Push a feature branch and open a merge request. The central `configure` job starts with defaults after 10 seconds. Follow **run-pipeline** to the build and Cucumber jobs. To select a different mode or Helm user profile, unschedule `configure` before its timer expires, then run it with the desired job inputs. See [pipeline choices](pipeline-options.md).
2. Merge to the protected default branch after review and successful checks. In this demo that branch is `main`.
3. The main pipeline automatically publishes development artifacts, deploys to dev and runs Cucumber against the deployed application.
4. To create an official release, open that successful **run-pipeline** child pipeline and select the **release** job name. Enter a new version such as `1.2.3`, then select **Run job**. The release button is available only after the full `deploy` mode; reduced modes do not qualify for a release.
5. Follow **release-delivery** to see validation, Maven publication, Jib image publication, Helm publication, dev deployment and the final Cucumber test. A successful run creates the GitLab release with its commit, image digest and chart version.

There is no separate tag approval. Clicking **release** is the release decision; code review happens before the merge. The local demo has one user, so that user also merges the merge request. In the real organization, require another person's review before merging into protected branches. A manual button alone does not enforce two-person approval.

A release creates immutable artifacts. Those artifacts may be deployed to dev. Future production deployment through Argo CD must select the existing release image digest and chart version; it must not rebuild the application. Argo CD production delivery is outside this local demo.

## Versions and repeated attempts

| Build | Version |
|---|---|
| Standalone `./mvnw verify` | `1.0.0-SNAPSHOT` by default |
| Development pipeline | `0.0.0-dev.<pipeline-number>.g<commit>` |
| Official release | User-selected SemVer, for example `1.2.3`; Git tag `v1.2.3` |

Maven, the image tag and the Helm chart use the same resolved version. A new development pipeline gets a new number. A release number is never reused for another commit or image. Select patch/minor/major according to [Semantic Versioning](https://semver.org/).

Maven uses `${revision}` and the standard Flatten Maven Plugin. CI supplies the version through `MAVEN_ARGS`; no release commit or release branch is needed. Outside CI, `./mvnw -Drevision=1.2.3 verify` builds and tests that version without publishing anything. [Maven CI Friendly Versions](https://maven.apache.org/guides/mini/guide-maven-ci-friendly.html)

The reservation job creates the Git tag atomically on the exact commit of the selected main pipeline, even if main has since advanced. The tag permanently reserves the number. If release creation fails, the tag stays and the number is not recycled. An existing image blocks another release build; deploying the already published digest again remains possible.

## Where the behavior lives

| File | Responsibility |
|---|---|
| [config/java-service.yml](../config/java-service.yml) | Organization defaults and the app-facing required inputs |
| [java-service.yml](../pipelines/java-service.yml) | Automatic builds, manual release decision and serialized delivery |
| [java-service-delivery.yml](../pipelines/java-service-delivery.yml) | Tool jobs, dev deployment and HTTP validation |
| [release-reserve.yml](../templates/release-reserve.yml) | Check and reserve a release tag; publish version/commit inputs |
| [release-check.yml](../templates/release-check.yml) | Check tag, commit and existing artifacts before the release build |
| [gitlab-release.yml](../templates/gitlab-release.yml) | Record the tested artifacts as a GitLab release |
| [shared/release.yml](../shared/release.yml) | Shared validation functions used by those components |

The reservation job writes a small child-pipeline configuration artifact. Its central template and application settings are fixed when the parent pipeline is created; only the selected version and exact commit are inserted at runtime. Job implementations stay in the library. This keeps a later retry tied to the original inputs and pinned library revision.

## Enforcement in GitLab and Artifactory

- Protect `main`: allow merge requests, deny direct pushes and force pushes, including CI identities.
- Protect `v*`: only the release deploy key can create release tags. Tag pipelines do not publish; the protected branch pipeline owns publication.
- Restrict release credentials to protected refs and `release/*` environments. The Git deploy key is limited to `release/reserve`. Use typed job inputs and disallow arbitrary pipeline-variable overrides.
- Publish images and OCI charts to `docker-releases-local` with a dedicated account having Read and Deploy, without Delete/Overwrite, Manage or administrator rights. The development publisher has no write access to this repository.
- Disable Maven duplicate publication in the namespace package settings. Each pipeline receives a unique development version; official versions are reserved by Git tag.
- Serialize reservation jobs. Serialize the delivery child pipeline through the final dev test, using the same dev lock as ordinary development delivery. Registry permissions remain necessary in addition to pipeline checks.

GitLab/Artifactory administrators can change permissions; CI must never use their credentials. Protected tags control tag permissions, not which branch a commit belongs to: the release components also validate branch protection and commit ancestry. [GitLab tags](https://docs.gitlab.com/user/project/protected_tags/), [resource groups](https://docs.gitlab.com/ci/resource_groups/), [Artifactory permissions](https://docs.jfrog.com/administration/docs/permissions).

These components are shared, but including YAML does not configure server permissions. The local setup is applied by `infra/gitlab-runner/configure-releases.py`, outside the application. Provision equivalent permissions for every consuming project and release repository in the organization.

The local free-edition lab stores Maven packages in GitLab and images/charts in Artifactory JCR. Test reports stay in GitLab. JCR does not support native Maven repositories; moving Maven packages into Artifactory requires an appropriate edition. [JFrog editions](https://docs.jfrog.com/artifactory/docs/jfrog-container-registry)
