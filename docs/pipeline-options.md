# Pipeline choices (reference)

For daily use, see the [three actions](../README.md#three-everyday-actions). Build and required tests start immediately. Application CI imports the shared [New pipeline form](../config/pipeline-inputs.yml) and one [central pipeline](../pipelines/java-service.yml), using the same pinned revision. Only `library-ref` and `maven-project` are required static app settings; form values are forwarded without repeating defaults.

Pipeline names use native [`workflow:name`](https://docs.gitlab.com/ci/yaml/#workflowname): **CI — <branch>**, **Dev — deployment en integratietests**, **Release — <version>**. The version is fixed in the release child configuration after reservation. The triggers do not inherit parent variables, so the parent name cannot override the child name.

## Choose before starting

On **Build > Pipelines > New pipeline**, select the branch and these inputs. Push pipelines use their defaults.

| Input | Default | Effect |
|---|---|---|
| `cluster` | `local` | Initial development cluster |
| `user_config` | `default` | Initial additional Helm values |
| `pipeline_mode` | `deploy` | Which jobs the pipeline includes |

| Mode | Jobs on protected main |
|---|---|
| `validate` | Backend/UI builds and required tests; optional custom backend test |
| `publish` | Also publish Maven packages, backend/UI images and Helm charts |
| `deploy` | Also choose deployment settings, run Helm and test the deployment; offer **start-release** |

Feature branches and merge requests run build/tests only. `pipeline_mode` is fixed when the pipeline is created. This follows GitLab's native configuration-input model; job inputs cannot change `rules` or add stages during execution. [Input scope](https://docs.gitlab.com/ci/inputs/), [job input limitations](https://docs.gitlab.com/ci/jobs/job_inputs/#where-you-can-use-job-inputs).

## Choose tests during development

Open the **test-custom** job by clicking its name, choose `not @ui and not @ignore` (the complete backend suite) or `@smoke and not @ui`, then select **Run job**. The demo's greeting check is tagged `@smoke`; the backend suite also checks health, animals and that an unknown endpoint returns 404. Use **Retry job with modified values** to run a different selection. The selected expression is recorded in the job's output artifact as `CUCUMBER_TEST_TAGS`. [Native GitLab job inputs](https://docs.gitlab.com/ci/jobs/job_inputs/).

This optional developer job does not qualify a merge or release. The separate mandatory **test** and release tests always run their complete configured suite. Browser scenarios run separately in **cucumber-ui** after both deployments are ready. A green pipeline can coexist with a failed optional custom test; inspect that job's own status and report.

This choice selects Cucumber scenarios. It is not a Spring or Maven profile. The standalone Cucumber component still supports its optional Maven `profile` input; add actual application profiles before exposing them as choices. Run the same smoke selection locally with `./mvnw -Dcucumber.filter.tags="@smoke and not @ui" verify`.

## Choose deployment after publication

**configure-deploy** is scheduled after image and chart publication succeeds. Its ten-second timer applies here, rather than before the build. With no action, it uses the initial `cluster` and `user_config` values. Runner availability determines when it actually executes.

To change them, choose **Unschedule** before the timer expires, open the job and run it with the desired inputs. Unscheduling stops the timer until the user runs the job. This is our convenience policy using GitLab delayed jobs, not an automatic popup. [Delayed jobs](https://docs.gitlab.com/ci/jobs/job_control/#run-a-job-after-a-delay).

**deploy-dev** starts one child containing **helm-deploy** and **cucumber-dev**. The child uses the same central YAML and downloads the image digest and chart reference from the exact parent pipeline. The parent trigger holds the development lock until both jobs finish. [Parent pipeline artifacts](https://docs.gitlab.com/ci/yaml/#needspipelinejob), [resource groups](https://docs.gitlab.com/ci/resource_groups/).

With `ui-directory` configured, this child also deploys the UI and runs **cucumber-ui**. Both Cucumber jobs depend on both Helm deployments succeeding. This also applies to release delivery. The build-time tests still run before deployment.

## Wait for healthy deployments

Helm uses its native readiness wait and rollback on failure. Kubernetes calls the sample's backend `/actuator/health/readiness` and UI `/healthz` every 10 seconds (`periodSeconds: 10`); it can check an unready container sooner. Healthy endpoints return HTTP 200. The charts set `maxUnavailable: 0`, requiring all desired replicas to become ready during rollout. No CI polling script is needed. [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/), [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/).

The central pipeline's optional `deployment-timeout` defaults to `5m` per Helm deployment. To override it, add only the changed value to the existing java-service include:

```yaml
inputs:
  # Keep the existing required inputs here.
  deployment-timeout: 8m
```

The setting carries through deployment and release child pipelines. It is a Helm operation timeout, not a deadline for the whole pipeline; rollback can take additional time. Keep it comfortably below the Helm job's default 30-minute limit. A standalone `helm-deploy` component exposes `timeout` and `job-timeout` separately. A failed or timed-out Helm job prevents both deployed integration suites from starting, even if rollback restores the previous healthy version.

Readiness checks each process's availability. UI health does not call the backend; Cucumber and Playwright verify the complete UI-to-backend behavior after both processes are ready. Liveness checks remain independent of external services, following [Spring Boot's probe guidance](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html#actuator.endpoints.kubernetes-probes).

## Deploy the same build with different values

1. Open the successful pipeline's **configure-deploy** job and use **Retry job with modified values**.
2. Select another Helm user profile and wait for the job to succeed.
3. Use **Run again** on the **deploy-dev** trigger. This recreates the complete deployment child, including its Cucumber test, under the same lock.

Retrying the selector alone does not automatically rerun a completed downstream job. The image and chart are reused; build and publication do not run again. Parent job artifacts must still be available (the default retention is seven days). [Recreate a downstream pipeline](https://docs.gitlab.com/ci/pipelines/downstream_pipelines/#recreate-a-downstream-pipeline).

## Helm files and credentials

```text
environment/
  cluster/local.yaml
  user/default.yaml
  user/two-replicas.yaml
```

Helm applies chart defaults, cluster values, then user values. The explicit image digest remains final. `default` is empty; `two-replicas` sets the replica count to two.

The only provisioned cluster is `local`, mapped centrally to `LOCAL_KUBECONFIG` and the development URLs. Credentials are GitLab variables, never values-file contents. Add actual credentials and a central mapping before exposing another cluster. Choices are explicit; GitLab does not discover dropdown options from directories.
