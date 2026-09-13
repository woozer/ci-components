# Zelf een pipeline samenstellen

Neem alleen de modules op die je nodig hebt. Je `.gitlab-ci.yml` bepaalt stages, afhankelijkheden tussen jobs, voorwaarden en extra jobs. Een organisatieprofiel of standaardpipeline voor Java is niet verplicht. Elke module heeft een eigen image en outputs; de gedeelde afhandeling van hooks wordt automatisch ingeladen.

## Een module kiezen

Elk voorbeeld is uitvoerbare YAML met de vereiste stage en één module. Vul de verplichte bibliotheekversie in, lever de image en uitvoeringsvoorwaarden aan en pas de applicatiepaden aan. Alle inputtypen en standaardwaarden staan in `spec:inputs` van de gelinkte module; inputs zonder standaardwaarde zijn verplicht. Zie [verplichte inputs](inputs.md).

| Module | Minimaal voorbeeld | Nodig bij uitvoering |
|---|---|---|
| [maven-build](../templates/maven-build.yml) | [YAML](../examples/modules/maven-build.yml) | POM en Java/Maven-image; maakt packages en slaat tests over |
| [cucumber-test](../templates/cucumber-test.yml) | [YAML](../examples/modules/cucumber-test.yml) | Cucumber/Failsafe-tests; dit voorbeeld start zelf de applicatie |
| [npm-build](../templates/npm-build.yml) | [YAML](../examples/modules/npm-build.yml) | Lockfile en `build`-script in `ui/` |
| [npm-test](../templates/npm-test.yml) | [YAML](../examples/modules/npm-test.yml) | Lockfile en `test:ci`-script dat `reports/junit.xml` aanmaakt |
| [sonar](../templates/sonar.yml) | [YAML](../examples/modules/sonar.yml) | SonarQube-project en analysetoken; Java/Maven en bij JS/TS ook Node in de image |
| [dependency-check](../templates/dependency-check.yml) | [YAML](../examples/modules/dependency-check.yml) | Maven-project en bereikbare openbare NVD-feed; geen API-key nodig |
| [maven-publish](../templates/maven-publish.yml) | [YAML](../examples/modules/maven-publish.yml) | Repository-URL en Maven-settingsbestand met authenticatie |
| [jib-build](../templates/jib-build.yml) | [YAML](../examples/modules/jib-build.yml) | Jib-plugin, Maven-settings voor de registry, doelrepository en Java-basisimage vastgezet op digest |
| [image-build](../templates/image-build.yml) | [YAML](../examples/modules/image-build.yml) | Dockerfile en geschikte runner voor rootless BuildKit; gebruikt standaard GitLab Registry-toegangsgegevens |
| [helm-publish](../templates/helm-publish.yml) | [YAML](../examples/modules/helm-publish.yml) | Chart, SemVer-versie, OCI-repository en registry-login |
| [helm-deploy](../templates/helm-deploy.yml) | [YAML](../examples/modules/helm-deploy.yml) | Image-digest, chartreferentie/-versie, values, kubeconfig, doel-URL en registry-login |
| [deployment-select](../templates/deployment-select.yml) | [YAML](../examples/modules/deployment-select.yml) | Eigen `deploy.yml` met cluster/user-config-inputs; een aparte GitLab-trigger gebruikt de gegenereerde YAML |
| [release-reserve](../templates/release-reserve.yml) | [YAML](../examples/modules/release-reserve.yml) | Protected branch, Git-URL voor releases, deploy-keybestand en known-hostsbestand |
| [release-check](../templates/release-check.yml) | [YAML](../examples/modules/release-check.yml) | Gereserveerde tag/commit en geauthenticeerde toegang tot de releaseregistry |
| [gitlab-release](../templates/gitlab-release.yml) | [YAML](../examples/modules/gitlab-release.yml) | Bestaande tag, gepubliceerde image-/chartoutputs en `CI_JOB_TOKEN` |

`JAVA_CI_IMAGE`, `NODE_CI_IMAGE`, `HELM_CI_IMAGE` en `BUILDKIT_CI_IMAGE` bevatten in de voorbeelden de goedgekeurde tool-images. Maven-modules gebruiken standaard `./mvnw`; de daarvoor benodigde tools moeten in de image zitten. Gebruik `maven-executable: mvn` wanneer je bewust de geïnstalleerde Maven gebruikt, zoals de uitvoerbare samples doen. Je kunt de jobnaam en stage van elke module wijzigen; declareer die stages in je pipeline.

Zie de [scanhandleiding](scanners.md) voor de automatische lokale inrichting en de beperkingen van de gratis scanners.

