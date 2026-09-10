# Inputs: required or optional?

Pass values under `include:inputs`. The `MODULE_*` variables inside a component are internal mappings used by its scripts; consumers do not need to set them.

The `spec:inputs` header in each module is the source of truth:

- An input **without `default` is required**. GitLab rejects the pipeline if it is missing.
- An input **with `default` is optional**. Supply it only to change the default.
- Additional runtime files, variables and credentials may still be needed by the operation, as described below.

Every module requires `image`. Other required inputs for the six demo modules are:

| Module | Additional required inputs |
|---|---|
| [maven-build](../templates/maven-build.yml) | None |
| [cucumber-test](../templates/cucumber-test.yml) | None; see the target URL condition below |
| [maven-publish](../templates/maven-publish.yml) | `settings-file`, `repository-url` |
| [jib-build](../templates/jib-build.yml) | `project-selector`, `settings-file`, `image-repository`, `base-image` |
| [helm-publish](../templates/helm-publish.yml) | `chart`, `chart-name`, `chart-version`, `oci-repository` |
| [helm-deploy](../templates/helm-deploy.yml) | `values-file`, `release`, `namespace`, `environment`, `target-url` |

Common optional inputs:

| Input | Default |
|---|---|
| `job-name`, `stage` | Defined by the chosen module |
| `working-directory` | `.` |
| `output-prefix` | Module-specific, for example `MAVEN_BUILD` |
| `pre-hook`, `post-hook`, `cleanup-hook` | Empty: no hook |
| `hook-parameters-json` | `{}` |
| `job-timeout` | `30m` for the demo modules |
| `artifact-expire-in` | `7 days` |
| `maven-executable` | `./mvnw` in the Maven/Jib/Cucumber modules |
| Cucumber `profile` | Empty: no Maven profile |

**Runtime conditions:**

- Cucumber normally reads the URL from `HELM_DEPLOY_URL`. Provide that variable, select another with `target-url-variable`, or set `target-url-variable: ''` when the suite starts its own application.
- Helm deployment needs either `chart` or `chart-variable`. The selected image variable must contain an immutable image reference. Provide a kubeconfig through `kubeconfig-variable` or the documented Kubernetes environment variables. Chart values must support `image.repository` and `image.digest`.
- Publishing needs authentication for the chosen registry or Maven repository. Use a settings file, GitLab variables or an authentication pre-hook; see [organization settings and credentials](defaults.md).

A single-module pipeline can be this small. Set `MY_MAVEN_IMAGE` to your chosen Maven image; this example uses its installed Maven:

```yaml
stages: [build]

include:
  - component: $CI_SERVER_FQDN/root/ci-components/maven-build@54f0b3819b073d138a5b0842979fe0bc84fefe0f
    inputs:
      image: $MY_MAVEN_IMAGE
      maven-executable: mvn
```

This creates one job. It uses the default working directory, timeout and retention, with no custom hooks. Shared hook handling is included automatically. No organization settings file or other modules are required. The pipeline must declare the selected stage, and its runner must be able to use the chosen image.
