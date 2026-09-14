# Instellingen van de demo

Het organisatiebestand [config/organization.yml](../config/organization.yml) bevat gedeelde serveradressen en imagekeuzes. Het voegt geen jobs toe. De applicatie neemt [java-service.yml](../pipelines/java-service.yml) rechtstreeks op. Die samenstelling bepaalt de modules, jobvolgorde en standaardwaarden op basis van de projectnaam.

Voor eigen serveradressen, credentials en OpenShift beschrijft [gebruik in de eigen organisatie](real-environment.md) de verdeling van instellingen en de configureerbare platformkeuzes.

| Instelling | Doel |
|---|---|
| `GITLAB_INTERNAL_URL` | GitLab-adres dat bereikbaar is vanuit jobcontainers |
| `ARTIFACTORY_PUBLIC_URL` | Browseradres voor release-artifactlinks, zonder toegangsgegevens |
| `OCI_REGISTRY` | Registry-adres voor Jib en Helm |
| `DEV_TARGET_URL`, `DEV_PUBLIC_URL` | Dev-URL voor respectievelijk CI en de GitLab-interface |
| `registry-plain-http` (pipeline-input) | Bewust ingeschakelde HTTP-toegang voor de lokale demo; zet op `false` voor HTTPS |
| `OCI_REPOSITORY` | Artifactory-repository voor images en charts |
| `MAVEN_PUBLISH_URL`, `MAVEN_PUBLISH_SERVER_ID` | Maven-publicatieadres en bijbehorende server-ID in Maven-settings |
| `MAVEN_BUILD_IMAGE`, `MAVEN_PUBLISH_IMAGE` | Images voor de twee Maven-taken |
| `CUCUMBER_TEST_IMAGE`, `JIB_BUILD_IMAGE` | Images voor HTTP-tests en Jib |
| `HELM_PUBLISH_IMAGE`, `HELM_DEPLOY_IMAGE` | Images voor chartpublicatie en deployment |
| `JIB_BASE_IMAGE` | Java-runtime in de applicatie-image |

GitLab-variabelen selecteren images voor Java/Maven, Node, BuildKit, Helm en Playwright, vastgezet op digest. Andere variabelen kiezen de Java- en Nginx-runtime. Deze zijn al ingesteld in de lokale testomgeving. Pas de koppeling van een taak aan om een andere goedgekeurde image te gebruiken, of vul een volledige imagereferentie met digest in. Groeps- en projectvariabelen kunnen YAML-standaardwaarden overschrijven.

**Toegangsgegevens en omgevingen** beheer je via GitLabs CI/CD-variabelen:

| Variabele | Opslag en gebruik |
|---|---|
| `LOCAL_KUBECONFIG` | Protected bestandsvariabele met Kubernetes-API-URL, CA en deploymentcredentials |
| `ARTIFACTORY_MAVEN_SETTINGS` | Protected bestandsvariabele met registry-toegangsgegevens voor Maven/Jib |
| `ARTIFACTORY_USERNAME` | Protected variabele met het registry-account voor publicatie |
| `ARTIFACTORY_PASSWORD_FILE` | Protected, masked bestandsvariabele met het publicatiewachtwoord |
| `DOCKER_AUTH_CONFIG` | Masked variabele met lees-/cachetoegang tot de registry voor de runner |
| `CI_JOB_TOKEN` | Automatisch geleverd door GitLab voor publicatie van Maven-packages |

De sample deployt naar lokaal Kubernetes. Voor OpenShift kun je dezelfde module `helm-deploy` gebruiken met een OpenShift-kubeconfig. Beperk deploymentcredentials tot de bijbehorende GitLab-omgeving, bijvoorbeeld `dev/local`, `dev/openshift-test` of `release/dev/openshift-test`, en geef alleen toegang tot de benodigde namespace. Publicatiejobs moeten ook over hun registry-credentials kunnen beschikken. Zet geen toegangsgegevens in de organisatie-YAML, hookparameters of outputartifacts.

**De vaste applicatie-instellingen zijn de verplichte inputs `library-ref` en `maven-project`.** De demo schakelt de aparte UI in met `ui-directory: ui`. Daarnaast geeft de applicatie keuzes uit het gedeelde formulier **New pipeline** door. De standaardpipeline gebruikt `$CI_PROJECT_NAME` als applicatienaam en namespace, `helm/$CI_PROJECT_NAME` als chartpad en `environment/` als configuratiemap. Lokale URL's, HTTP-toegang tot de registry en de koppeling tussen cluster en kubeconfig staan centraal bij de organisatie-instellingen. De applicatie herhaalt geen standaardwaarden. Stages, afhankelijkheden en hooks staan in de centrale strategie.

Na publicatie kiest de job `configure-deploy` de waarden van `cluster` en `user_config`, met standaard tien seconden wachttijd. `pipeline_mode` kies je vóór het aanmaken van de pipeline. De optionele job `test-custom` accepteert een Cucumber-tagselectie; verplichte tests houden hun vaste configuratie. Zie [pipelinekeuzes](pipeline-options.md).

**Standaardwaarden van modules** staan in hun eigen `spec:inputs`. Afnemers kunnen deze inputs weglaten:

| Input | Standaardwaarde voor de demomodules |
|---|---|
| `artifact-expire-in` | `7 days` |
| `job-timeout` | `30m` |
| `working-directory` | `.` |
| `output-prefix` | Modulespecifiek, bijvoorbeeld `MAVEN_BUILD` |
| `maven-executable` | `./mvnw` in Maven-, Jib- en Cucumber-modules |
| `pre-hook`, `post-hook`, `cleanup-hook` | Leeg: geen hook |
| `hook-parameters-json` | `{}` |
| Cucumber `profile` | Leeg: geen Maven-profiel |

Stel bijvoorbeeld alleen `artifact-expire-in: 30 days` in als een job een langere bewaartermijn nodig heeft. `image` blijft verplicht, zodat elke module expliciet een image kiest. Zie [verplichte inputs per module](inputs.md) voor het volledige overzicht en de voorwaarden bij uitvoering.

Inputdeclaraties staan in elke component, omdat hun bereik beperkt is tot het bestand dat ze declareert. GitLabs `spec:include` ondersteunt gedeelde definities voor pipeline-inputs, maar niet voor component-inputs. De gedeelde hookcode staat in `shared/module.yml`; de getypeerde inputdefinities blijven bij de modules. Er is geen extra loader of generatiestap voor standaardwaarden. Zie [het bereik van inputs](https://docs.gitlab.com/ci/inputs/) en [beperkingen van gedeelde inputs](https://docs.gitlab.com/ci/inputs/#define-pipeline-inputs-in-external-files).

Het [uitgebreide pipelinevoorbeeld](../examples/full-pipeline/application.gitlab-ci.yml) en de [profielhandleiding](organization-profile.md) dienen als naslag voor scanners en andere toekomstige modules. De demo laadt deze niet in.

Bij publicatie vanuit een Dockerfile kopieert `image-build` de leescredentials van de runner naar een tijdelijk Docker-configuratiebestand. Voor de doelregistry gebruikt de job de expliciete publicatiecredentials. Vóór BuildKit start, verwijdert de job `DOCKER_AUTH_CONFIG` uit zijn omgeving: nieuwere Docker-clients geven die variabele voorrang op `config.json`. De runner kan de jobimage blijven ophalen met zijn leesaccount en credentials voor andere basisimage-registries blijven beschikbaar. `after_script` verwijdert de tijdelijke publicatiecredentials. Zie [Docker-credentialselectie](https://github.com/docker/cli/blob/master/cli/config/configfile/file.go).
