# Pipeline choices

On **Build > Pipelines > New pipeline**, select the branch, then choose `cluster`, `user_config` and `pipeline_mode`. These fields also appear for `main`. The application imports the form definitions from [config/pipeline-inputs.yml](../config/pipeline-inputs.yml) and forwards the selections to the organization profile. Push and merge request pipelines use the defaults automatically.

The only static app settings are the pinned library revision and deployable Maven module. No scripts or stage definitions are copied into the app. The form definition and implementation have the same pinned revision; YAML anchors cannot cross the header's document separator, so that revision appears in both includes.

## Ten-second default

`configure` uses `when: delayed` and `start_in: 10 seconds`. After the pipeline has been created, GitLab schedules it using the selections from the form, or `local`, `default` and `deploy` for an automatic/default run. Runner availability determines when execution actually starts.

To change values after starting the pipeline, select **Unschedule** on `configure` before the timer expires. Open the job, set its inputs and select **Run job**. Unscheduling stops the timer, so the job waits for this explicit run. GitLab does not automatically submit the New pipeline page: its timer applies to the job in a created pipeline. [Delayed jobs](https://docs.gitlab.com/ci/jobs/job_control/#run-a-job-after-a-delay), [job inputs](https://docs.gitlab.com/ci/jobs/job_inputs/).

Follow **run-pipeline** to the executing jobs. The selected values and the pinned library revision are recorded in the configuration artifact; the resulting child pipeline uses those fixed settings.

| Input | Default | Effect |
|---|---|---|
| `cluster` | `local` | Choose a centrally configured cluster and its cluster values |
| `user_config` | `default` | Choose additional Helm values from the application |
| `pipeline_mode` | `deploy` | Choose how far the ordinary pipeline runs |

| Mode | Jobs |
|---|---|
| `validate` | Maven build and Cucumber tests |
| `publish` | Build/tests, Maven packages, Jib image and Helm chart |
| `deploy` | Publication, Helm deployment and Cucumber against the running application |

Publication and deployment remain restricted to the protected default branch. Feature branches and merge requests run build/tests regardless of the selected mode. Reduced modes omit dependent jobs as a group. A release requires the full deployment flow and runs its own build, tests and release checks.

## Values in the application

```text
environment/
  cluster/local.yaml
  user/default.yaml
  user/two-replicas.yaml
```

The path is relative to the application repository, not the filesystem root. The organization profile has an optional `environment-directory` input; the demo uses its `environment` default.

Helm applies chart defaults, then the cluster file, then the user file. A later file overrides the same key in an earlier file. The explicit image digest remains final. The `default` user file is empty (`{}`); `two-replicas` changes only the replica count. [Helm values precedence](https://docs.helm.sh/docs/helm/helm_upgrade/).

These files contain Helm values, not cluster credentials. The current lab has one real cluster: `local`, mapped centrally to the protected `LOCAL_KUBECONFIG` file variable. Add real credentials, target URLs and a central mapping before adding another cluster choice. Update the profile's user choices when adding another user values file; GitLab does not dynamically populate these choices from directory contents.
