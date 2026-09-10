# GitLab CI demo

A Java 25 Spring Boot application returns `hello world`. Its pipeline builds, tests, publishes and deploys it using small reusable YAML modules.

Start with the [hello-world application](http://localhost:8929/root/hello-world). Run `./mvnw verify` from `ci/java` to build and test without GitLab. To see CI, open [Pipelines](http://localhost:8929/root/hello-world/-/pipelines), choose **New pipeline**, select `main`, and run it. Pushing a commit also starts the pipeline.

```mermaid
flowchart LR
  B[Build] --> T[Cucumber]
  T --> M[Publish Maven]
  M --> I[Publish Jib image]
  M --> C[Publish Helm chart]
  I --> D[Helm deploy]
  C --> D
  D --> V[Cucumber against deployment]
```

The deployed endpoint is [localhost:8080/hello](http://localhost:8080/hello).

The demo uses six modules; Cucumber runs twice:

| Module | What it does |
|---|---|
| [maven-build](templates/maven-build.yml) | Package the application |
| [cucumber-test](templates/cucumber-test.yml) | Test the HTTP endpoint, locally or after deployment |
| [maven-publish](templates/maven-publish.yml) | Publish Maven packages to GitLab |
| [jib-build](templates/jib-build.yml) | Publish the application image to local Artifactory |
| [helm-publish](templates/helm-publish.yml) | Publish the Helm chart to local Artifactory |
| [helm-deploy](templates/helm-deploy.yml) | Deploy that chart and image digest |

Each module chooses its own Maven or Helm image. The application includes the modules at a pinned revision and owns their order.

**Three places to read:**

1. [Application pipeline](http://localhost:8929/root/hello-world/-/blob/main/.gitlab-ci.yml): select modules, pass inputs, connect jobs with `needs`.
2. [A module](templates/maven-build.yml): declare inputs, choose an image, run one operation.
3. [Shared lifecycle](shared/module.yml): common setup, post-hook/output handling and cleanup. Its comments explain `!reference`.

The build post-hook writes `BUILD_CUSTOM_LABEL`; the test pre-hook reads it. Other outputs pass the image digest, chart version and deployment URL to the next job. Outputs are variables in a GitLab dotenv artifact.

**Configuration stays small.** [config/organization.yml](config/organization.yml) holds server addresses and an image selection for each task. Credentials stay in GitLab variables. Module defaults live in `spec:inputs`; application inputs select paths and the deployment target. The settings file adds no jobs. See [settings used by the sample](docs/defaults.md).

See [required inputs and optional defaults](docs/inputs.md) before configuring a module. A project can use just one module. Include its component, supply the required `image` and other inputs, and declare its stage. Shared hook handling is included automatically; organization settings and other modules are optional. A deployment module can receive its chart and image digest from any producer that supplies its inputs.

For details beyond this demo, use the [library reference](docs/reference.md) and [hook contract](docs/hooks.md).
