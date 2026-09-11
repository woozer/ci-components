# Future option: reuse standard components

Current decision: use our own components, with active modules in `templates/` and unused modules in `modules/todo/`, each maintained as an individual YAML file. This assessment records standard implementations we may adopt later. The public inputs, outputs, hooks, image requirements, and failure behavior form the contract a replacement must preserve or explicitly version. These components still require live integration validation before production adoption.

## Working agreement for changes

Prefer supported GitLab features over custom orchestration. For each proposed or implemented change, check the relevant standard or established practice and the existing supported implementations. Distinguish formal standards, platform features, common practice, organization policy, and custom behavior; these are not interchangeable claims.

When we choose a deviation, explain the conventional alternative, our reason, and the practical consequences for consumers, maintenance, compatibility, or assurance. Use primary documentation to support the assessment where needed, and state uncertainty instead of claiming a universal standard. Record material accepted deviations in the documentation for the affected feature. Keep this assessment proportional to the change and within the user's existing authorization.

## Deliberate choices in the demo

| Choice | Standard mechanism or conventional alternative | Reason and consequence |
|---|---|---|
| Automatic required tests plus an optional custom Cucumber run | Native GitLab job inputs and ordinary mandatory CI tests | Developers can select scenarios without weakening the required test. Optional failures do not make the whole pipeline fail. |
| Ten seconds to change deployment settings | GitLab delayed jobs; manual deployment or defaults selected before pipeline creation are simpler alternatives | Preserves the requested choice after an automatic start. Requires Unschedule, then an explicit run; there is no popup. |
| One central YAML for normal, deployment and release flows | Native includes, rules, dynamic child pipelines and resource groups | One place to read the composition. The internal `flow` input selects jobs; deployment remains a child so its lock spans Helm and Cucumber. |
| Our own task components | Supported tool CLIs/plugins and maintained components listed below | Keeps the agreed input/output/hook contract; we own maintenance and integration testing. |
| Automatic next patch release | SemVer defines version meaning; it does not mandate automatic patch bumps | An organization convenience policy. A developer must still request a minor/major version when compatibility changes require it. |

