# Extending jobs and pipelines

Use GitLab job dependencies for an extra pipeline step. Use the existing component hooks for small additions inside one job. The Java demo keeps these definitions in the central CI library; no CI scripts need to be added to its application repository.

## Extra step: a normal GitLab job

The following fragment adds a required check between existing `build` and `publish` jobs. The build publishes `package.jar` as an artifact; `check` is a declared stage. Set `CHECK_IMAGE` to an approved image containing POSIX shell and the tools needed for the real check.

```yaml
custom-check:
  stage: check
  image: $CHECK_IMAGE
  needs:
    - job: build
      artifacts: true
  script:
    - test -s package.jar

publish:
  needs:
    - job: build
      artifacts: true
    - job: custom-check
      artifacts: false
```

GitLab starts `publish` after both required jobs succeed. The check's exit status determines success. Listing `build` directly also supplies its files; artifacts are not automatically forwarded through intermediate jobs. Replace the illustrative non-empty-file check with the required business or technical validation. [GitLab needs](https://docs.gitlab.com/ci/yaml/needs/), [job artifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/).

For additional values, publish an `artifacts:reports:dotenv` file and import that job's artifacts with `needs`. For structured data, publish a JSON artifact. Keep secrets in GitLab's credential mechanisms. A step that changes an artifact must publish the replacement and arrange the required scans and verification for that replacement. [Dotenv variables](https://docs.gitlab.com/ci/variables/dotenv_variables/).

## Small addition inside a component

These optional component inputs are our library convention over GitLab's native job lifecycle:

| Component input | Execution | Failure behavior |
|---|---|---|
| `pre-hook` | During `before_script`, after common setup | Fails the job |
| `post-hook` | At the end of `script`, before outputs are published | Fails the job |
| `cleanup-hook` | During `after_script`, in a fresh shell | Best effort; cannot turn a successful job into a failure |

Required checks belong in `script` or their own required job. `after_script` is for cleanup. Each component references [shared/module.yml](../shared/module.yml) for these phases; its comments explain the YAML references. [GitLab job execution](https://docs.gitlab.com/ci/jobs/job_execution/).

Hook paths are relative to the consuming repository and are executed with `sh` in the component's working directory. They run as subprocesses; use files to pass results back. `hook-parameters-json` is written to `CI_MODULE_PARAMETERS_FILE`. Optional outputs go into `CI_MODULE_EXTRA_OUTPUTS` using the component prefix followed by `_CUSTOM_`. Hooks and outputs must not contain secrets. Examples of [pre-build](../examples/hooks/pre-build.sh), [post-build](../examples/hooks/post-build.sh) and [cleanup](../examples/hooks/cleanup.sh) remain available.

## Migration from the removed callback component

Replace the old continuation component with a normal job:

1. Keep the script's useful processing in that job's `script`, using the same required tool image.
2. Read upstream values through imported dotenv artifacts; remove the explicit continuation-helper call.
3. Publish any changed values or files as ordinary artifacts.
4. Make the next job depend on this job, and on any original producer whose files it still needs.

There is no replacement callback helper. GitLab owns scheduling. Runtime dotenv values cannot change the existing job graph; select jobs through pipeline inputs and `rules`, or use a child pipeline when runtime configuration requires one.
