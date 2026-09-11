# Defaults and organization profiles

Use two layers of ordinary GitLab YAML:

| Location | Owns |
|---|---|
| `templates/<module>.yml`, under `spec:inputs` | Module defaults, input types, hooks, output contract, and one job |
| `examples/full-pipeline/profile.yml` | Optional organization baseline: images, shared retention, timeouts, scanner policy, and application path defaults |
| Application `.gitlab-ci.yml` | Profile input overrides, stages, dependencies, hook scripts, and promotion rules |

Each module still works independently. Its `image` input is required, so a Maven job cannot silently inherit an npm image. There is no global `default:image`, separate per-module defaults file, configuration loader, or YAML generation step.

The organization profile composes the Maven + npm + Kubernetes baseline used by `examples/full-pipeline/application.gitlab-ci.yml`. It includes jobs but deliberately leaves `workflow`, `stages`, and `needs` to that application example. Use individual components for a smaller pipeline or a different architecture. Add extra steps as ordinary jobs with `needs`; see [extension patterns](hooks.md).

## Approved defaults and application overrides

The profile currently binds each image input to a separate group/project CI variable, such as `$MAVEN_BUILD_IMAGE`. Configure these with the approved digest-pinned images listed in [setup](setup.md). These bindings do not select or install images automatically. For a versioned organization image catalogue, replace the profile's image defaults with literal approved digest references and release the profile at an immutable commit.

```yaml
include:
  - project: platform/ci-components
    ref: REPLACE_WITH_COMMIT_SHA
    file: /examples/full-pipeline/profile.yml
    inputs:
      production-namespace: application-production
      test-url: https://$CI_PROJECT_ID-$CI_PIPELINE_ID.test.example.com
      production-url: https://application.example.com
      maven-directory: services/api
      npm-directory: web
      maven-build-image: registry.example.com/ci/maven@sha256:REPLACE_WITH_DIGEST
      artifact-expire-in: 30 days
      job-timeout: 45m
```

These overrides affect this inclusion. Each image has its own input, including separate test and production Helm images. The profile uses 30 minutes for ordinary jobs, one hour for Dependency-Check, and two hours for the Fortify scan. Adjust the longer jobs through `dependency-check-job-timeout` and `fortify-scan-job-timeout`; they do not inherit the ordinary timeout. GitLab Runner's maximum timeout remains an upper limit. Artifact retention defaults to seven days.

Inputs are scoped to the file declaring them. The profile explicitly passes values to its nested module includes; modules do not read the profile themselves. Nested `include:local` files resolve in the project and revision containing the profile. [GitLab inputs](https://docs.gitlab.com/ci/inputs/), [nested includes](https://docs.gitlab.com/ci/yaml/includes/)

## Hooks and individual modules

When consuming an individual module, pass `pre-hook`, `post-hook`, `cleanup-hook`, and `hook-parameters-json` as component inputs, as shown in [setup](setup.md#extending-a-module).

When using the full profile, application job overlays can set these runtime hook variables without replacing the component scripts:

```yaml
maven-build:
  variables:
    MODULE_PRE_HOOK: ci/hooks/pre-build.sh
    MODULE_POST_HOOK: ci/hooks/post-build.sh
    MODULE_CLEANUP_HOOK: ci/hooks/cleanup.sh
    MODULE_HOOK_PARAMETERS_JSON: '{"label":"candidate"}'
```

Scripts live in the consuming repository and receive the same hook context and output contract. Do not redefine `before_script`, `script`, or `after_script` to add a hook: GitLab replaces arrays instead of appending them. Job-level overrides are part of the application's trusted configuration; these defaults do not enforce security policy against an application author who can edit its pipeline. Keep credentials in protected variables or a secret manager, outside inputs and artifacts.

If a standard component replaces an implementation later, preserve the public input/output and documented hook contracts in its adapter. The organization profile is the place to change that component selection; it should not acquire build or deployment scripts.
