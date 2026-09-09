# Future option: reuse standard components

Current decision: use our own components, each maintained as an individual YAML file in `templates/`. This assessment records standard implementations we may adopt later. The public inputs, outputs, hooks, image requirements, and failure behavior form the contract a replacement must preserve or explicitly version. These components still require live integration validation before production adoption.

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

Our optional `handoff` component implements the extra explicit `next(work)` convention requested in this conversation. It is a small custom adapter over GitLab scheduling, not an industry-standard callback API. Prefer native template hooks for ordinary extensions. Add the handoff only where a separately imaged custom job and explicit continuation add value.

One logical component need not mean exactly one physical job. Vendor components may need preparation, scan, and report jobs. Keep one responsibility per building block where practical without dismantling a tested vendor workflow merely to impose a job-count rule.

## Standards alignment is a control-and-evidence exercise

| Reference | Relevant evidence | Prototype status |
|---|---|---|
| [NIST SSDF SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final) | Controlled toolchains, protected source/artifacts, defined testing and vulnerability response | Some pipeline patterns documented; organization practices and enforcement not configured |
| [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) | A selected set of application security requirements with verification evidence | Scanners cover only part; threat modeling, application assertions and manual verification still needed |
| [SLSA build requirements](https://slsa.dev/spec/v1.2/build-requirements) | Provenance tied to artifact digests, appropriate builder trust/isolation and verification | Digest promotion/signing demonstrated; provenance generation, distribution and builder assessment remain outstanding |

Image signatures and an SBOM alone do not establish a SLSA level. Likewise, successful scanner execution does not establish ASVS compliance, and an arbitrary 80% coverage threshold is organization policy rather than a universal standard.

Mandatory security controls must survive changes to application YAML and hooks. GitLab Ultimate offers [pipeline execution policies](https://docs.gitlab.com/user/application_security/policies/pipeline_execution_policies/) for central enforcement. On other editions, design equivalent protected release/policy controls with the capabilities available. Scanner reporting and policy enforcement are separate: explicitly configure how findings block merge or release.

## Replacement process if we adopt standard components later

1. Select one candidate implementation for a concrete need. The table above is an evaluation list, not a commitment to switch.
2. Compare its contract with our component: inputs, outputs, artifact paths, image/tool requirements, hook lifecycle, job dependencies, and failure behavior.
3. Pin the candidate's revision and images, review its license and runner requirements, and use supported extension points or a small adapter for any compatible differences.
4. Validate the replacement with contract checks and representative applications, including scanner errors, missing reports, failed hooks, and blocked production promotion. Version incompatible changes and migrate consumers explicitly.
5. Roll out one replacement at a time while retaining organization policy enforcement and evidence requirements. Continue assessing standards conformance independently of component sourcing.

The local contract tests pass, but no real GitLab pipeline, scanner, registry, Fortify service, KMS, or Kubernetes deployment has been exercised. The current implementation work is to configure and validate our own components against the organization's tool images and services. Standard component adoption remains a future option.
