# Deployment without a child pipeline

Investigation, 11 September 2026, GitLab CE 19.3.1. This records options and measured behavior; it does not change the application's current delivery strategy.

## Conclusion

Ordinary jobs can serialize a deployment/test sequence using GitLab's `oldest_first` resource-group process mode. GitLab Support explicitly documents this alternative to child pipelines. The earlier assessment that resource groups could only protect individual jobs was incomplete: ordered scheduling also considers future jobs in older pipelines.

However, this is not a drop-in replacement for our current behavior. Retrying an older deployment while a newer pipeline is between deployment and verification can interrupt that newer sequence. We reproduced this on the local GitLab instance. Arbitrary old-job retries and delayed activation of release jobs require separate consideration.

For the existing shared dev environment, the child pipeline remains the smallest proven implementation that combines separate tool images, a complete delivery lock, and rerunning the entire deployment/test sequence. Flattening is possible, but requires choosing a different operational tradeoff below.

## The supported ordinary-job pattern

GitLab Support describes a job at the start and end of a sequence, both using the same `resource_group`, configured with `process_mode: oldest_first`. The final job must depend on all protected work; jobs inside the sequence must depend on its start. Alternatively, assign the same group to each Helm and integration-test job, which also serializes those jobs within one pipeline.

The process mode is project/resource-group configuration through the GitLab API, not a `process_mode` key inside `.gitlab-ci.yml`. It must be configured before relying on the ordering. GitLab also exposes a project default for newly created resource groups; existing groups must be checked separately. Do not change every group's policy implicitly when only dev delivery needs this behavior.

`oldest_first` considers jobs in `created`, `scheduled`, and `waiting_for_resource` states. Therefore a future verification job in pipeline A can keep pipeline B's deployment waiting. `needs` and stages still define the order inside each pipeline. Conditional jobs, manual gates, failure/skip paths and retries must be checked; a future job that remains blocked can also delay newer deliveries.

