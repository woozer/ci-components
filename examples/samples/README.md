# Runnable module examples

These are ordinary GitLab pipelines assembled from individual modules. The validation project executes these exact files; the Java application's normal pipeline remains independent.

| Sample | Jobs demonstrated |
|---|---|
| [maven-build](maven-build.yml) | One Maven build, with no other module required |
| [build-and-test](build-and-test.yml) | Maven build artifacts imported by a Cucumber/Failsafe job |
| [deploy-and-test](deploy-and-test.yml) | Jib image and OCI Helm chart → Helm readiness → API tests |
| [two-deployables](two-deployables.yml) | Backend and UI, repeated Helm/Cucumber modules with distinct names and outputs |

## Run in GitLab

1. Open [CI samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new).
2. Select `main` and choose `sample`: one of the four names above, or `all`.
3. Keep the supplied `library_ref` for the installed version, or enter the exact component commit you are testing.
4. Select **New pipeline**. Open the child named after the sample to inspect jobs, artifacts and test reports.

A module change also runs all four examples from the component project's `validate-samples` trigger. `strategy: mirror` propagates failures to that pipeline. The trigger supplies the candidate component commit, rather than testing an older published copy. Tests do not silently skip a failing sample. The internal [component validation include](../../tests/samples/component-validation.yml) resolves `CI_COMMIT_SHA` with GitLab's native `expand_vars` before passing it to the downstream input; the sample project accepts only a full commit SHA.

## Use an example in your project

Include the selected file at an immutable library revision, passing the same revision as `library-ref`. For example:

```yaml
include:
  - project: root/ci-components
    ref: &library REPLACE_WITH_COMMIT_SHA
    file: /examples/samples/build-and-test.yml
    inputs:
      library-ref: *library
```

Alternatively copy the example and adapt its component includes. Keep job order in your pipeline with `stages` and `needs`. Optional module defaults remain omitted. Supply approved tool images as GitLab group/project variables. Our runtime settings under `tests/samples/` configure only the validation lab and assertions; they are not required when using the modules.

The build examples need `JAVA_CI_IMAGE`, Java 25, Maven and a repository POM. The configured CI image provides `mvn`; standalone applications can instead use the module's default `./mvnw`. The test example expects Cucumber/Failsafe to start its own backend. Adapt that test configuration to your application.

The deployment examples use the sample's `hello-app`, `helm/hello-world`, `ui` and `helm/hello-world-ui` directories. These paths are explicit, so it is clear what to change for your application. Set:

| Configuration | Purpose |
|---|---|
| `JAVA_CI_IMAGE`, `HELM_CI_IMAGE`, `JAVA_RUNTIME_IMAGE` | Approved Java/Maven, Helm and Java runtime images |
| `OCI_REGISTRY`, `OCI_REPOSITORY` | Registry and publication repository |
| `ARTIFACTORY_USERNAME`, `ARTIFACTORY_PASSWORD_FILE`, `ARTIFACTORY_MAVEN_SETTINGS` | Scoped registry credentials; password/settings are file variables |
| `SAMPLE_KUBECONFIG`, `SAMPLE_NAMESPACE`, `API_TARGET_URL` | Pre-provisioned test namespace, scoped kubeconfig file and reachable API URL |
| `NODE_CI_IMAGE`, `BUILDKIT_CI_IMAGE`, `BROWSER_CI_IMAGE`, `NGINX_RUNTIME_IMAGE`, `UI_TARGET_URL` | Additional tools/runtime and URL for the UI example |

Commit `environment/cluster/validation-api.yaml` and, for the UI example, `validation-ui.yaml`. They set service routing, image-pull secret and the UI backend URL for your environment. Registry login uses the shared `.helm-login` YAML; set `HELM_REGISTRY_PLAIN_HTTP` only for an explicit HTTP lab. `plain-http` defaults to false in the examples.

## Test isolation and evidence

The local `ci-samples` project contains a pinned snapshot of the Java/Angular application; its README records the source commit. It has its own namespace, Helm releases and registry write scope. Backend/UI test ports are 8180/8190; ordinary dev remains on 8080/8090. A native resource group on each deployment trigger holds the test-environment lock through deployment, tests and cleanup. The `cleanup-sample` job uninstalls test releases even when tests fail. A canceled pipeline can require manual cleanup; the credentials cannot operate in the normal application's namespace.

`verify-sample` checks real build artifacts, the producing commit/pipeline and the image/chart/URL outputs consumed downstream. Cucumber and Playwright validate actual deployed behavior. GitLab's compilation and existing Python contract tests complement those real executions; CI Lint alone cannot establish that a build or deployment works.

This adopts [GitLab's component testing advice](https://docs.gitlab.com/ci/components/#test-the-component) and [testing with sample files](https://docs.gitlab.com/ci/components/#test-a-component-against-sample-files). The separate project, four examples and local isolation settings are our implementation choices. Selection and orchestration use native [pipeline inputs](https://docs.gitlab.com/ci/inputs/#for-a-pipeline), [downstream pipelines](https://docs.gitlab.com/ci/pipelines/downstream_pipelines/) and [resource groups](https://docs.gitlab.com/ci/resource_groups/).
