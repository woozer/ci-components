# Parameters and continuation

Pre/post hooks extend one component's job. A separate `handoff` job supports **module → hook → next module**, with an image chosen for the custom script.

Every component accepts `hook-parameters-json`. Its non-secret JSON configuration is written to `CI_MODULE_PARAMETERS_FILE`. Hook scripts parse that file using their image's tooling. Credentials stay in scoped secret-manager/environment inputs.

The handoff accepts `work-variable` (the name of an upstream dotenv output) and `hook` (a script in the consuming repository). It provides:

| Environment variable | Purpose |
|---|---|
| `CI_HOOK_WORK` | Upstream image reference, URL, artifact path, or other single-line value |
| `CI_MODULE_PARAMETERS_FILE` | JSON parameter file |
| `CI_HOOK_NEXT` | Executable helper to request continuation |
| `CI_MODULE_EXTRA_OUTPUTS` | File for `<PREFIX>_CUSTOM_...` output variables |

```yaml
stages: [package, handoff, supply-chain]
include:
  - component: $CI_SERVER_FQDN/platform/ci-components/image-build@REPLACE_WITH_COMMIT_SHA
    inputs:
      image: $IMAGE_BUILD_IMAGE
  - component: $CI_SERVER_FQDN/platform/ci-components/handoff@REPLACE_WITH_COMMIT_SHA
    inputs:
      job-name: custom-check
      image: $HANDOFF_IMAGE
      output-prefix: CUSTOM_CHECK
      work-variable: IMAGE_BUILD_IMAGE_REF
      hook: ci/hooks/check-image.sh
      hook-parameters-json: '{"requireDigest":true}'
  - component: $CI_SERVER_FQDN/platform/ci-components/image-scan@REPLACE_WITH_COMMIT_SHA
    inputs:
      image: $IMAGE_SCAN_IMAGE
      image-ref-variable: CUSTOM_CHECK_WORK_VALUE

custom-check:
  needs:
    - job: image-build
      artifacts: true
image-scan:
  needs:
    - job: custom-check
      artifacts: true
```

The application's hook implements its own work, then requests continuation:

```sh
#!/bin/sh
set -eu
./ci/company-check.sh "$CI_MODULE_PARAMETERS_FILE" "$CI_HOOK_WORK"
"$CI_HOOK_NEXT" "$CI_HOOK_WORK"
```

Calling `"$CI_HOOK_NEXT"` with no argument forwards the original value. One argument replaces it. The resulting `<PREFIX>_WORK_VALUE` becomes available to the next job.

`next` is a small custom helper, not a built-in GitLab feature. It records a continuation request; GitLab schedules the configured next job **after the hook job succeeds**, in that job's own image. The hook cannot synchronously call the downstream job or wait for its return value. The consumer's `needs` graph selects the next job and retains mandatory policy checks.

No call to `next`, hook failure, or a failure after calling `next` blocks the chain. A duplicate call returns an error; scripts must propagate errors with `set -eu`. This is a contract for trusted scripts, not a sandbox against a script deliberately changing its own job files.

If a hook changes an image, it must output a new immutable digest and the remaining chain must scan, sign, and verify that replacement before deployment. Keep checks placed after signature verification read-only with respect to the artifact. Required policy gates must remain outside a consumer's ability to remove them.

Dotenv transfers values, not file contents. For work referencing a file, the hook must import the producer's artifacts. A later job needing the original bytes must also import that producer or the handoff must explicitly republish the required paths. Requiring both producer and handoff does not bypass the handoff: GitLab waits for all `needs` entries. For structured work, publish a JSON artifact and pass its relative path.

Choosing a different set of jobs at runtime requires a separately designed dynamic child pipeline; dotenv values are unavailable to `rules` and `include`. [GitLab dotenv](https://docs.gitlab.com/ci/variables/dotenv_variables/), [dynamic child pipelines](https://docs.gitlab.com/ci/pipelines/downstream_pipelines/#dynamic-child-pipelines)

The executable example in `examples/hooks/handoff.sh` uses Python 3 in the hook image to read JSON parameters and then calls `next`.