De releasevoorbeelden tonen afzonderlijke bewerkingen, geen volledig goedkeurings- of releasebeleid. Het opnemen van een module richt geen serverrechten in en een handmatige job maakt een release niet vanzelf toegestaan. De optionele [standaardreleasestrategie](releases.md) laat zien hoe deze bewerkingen worden gecombineerd en beveiligd.

## Outputs verbinden met needs

Begin met de [uitvoerbare voorbeelden](../examples/samples/README.md). Die gebruiken de volgende relaties:

| Output van de producerende job | Input van de afnemende job | Afhankelijkheid |
|---|---|---|
| `JIB_BUILD_IMAGE_REF` | Helm `image-ref-variable: JIB_BUILD_IMAGE_REF` | Helm gebruikt `needs` op de Jib-job, inclusief artifacts |
| `HELM_PUBLISH_REF`, `HELM_PUBLISH_VERSION` | Helm `chart-variable` en `chart-version-variable` | Helm gebruikt `needs` op de chartpublicatiejob, inclusief artifacts |
| `HELM_DEPLOY_URL` | Cucumber gebruikt deze standaard bij `target-url-variable` | Cucumber gebruikt `needs` op de Helm-job, inclusief artifacts |
| Artifactbestanden van een module | Gewone bestanden in de werkmap van de volgende job | De afnemende job gebruikt `needs` op de producerende job, inclusief artifacts |

GitLab importeert dotenv-waarden via de artifactafhankelijkheid. Inputs die eindigen op `-variable` bevatten een **variabelenaam**, niet de waarde zelf. Outputs uit een job kunnen geen `rules`, stages of includes bepalen: GitLab beoordeelt die vóór de uitvoering van jobs. Zie [GitLabs dotenv-documentatie](https://docs.gitlab.com/ci/variables/dotenv_variables/).

`helm-deploy` vraagt expliciet om de naam van de imagevariabele. De module veronderstelt geen vaste keten voor signing of verificatie. Gebruik voor twee instanties van dezelfde module verschillende waarden voor `job-name` en `output-prefix`, en verwijs naar de bijbehorende namen van de producerende jobs. Gebruik binnen één pipeline dezelfde bibliotheekversie, omdat modules hun lifecycle-implementatie delen. Het [voorbeeld met twee deployables](../examples/samples/two-deployables.yml) toont dit in uitvoerbare YAML.

## Eigen gedrag toevoegen

Voeg voor een extra controle of bewerking een gewone job toe met een eigen image en `needs`. Gebruik `pre-hook` of `post-hook` voor een kleine aanvulling binnen de modulejob. `cleanup-hook` draait in `after_script`. Hooks zijn optioneel; afnemers hoeven de interne `MODULE_*`-variabelen niet in te stellen of te begrijpen. Zie [hookvoorbeelden en foutafhandeling](hooks.md).

Ook tijdelijke testafhankelijkheden gebruiken bestaande mogelijkheden. Java-tests kunnen lokaal en in CI [Spring Boot Testcontainers](https://docs.spring.io/spring-boot/reference/testing/testcontainers.html) gebruiken als de runner een ondersteunde Docker-omgeving levert. Onze gewone runner stelt momenteel geen Docker-daemon beschikbaar aan jobs; daarvoor is een aparte geschikte runner nodig. Je kunt ook [GitLab-services](https://docs.gitlab.com/ci/services/) zoals PostgreSQL aan de testjob koppelen en de verbindingsinstellingen meegeven. De module voert alleen de tests uit en heeft geen eigen dependency-manager nodig. Geen van beide mogelijkheden is al aan de sample-applicatie toegevoegd.

## Optionele standaardpipeline

[java-service.yml](../pipelines/java-service.yml) is een kant-en-klare samenstelling van dezelfde modules. Deze ondersteunt één Java-applicatie of een Maven-reactor met één deploybare Java-module, eventueel met een Angular-UI. Meerdere Maven-modules betekenen niet automatisch meerdere deployables. Gebruik voor meer deployables expliciete module-instanties zoals in de voorbeelden; automatische verdeling over een willekeurig aantal deployables is niet geïmplementeerd.

De uitgestelde Helm-keuze, dev-lock en handmatige patchrelease van de standaardpipeline zijn optioneel organisatiebeleid. Losse modules vereisen deze afspraken niet. [GitLabs componentadvies](https://docs.gitlab.com/ci/components/#write-a-component) beveelt configureerbare jobs, weinig afhankelijkheden en duidelijke gebruiksvoorbeelden aan; daarop baseren we deze bibliotheek.