The native GitLab features are documented in [job inputs](https://docs.gitlab.com/ci/jobs/job_inputs/), [downstream pipelines](https://docs.gitlab.com/ci/pipelines/downstream_pipelines/) and [resource groups](https://docs.gitlab.com/ci/resource_groups/). Our delay and version policies are not formal industry standards.

## Available implementations

| Capability | Existing implementation to evaluate | What the organization still owns |
|---|---|---|
| Maven build/test | [to be continuous Maven component](https://to-be-continuous.gitlab.io/doc/ref/maven/) and Maven's standard plugins | JDK/tool versions, parent POM, test profiles, repository configuration |
| npm build/test | [to be continuous Node.js component](https://to-be-continuous.gitlab.io/doc/ref/node/) | Lockfiles, build/test scripts, supported Node version |
| Helm deployment | [to be continuous Helm component](https://to-be-continuous.gitlab.io/doc/ref/helm/) | Chart, image digest mapping, environments, RBAC, approvals |
| Sonar analysis and gate | SonarScanner's native `sonar.qualitygate.wait=true`; the [to be continuous Sonar component](https://to-be-continuous.gitlab.io/doc/ref/sonar/) is another integration option | Quality profile, gate policy, coverage paths, server credentials |
| Fortify | [OpenText Fortify AST Scan component](https://gitlab.com/Fortify/components/ast-scan) or [Fortify fcli component](https://fortify.github.io/fcli/v3/ci/gitlab/v2.0.x/fcli-component.html) for custom sequences | SSC/ScanCentral versus FoD configuration, licensing, security policy, result mapping |
| Dependency, container, and secrets scans | [GitLab security templates/components](https://docs.gitlab.com/user/application_security/detect/security_configuration/) where your edition supports them | Severity policy, exceptions, feed freshness, required merge/release controls |
| Specifically OWASP Dependency-Check | [Official Maven plugin](https://dependency-check.github.io/DependencyCheck/dependency-check-maven/check-mojo.html) | Plugin version, NVD feed access, CVSS threshold, reviewed suppressions |
| Image signing | [Sigstore Cosign](https://docs.sigstore.dev/cosign/key_management/overview/) | KMS/OIDC trust, signing permissions, verification/admission policy |
| OWASP runtime scanning | [ZAP packaged scans](https://www.zaproxy.org/docs/docker/baseline-scan/) | Target/authentication, scan scope, active versus passive testing, policy |
| Cucumber integration tests | [Maven Failsafe's Cucumber support](https://maven.apache.org/components/surefire/maven-failsafe-plugin/examples/cucumber.html) | Your scenarios, runner, target URL, test data and assertions |

These are maintained implementations, not all official GitLab products. **to be continuous is a third-party component suite**; assess its maintenance, license, compatibility, and support model. A catalog listing is discovery, not security certification. Published upstream examples can contain floating versions or images; select and test exact versions before rollout.

## How much of the requested architecture already exists?

- Components already accept configurable inputs and select job images.
- GitLab's `needs` plus artifacts/dotenv already provides job ordering and runtime output handoffs. We do not need another pipeline execution engine.
- The to be continuous architecture already uses dotenv outputs between templates. Its deployment templates expose environment information for downstream acceptance tests. Existing hook and command-extension support varies by template; confirm exact failure semantics in the selected release. [Architecture](https://to-be-continuous.gitlab.io/doc/dev/architecture/)
- SonarScanner already waits for its quality gate. Combining analysis and the associated gate in one logical component is a reasonable single-responsibility exception and removes custom polling code. [Sonar parameters](https://docs.sonarsource.com/sonarqube-server/2026.1/analyzing-source-code/analysis-parameters/parameters-not-settable-in-ui)
- Fortify already supplies a complete AST workflow and a lower-level fcli component. Reuse its setup and scan handling; customize only where organization policy or edition-specific integration requires it.

The custom `handoff` component and its `next(work)` callback protocol have been removed. Extra processing is an ordinary GitLab job with its own image and `needs` dependencies. GitLab schedules the next required job after successful completion; artifacts and dotenv carry results. Consumers of an older pinned revision must migrate that component before upgrading. See [extension patterns](hooks.md).

One logical component need not mean exactly one physical job. Vendor components may need preparation, scan, and report jobs. Keep one responsibility per building block where practical without dismantling a tested vendor workflow merely to impose a job-count rule.

## Standards alignment is a control-and-evidence exercise

| Reference | Relevant evidence | Prototype status |
|---|---|---|
| [NIST SSDF SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final) | Controlled toolchains, protected source/artifacts, defined testing and vulnerability response | Some pipeline patterns documented; organization practices and enforcement not configured |
| [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) | A selected set of application security requirements with verification evidence | Scanners cover only part; threat modeling, application assertions and manual verification still needed |
| [SLSA build requirements](https://slsa.dev/spec/v1.2/build-requirements) | Provenance tied to artifact digests, appropriate builder trust/isolation and verification | Digest-based deployment exercised; signing, provenance generation/distribution and builder assessment remain outstanding |

Image signatures and an SBOM alone do not establish a SLSA level. Likewise, successful scanner execution does not establish ASVS compliance, and an arbitrary 80% coverage threshold is organization policy rather than a universal standard.

Mandatory security controls must survive changes to application YAML and hooks. GitLab Ultimate offers [pipeline execution policies](https://docs.gitlab.com/user/application_security/policies/pipeline_execution_policies/) for central enforcement. On other editions, design equivalent protected release/policy controls with the capabilities available. Scanner reporting and policy enforcement are separate: explicitly configure how findings block merge or release.

## Replacement process if we adopt standard components later

1. Select one candidate implementation for a concrete need. The table above is an evaluation list, not a commitment to switch.
2. Compare its contract with our component: inputs, outputs, artifact paths, image/tool requirements, hook lifecycle, job dependencies, and failure behavior.
3. Pin the candidate's revision and images, review its license and runner requirements, and use supported extension points or a small adapter for any compatible differences.
4. Validate the replacement with contract checks and representative applications, including scanner errors, missing reports, failed hooks, and blocked production promotion. Version incompatible changes and migrate consumers explicitly.
5. Roll out one replacement at a time while retaining organization policy enforcement and evidence requirements. Continue assessing standards conformance independently of component sourcing.

The local lab has exercised GitLab pipelines, Maven publication, Jib/Helm publication to Artifactory, Kubernetes deployment, Cucumber and release protections. Scanner, Fortify and KMS/signing integrations still require live validation. Standard component adoption remains a future option.

The [deployment concurrency investigation](deployment-concurrency.md) compares ordinary jobs with the current child pipeline. GitLab supports `oldest_first` for pipeline ordering; local experiments also show why older-job retries need additional treatment. It records options and evidence without changing the current delivery policy.

## Angular UI and browser tests

The optional `ui-directory` activates the existing npm/image/Helm modules in the same central pipeline. Native `rules`, `needs` and artifacts connect the jobs. Backend and UI have separate images, Helm releases and deployments; one repository release versions both. This is an organization composition, not a new pipeline engine or a formal standard. More deployables can consume the individual modules; this demo composition deliberately supports one backend and one UI.

The UI uses the current stable Angular CLI workspace, a lockfile and `npm ci`. The [maintained unprivileged Nginx image](https://github.com/nginx/docker-nginx-unprivileged) serves static files and proxies `/api/` to the backend. Its supported environment-template mechanism configures the backend URL. Both deployments accept the selected cluster/user values; chart-specific settings such as the service port stay in each chart's defaults.

Dockerfile images use [GitLab's documented rootless BuildKit method](https://docs.gitlab.com/ci/docker/using_buildkit/). In this Docker Desktop lab, a dedicated `local-buildkit` runner uses Docker's default seccomp profile plus `clone`, `unshare`, `setns`, `mount` and `umount2`. The runner remains unprivileged and does not mount the Docker socket into jobs. This is local runner configuration that must be reviewed for another host, not an application hook. The tool image adds Python for registry authentication and metadata parsing. The Java image still uses Jib.

Cucumber UI scenarios call the official [Playwright Java API](https://playwright.dev/java/docs/test-runners) with headless Chromium. Headless still requires a browser engine. The existing Cucumber component selects a [Playwright browser image](https://playwright.dev/java/docs/docker) extended with our Java 25 and Maven versions; ordinary backend tests retain the smaller Java image. The browser and Java dependency versions must match. The CI browser runs against our own test application with the image's default settings; this image is not intended for arbitrary untrusted browsing.

`@ui` scenarios run after both deployments and block completion of the release. They compare the rendered table to the browser's actual API response, refresh the list and verify a mobile viewport. Screenshots are embedded in the Cucumber report; failures also preserve Playwright traces. No custom Cucumber/Playwright adapter service is needed.