Sources: [GitLab Support: pipeline-level concurrency](https://support.gitlab.com/hc/en-us/articles/21727269790620-Achieve-Pipeline-level-concurrency-with-resource-group-CI-CD-keyword), [resource-group modes](https://docs.gitlab.com/ci/resource_groups/#process-modes), [Projects API](https://docs.gitlab.com/api/projects/). We also inspected the installed `Ci::ResourceGroup#upcoming_processables` scheduler implementation.

## Local experiment

The archived [CI ordering lab](http://localhost:8929/root/ci-ordering-lab) uses harmless jobs that print their pipeline ID and pause. It does not deploy or modify the application. Its graph is `deploy → between → verify`; `deploy` and `verify` share an `oldest_first` resource group. The middle job models time between deployment and verification.

**Normal concurrent pipelines:** [128](http://localhost:8929/root/ci-ordering-lab/-/pipelines/128) and [129](http://localhost:8929/root/ci-ordering-lab/-/pipelines/129) completed in this order:

```text
128: deploy → between → verify
129: deploy → between → verify
```

**Older-job retry:** while new pipeline 130 was deploying, we retried pipeline 128's already completed deployment. All individual jobs succeeded, but their order was:

| Event | Evidence | UTC time |
|---|---|---|
| New pipeline 130 finishes deployment | [Job 368](http://localhost:8929/root/ci-ordering-lab/-/jobs/368) | 13:13:14.486 |
| Old pipeline 128's deployment retry starts | [Job 371](http://localhost:8929/root/ci-ordering-lab/-/jobs/371) | 13:13:32.249 |
| Old deployment retry finishes | Job 371 | 13:13:55.898 |
| New pipeline 130 starts verification | [Job 370](http://localhost:8929/root/ci-ordering-lab/-/jobs/370) | 13:13:57.989 |

This proves that the ordered group can allow an older deployment retry between a newer deployment and its test. In a shared environment, that test could therefore examine the older application. Retrying the deployment did not rerun its already successful downstream tests automatically.

The first two lab pipelines, 126/127, failed while pulling the runner helper before any experiment job ran. After configuring the existing read-only pull credentials, 128–130 produced the scheduling evidence above.

The experiment tests retries directly. The corresponding concern about activating manual release jobs later in an older pipeline is an inference from the same pipeline-ID scheduling rule, not a separately executed release experiment.

## Alternatives and tradeoffs

| Approach | Protection | Consequence for our sample |
|---|---|---|
| Current child plus `resource_group` and `strategy: mirror` | The trigger holds the dev lock until all Helm and integration jobs finish | Separate images and one complete delivery retry are preserved; GitLab displays the child on the right |
| Ordinary jobs with `oldest_first` | Serializes normally progressing pipelines; old retries can interrupt a newer sequence | Requires a controlled restart/release workflow; not equivalent to the current behavior |
| One ordinary delivery job holding the lock | Covers the whole deployment/test operation, including retries | Separate CI jobs become one job; use a combined tool image or move acceptance tests into Kubernetes Jobs |
| Isolated environment per pipeline | Another pipeline deploys elsewhere, so it cannot replace the application under test | Keeps separate jobs/images; adds environment routing, resource limits, credentials and cleanup |

### One delivery job with Helm hooks

Helm can run Kubernetes Job hooks after install/upgrade. With readiness waiting enabled, the post-install hook runs after the release's resources are ready; Job hooks must complete for Helm to finish. Tests can use their own browser image in the cluster, while the CI job uses only Helm. A single CI resource group can then protect the complete operation.

For our two deployables, this would need a combined release such as an umbrella chart, or one job that deploys both charts before running acceptance tests. The existing Cucumber/Playwright tests would need a version-matched test image and a way to return their reports to GitLab. Helm hook resources also need cleanup policies. This is supported Helm behavior, but it is a larger change than flattening YAML.

`helm test` runs test hooks explicitly. It is not automatically covered by a previous successful `helm upgrade --rollback-on-failure`; post-install/post-upgrade verification and a separate `helm test` command have different rollback semantics. [Helm hooks](https://helm.sh/docs/topics/charts_hooks/), [Helm chart tests](https://helm.sh/docs/topics/chart_tests/).

### Isolated environments

GitLab dynamic environments and review apps are a conventional alternative. For concurrent pipeline tests, use an environment/release namespace unique to the pipeline, not only the branch: two pipelines of one branch can overlap. Backend, UI and their test targets must all point to that same isolated environment. GitLab's environment record alone does not create or isolate Kubernetes resources. [Review apps](https://docs.gitlab.com/ci/review_apps/).

This fits concurrent development well, but changes the current stable `localhost:8080` / `localhost:8090` experience and requires routing and cleanup. Shared external test data would need isolation too if the application gains state.

## A possible flat workflow with fresh delivery pipelines

If we choose ordinary jobs with `oldest_first`, a practical direction is to make each delivery attempt a new pipeline rather than retrying mutation jobs in an older pipeline:

- A main pipeline builds, publishes, deploys and verifies through ordinary jobs.
- The manual release button can still reserve a protected tag. A native tag pipeline then builds and delivers that release with its own pipeline ID. This is a separate top-level pipeline, not the same graph and not a child. [GitLab release examples](https://docs.gitlab.com/user/project/releases/release_cicd_examples/).
- Redeployment would start a new deployment-only pipeline using the existing immutable artifacts and chosen profile. Artifact resolution and test-source provenance must be designed before replacing the current parent-artifact links.

This changes the user workflow and does not itself prevent someone from retrying an old job. Outdated-deployment protection can help enforce parts of that policy but is not a lock spanning deployment and tests. Do not present a convention alone as equivalent protection. [Deployment safety](https://docs.gitlab.com/ci/environments/deployment_safety/).

Cluster/profile choices can remain native job inputs, with a delayed default and dotenv outputs consumed by ordinary jobs. They do not intrinsically require a child pipeline. Runtime dotenv values cannot choose new jobs through `rules`; use a resource-group key known when the pipeline is created. [Dotenv variables](https://docs.gitlab.com/ci/variables/dotenv_variables/).

The next design decision is therefore which requirement can change: the shared environment, separate CI jobs/tool images, or the existing retry/release workflow. No custom lock service or continuation engine is proposed.
