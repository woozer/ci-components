# GitLab CI demo

Java 25 / Spring Boot backend and a separate Angular UI served by Nginx. Open the [UI](http://localhost:8090) or [backend](http://localhost:8080/hello). Both also build and test [without GitLab](http://localhost:8929/root/hello-world/-/blob/main/README.md).

## Three everyday actions

1. **Build:** push a branch or merge a reviewed MR. Required backend and Angular tests run automatically. Protected `main` also publishes development artifacts, deploys both applications and runs API/browser integration tests.
2. **Use another Helm profile:** retry **configure-deploy** with modified values, wait for success, then select **Run again** on **deploy-dev**. This redeploys the same images/charts and reruns integration tests. On the first run, use **Unschedule** within ten seconds to choose values before deployment; otherwise defaults apply.
3. **Release:** after green dev validation, run **start-release**. It reserves the next patch version; open the job to override it for a minor/major release. Follow **release-delivery**. The last job, **publish-release**, creates the GitLab Release with notes and asset links after the release artifacts pass dev validation.

Pipeline names identify the work: **CI — main** (or the feature branch), **Dev — deployment en integratietests**, and **Release — 1.2.3** (the reserved version). GitLab places child cards on the right. Their position does not determine execution order.

## Adopt or extend

Copy the [application CI file](http://localhost:8929/root/hello-world/-/blob/main/.gitlab-ci.yml), pin a library revision and set the deployable Maven module. Set `ui-directory` only when there is a separate UI. Application name, chart path and namespace default to the project name; optional defaults do not need repeating.

The shared form and [java-service.yml](pipelines/java-service.yml) contain the complete composition. [Organization settings](config/organization.yml) hold server addresses and task images; credentials stay in GitLab. CI scripts stay in this library.

GitLab provides jobs, `needs`, artifacts, child pipelines, locks, pipeline names and release asset links. Our organization chooses the ten-second deployment selection, manual release moment and automatic patch version. These choices are not industry standards. See [standards and decisions](docs/reuse-and-standards.md).

Reference: [pipeline choices and health timeout](docs/pipeline-options.md), [release policy and assets](docs/releases.md), [required inputs and defaults](docs/inputs.md), [module catalogue](docs/reference.md), [hooks](docs/hooks.md).

The thirteen active modules in `templates/` also work independently, with their own images, inputs, outputs and hooks. Twelve unused modules remain in [modules/todo/](modules/todo/). There is no custom handoff chain; extra steps use ordinary jobs and `needs`.
