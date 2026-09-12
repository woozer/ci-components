# GitLab CI modules

Build your own pipeline from independently usable modules, or use the optional Java standard pipeline. Each module owns one operation, selects its own image and publishes named outputs. Your pipeline owns `stages`, `needs`, conditions and additional jobs.

## Build your own pipeline

1. Choose a module from the [module guide](docs/modules.md).
2. Copy its minimal example, pin the library commit and provide the required inputs. Optional defaults can be omitted.
3. Connect jobs with ordinary GitLab `needs` and artifacts/dotenv. Start from a [runnable example](examples/samples/README.md).

| Start small | Add a next step | Repeat modules |
|---|---|---|
| [Maven build](examples/samples/maven-build.yml) | [Build → test](examples/samples/build-and-test.yml), [image/chart → deployment → test](examples/samples/deploy-and-test.yml) | [Two deployables](examples/samples/two-deployables.yml) |

Run these in [CI samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new): choose `sample`, then **New pipeline**. The same YAML files serve consumers and validate module changes in real GitLab jobs. See [how validation works](examples/samples/README.md#test-isolation-and-evidence).

You do not need the Java standard pipeline, organization profile or release process to use one module. Images and service credentials are supplied by your platform; required inputs and runtime prerequisites are documented per module. Shared hook handling is included automatically.

## Standard pipeline for the Java sample

1. **Build:** push a branch or merge a reviewed MR. Required backend and Angular tests run automatically. Protected `main` also publishes development artifacts, deploys both applications and runs API/browser integration tests.
2. **Use another Helm profile:** retry **configure-deploy** with modified values, wait for success, then select **Run again** on **deploy-dev**. This redeploys the same images/charts and reruns integration tests. On the first run, use **Unschedule** within ten seconds to choose values before deployment; otherwise defaults apply.
3. **Release:** after green dev validation, run **start-release**. It reserves the next patch version; open the job to override it for a minor/major release. Follow **release-delivery**. The last job, **publish-release**, creates the GitLab Release with notes and asset links after the release artifacts pass dev validation.

Pipeline names identify the work: **CI — main** (or the feature branch), **Dev — deployment en integratietests**, and **Release — 1.2.3** (the reserved version). GitLab places child cards on the right. Their position does not determine execution order.

The optional [java-service.yml](pipelines/java-service.yml) composes these same modules. It supports one Java deployable (including a multi-module Maven reactor) and an optional Angular UI. More Java deployables can use the individual modules; automatic fan-out of arbitrary deployables is not implemented. The [application CI file](http://localhost:8929/root/hello-world/-/blob/main/.gitlab-ci.yml) shows adoption with only app-specific settings and forwarded form selections.

Reference: [module guide](docs/modules.md), [required inputs](docs/inputs.md), [outputs and advanced reference](docs/reference.md), [hooks and extra jobs](docs/hooks.md), [standard-pipeline choices](docs/pipeline-options.md), [release policy](docs/releases.md).

We follow GitLab's component testing and reuse guidance. GitLab provides jobs, dependencies, artifacts, inputs and locks; the ten-second deployment selection and automatic patch policy belong to our optional standard pipeline. See [standards and decisions](docs/reuse-and-standards.md).

Thirteen active modules live in `templates/`; twelve future modules remain in [modules/todo/](modules/todo/). There is no custom handoff chain or YAML generator.
