# Modulehandleiding

Hier vind je per actieve module het doel, de benodigde inrichting, de werking, de outputs en het gedrag bij fouten. Je eigen `.gitlab-ci.yml` bepaalt stages, afhankelijkheden en voorwaarden. De standaardpipeline voor Java is optioneel.

Direct naar: [module kiezen](#actief-een-module-kiezen), [inputs en defaults](#inputs-en-defaults), [image en runner](#image-en-runner), [outputs doorgeven](#outputs-verbinden-met-needs), [eigen gedrag toevoegen](#eigen-gedrag-toevoegen) of [TODO-modules](#todo-nog-niet-actief).

## Snel beginnen

Kies een module, gebruik één uitgebrachte bibliotheekversie en lever de image en projectvoorwaarden aan. Dit voorbeeld bouwt vanuit de projectroot met Maven uit de gekozen image:

```yaml
stages: [build]

include:
  - component: $CI_SERVER_FQDN/root/ci-components/maven-build@1.0.0
    inputs:
      image: $MY_MAVEN_IMAGE
      maven-executable: mvn
```

De module kiest haar overige defaults zelf. Gebruik binnen één pipeline dezelfde [componentversie](component-versions.md), ook voor gedeelde includes. Een volledige commit-SHA is bedoeld voor het testen van een kandidaatwijziging.

De gelinkte YAML-voorbeelden zijn uitvoerbaar. Start een los voorbeeld in [CI samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new) met `sample: module-<module-name>`. De [samplehandleiding](../examples/samples/README.md#starten-in-gitlab) beschrijft de uitvoering en beperkingen. Voor een complete pipeline zijn er voorbeelden voor [bouwen en testen](../examples/samples/build-and-test.yml), [deployen en testen](../examples/samples/deploy-and-test.yml) en [twee deployables](../examples/samples/two-deployables.yml).

## Actief: een module kiezen

Alle vijftien modules hieronder zijn actief. Open de modulenaam voor de volledige uitleg; daar staan ook de implementatie en het minimale voorbeeld.

| Module | Taak |
|---|---|
| [maven-build](#maven-build) | Java-packages en unittests |
| [maven-publish](#maven-publish) | Maven-artifacts publiceren |
| [jib-build](#jib-build) | Java-image met Jib publiceren |
| [npm-build](#npm-build) | Frontend-assets bouwen |
| [npm-test](#npm-test) | Frontend-unittests uitvoeren |
| [cucumber-test](#cucumber-test) | API- en browserintegratietests |
| [image-build](#image-build) | Dockerfile-image publiceren |
| [helm-publish](#helm-publish) | OCI-chart publiceren |
| [helm-deploy](#helm-deploy) | Image en chart deployen |
| [sonar](#sonar) | Broncodeanalyse en quality gate |
| [dependency-check](#dependency-check) | Kwetsbare Maven-dependencies |
| [deployment-select](#deployment-select) | Deploymentprofiel kiezen |
| [release-reserve](#release-reserve) | Releaseversie reserveren |
| [release-check](#release-check) | Reservering en vrije artifactlocaties |
| [gitlab-release](#gitlab-release) | GitLab Release publiceren |

## Inputs en defaults

In de gelinkte `spec:inputs` van iedere module staat de volledige inputdefinitie: betekenis, type, toegestane waarden en default. Een input **zonder `default` is verplicht**; met `default` is zij optioneel. Elke module vereist `image`. Vul optionele inputs alleen in als je van de standaardwaarde wilt afwijken. Bestanden, credentials en andere voorwaarden bij uitvoering staan bij de module onder **Vooraf**.

De gedeelde instellingen werken overal hetzelfde:

| Instelling | Gebruik |
|---|---|
| `job-name`, `stage` | Geef herhaalde modulejobs unieke namen en declareer hun stages in de pipeline |
| `working-directory` | Werkmap relatief aan de projectroot; standaard `.` |
| `output-prefix` | Prefix van de outputvariabelen; standaard modulespecifiek, bij herhaling uniek kiezen |
| `job-timeout` | Maximale jobduur: standaard `30m`, bij Dependency-Check `1h`; ook runnerlimieten gelden |
| `artifact-expire-in` | Bewaarinstelling voor jobartifacts: standaard `7 days` |
| `pre-hook`, `post-hook`, `cleanup-hook` | Optionele scripts; standaard leeg |
| `hook-parameters-json` | Niet-geheime hookparameters; standaard `{}` |

De exacte definities blijven bij de module. We herhalen hier niet alle inputtabellen; GitLab toont die ook op de gepubliceerde componentpagina. De korte beschrijving en het uitvoerbare voorbeeld per module volgen [GitLabs documentatieadvies](https://docs.gitlab.com/ci/components/#write-a-clear-readmemd). De keuze om de uitleg in deze handleiding bijeen te brengen is onze documentatieafspraak.

De interne `MODULE_*`-variabelen verbinden inputs met de scripts. Afnemers stellen componentinputs in. Het [organisatiebestand van de demo](defaults.md) kiest serveradressen en images; het verandert niet wat een module verplicht stelt.

## Image en runner

Iedere module gebruikt de opgegeven `image`. Taken mogen dezelfde image delen als die hun benodigde tooling bevat. De image moet POSIX `sh` en basistools zoals `awk`, `grep`, `wc`, `printenv`, `cat`, `cp`, `mv`, `rm` en `mkdir` bevatten. De extra tools staan per module onder **Vooraf**. Het platform levert goedgekeurde images met een vaste digest, passende CA-certificaten, proxies en toegangsrechten.

Maven-modules gebruiken standaard de uitvoerbare `./mvnw` in hun werkmap. Commit de wrapper met distributieversie en checksum; lever de benodigde download- en uitpaktools in de image. Onze wrapper met ZIP-distributie en checksum vereist ook `unzip`. Gebruik `maven-executable: mvn` voor de Maven-installatie in de image. Stem Java- en Node-versies af op het project en de gekozen tools.

Een module configureert niet zelf de runner of serverrechten. Onze gewone runner geeft jobs geen Docker-daemon. Voor Testcontainers is een geschikte runner met Docker-toegang nodig; een alternatief is een tijdelijke database of queue via [GitLab-services](https://docs.gitlab.com/ci/services/). De sample gebruikt deze testafhankelijkheden nog niet.

## Outputs verbinden met needs

Neem de producerende job rechtstreeks op in `needs` met `artifacts: true`. GitLab haalt dan de gepubliceerde bestanden op en stelt dotenv-waarden beschikbaar. Een padvariabele alleen kopieert geen bestand; een imagereferentie downloadt geen image. Voor ophalen uit een registry of Maven-repository blijven netwerktoegang en de juiste credentials nodig. Met `artifacts: false` wacht de job wel op de producent, maar ontvangt zij diens bestanden en dotenv-waarden niet. Zie [GitLab needs:artifacts](https://docs.gitlab.com/ci/yaml/#needsartifacts).

Dit fragment vult twee al opgenomen modules aan. Helm gebruikt hier `image-ref-variable: JIB_BUILD_IMAGE_REF`; Cucumber leest standaard `HELM_DEPLOY_URL`:

```yaml
helm-deploy:
  needs:
    - job: jib-build
      artifacts: true

cucumber-test:
  needs:
    - job: helm-deploy
      artifacts: true
```

Heeft Helm ook een gepubliceerde chart nodig, voeg dan de chartpublicatiejob toe aan zijn `needs`. Heeft Cucumber daarnaast buildbestanden nodig, voeg dan de buildjob rechtstreeks toe; artifacts worden niet automatisch via tussenliggende jobs doorgegeven. Het [uitvoerbare deploymentvoorbeeld](../examples/samples/deploy-and-test.yml) toont de volledige koppeling met image en chart.

Inputs met `-variable` verwachten een variabelenaam, niet de waarde. `runtime_input()` controleert alleen of die variabele bestaat; `image_input()` controleert aanvullend het digestformaat. De overige controles verschillen per module. Dotenv-waarden ontstaan tijdens jobuitvoering en zijn niet beschikbaar voor `rules` of het samenstellen van includes. Gebruik unieke prefixen en voorkom project- of pipelinevariabelen met dezelfde outputnamen; die kunnen dotenv-waarden overschrijven. Zet geen geheimen in outputs. Zie [GitLab-dotenv-variabelen](https://docs.gitlab.com/ci/variables/dotenv_variables/).

## Gedeelde outputafspraken

De producerende module levert haar afgesproken outputs; de ontvangende job controleert haar benodigde inputs vóór gebruik. De modulebeschrijvingen vermelden de huidige controles en beperkingen. Een artifactpad alleen bewijst niet dat alle bedoelde bestanden bestaan.

Alle outputvariabelen zijn strings in `.ci-output/<job-name>/outputs.env`. De onderstaande namen gebruiken de standaardwaarde van `output-prefix`. Een andere prefix vervangt dat gedeelte van de naam: met `output-prefix: API` wordt `JIB_BUILD_IMAGE_REF` bijvoorbeeld `API_IMAGE_REF`. Een andere `job-name` wijzigt het artifactpad, maar niet de prefix.

Iedere module levert bij geslaagde afhandeling deze drie variabelen:

| Output | Betekenis |
|---|---|
| `<PREFIX>_STATUS` | `passed`; informatieve status, geen vervanging voor GitLabs jobresultaat |
| `<PREFIX>_COMMIT_SHA` | De volledige `CI_COMMIT_SHA` van de producerende job |
| `<PREFIX>_PIPELINE_ID` | De `CI_PIPELINE_ID` van de producerende job, als tekst |

De taakspecifieke variabelen hieronder zijn eveneens aanwezig bij geslaagde afhandeling, behalve waar expliciet **optioneel** staat. Bestands- en mappaden zijn relatief aan de projectroot. `<workdir>` betekent de input `working-directory`, standaard `.`; `<output-dir>` betekent `.ci-output/<job-name>`.

Elke module publiceert `<output-dir>/` als jobartifact. Daarin staat `outputs.env`, dat ook als `artifacts:reports:dotenv` is gedeclareerd. De overige bestanden in die map, zoals `pending.env` en hookparameters, zijn intern tenzij hieronder genoemd. De input `artifact-expire-in` is standaard `7 days`; GitLabs bewaarbeleid bepaalt wanneer jobartifacts worden verwijderd. Deze instelling geldt niet voor packages, images, charts, Git-tags of releases in externe opslag. Zie [GitLab-jobartifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/).

**Publicatie en fouten:** de module voert eerst haar bewerking en taakspecifieke controles uit, daarna de optionele posthook en de gedeelde controle van outputvariabelen. Pas dan wordt `outputs.env` aangemaakt. De gedeelde code controleert onder meer unieke namen, niet-lege waarden op één regel en maximaal 5120 bytes. Zij controleert bestanden niet opnieuw na een hook. Alle actieve modules gebruiken `artifacts:when: always`, zodat beschikbare rapporten ook bij fouten kunnen worden bewaard; dat maakt die bestanden nog geen bewijs van succes. Een fout na een push of tagreservering draait die externe bewerking niet automatisch terug.

De outputnamen, prefixen en aanvullende formaatcontroles zijn afspraken van deze bibliotheek. De implementatie staat in [shared/module.yml](../shared/module.yml). Eigen hooks kunnen optionele outputs met `<PREFIX>_CUSTOM_` toevoegen; hun betekenis legt de afnemer zelf vast. Zie [hooks uitbreiden](#kleine-aanvulling-binnen-een-component). De overdracht gebruikt GitLabs bestaande artifacts en dotenv-rapporten.

Een retry voert de modulebewerking opnieuw uit. Test- en buildjobs maken hun resultaten opnieuw; publicatie- en deploymentjobs kunnen ook externe toestand wijzigen. Hun specifieke gedrag staat hieronder.

## maven-build

Bouwt een Maven-project of reactor en voert de unittests uit.

[Voorbeeld](../examples/modules/maven-build.yml) · [Inputdefinitie en implementatie](../templates/maven-build.yml)

**Vooraf:** Een POM, een passende JDK en Maven of de Maven Wrapper. Configureer Surefire voor unittests. Configureer voor coverage JaCoCo `prepare-agent` vóór de tests en het XML-rapport uiterlijk tijdens `package`, bijvoorbeeld in `prepare-package`. De module stelt de test- en coverageconfiguratie niet zelf in.

**Werking en controles:** De module vereist een geslaagde Maven-opdracht `package` met unittests en `-DskipITs`. De module controleert niet afzonderlijk of een specifieke JAR, testsuite of coveragebestand bestaat.

| Output | Betekenis |
|---|---|
| `MAVEN_BUILD_ARTIFACT_ROOT` | Map `<workdir>` waaronder de Maven-modules en hun `target/`-mappen staan; geen pad naar één JAR |

**Bestanden:** `<workdir>/**/target/`. Surefire-rapporten uit `<workdir>/**/target/surefire-reports/TEST-*.xml` zijn ook als JUnit-rapporten gedeclareerd. De POM bepaalt welke JARs, andere packages en coveragebestanden ontstaan.

**Vervolgjob:** haal de buildjob op via `needs` met artifacts voor classes, packages of coverage, bijvoorbeeld voor Sonar. Gebruik het bij de applicatie afgesproken pad binnen `target/`.

## maven-publish

Publiceert Maven-artifacts naar de gekozen repository nadat de pipeline de vereiste tests heeft uitgevoerd.

[Voorbeeld](../examples/modules/maven-publish.yml) · [Inputdefinitie en implementatie](../templates/maven-publish.yml)

**Vooraf:** Een JDK, Maven en de verplichte inputs `settings-file` en `repository-url`. De server-id in het settingsbestand moet bij `repository-id` passen. Met `project-selector` kun je een deel van de reactor selecteren; Maven bouwt dan ook de benodigde reactormodules.

**Werking en controles:** De module vereist een geslaagde Maven-opdracht `deploy`. De module slaat tests over en haalt gepubliceerde artifacts niet opnieuw op ter controle.

| Output | Betekenis |
|---|---|
| `MAVEN_PUBLISH_REPOSITORY_URL` | De ingestelde Maven-repository-URL; geen lijst met gepubliceerde artifactcoördinaten |

**Bestanden en opslag:** alleen de gedeelde outputmap is een jobartifact. Maven publiceert de reactorartifacts in de ingestelde repository; de POM bepaalt hun coördinaten en versies.

**Vervolgjob:** gebruik `needs` met artifacts als de repository-URL nodig is. Download packages met Maven via hun coördinaten en de passende repositoryconfiguratie. Gebruik `artifacts: false` als alleen succesvolle publicatie een voorwaarde is.

**Bij opnieuw uitvoeren:** Een retry voert `deploy` opnieuw uit. Controleer na een fout of er al artifacts zijn gepubliceerd. Repositoryrechten en versiebeleid bepalen of dezelfde versie opnieuw mag worden aangeboden.

## jib-build

Bouwt en publiceert één Java-image met Jib vanuit de geselecteerde Maven-module; een Docker-daemon is niet nodig.

[Voorbeeld](../examples/modules/jib-build.yml) · [Inputdefinitie en implementatie](../templates/jib-build.yml)

**Vooraf:** Een JDK, Maven en een geconfigureerde Jib-plugin. Stel `project-selector`, `settings-file`, `image-repository` en `base-image` in. De basisimage moet een digest bevatten. Het settingsbestand levert registry-authenticatie; `digest-file` moet wijzen naar het digestbestand van de geselecteerde module. Jib ontvangt de standaardproperties `jib.to.image` en `jib.from.image`.

**Werking en controles:** De module vereist een geslaagde Jib-build en push. De module leest het digestbestand en controleert het formaat. Zij haalt de image niet opnieuw op.

| Output | Betekenis |
|---|---|
| `JIB_BUILD_IMAGE_REF` | Imagereferentie `<image-repository>@sha256:<64 kleine hextekens>` |
| `JIB_BUILD_IMAGE_REPOSITORY` | De ingestelde `image-repository`, zonder de door de module toegevoegde tag of digest |
| `JIB_BUILD_IMAGE_DIGEST` | De door Jib gerapporteerde `sha256:<64 kleine hextekens>` |

**Bestanden en opslag:** de image staat in de registry. Alleen de gedeelde outputmap is een jobartifact; het via `digest-file` gelezen Jib-bestand wordt niet afzonderlijk door deze module gepubliceerd. Een imagearchief en SBOM behoren niet tot deze outputs.

**Vervolgjob:** haal de Jib-job op via `needs` met artifacts en geef Helm `image-ref-variable: JIB_BUILD_IMAGE_REF`. Gebruik de referentie met digest om dezelfde image te selecteren.

**Bij opnieuw uitvoeren:** De opdracht `compile jib:build` draait bij een retry opnieuw. Een eerdere push kan al geslaagd zijn. Voor releases moet het repositorybeleid overschrijven verhinderen.

## npm-build

Installeert de vastgelegde npm-dependencies en voert het buildscript van de applicatie uit.

[Voorbeeld](../examples/modules/npm-build.yml) · [Inputdefinitie en implementatie](../templates/npm-build.yml)

**Vooraf:** Node.js, npm, `package.json` en `package-lock.json` in `working-directory`. Standaard wordt het script `build` uitgevoerd en de map `dist` verwacht. Pas `build-script` en `artifact-directory` aan als het project andere namen gebruikt.

**Werking en controles:** De module vereist geslaagde `npm ci`- en buildopdrachten en controleert of de outputmap bestaat. De module controleert niet of die map gevuld is of bijvoorbeeld `index.html` bevat.

| Output | Betekenis |
|---|---|
| `NPM_BUILD_ARTIFACT_DIR` | Map `<workdir>/<artifact-directory>` met de buildoutput |

**Bestanden:** `<workdir>/<artifact-directory>/` wordt naast de gedeelde outputmap gepubliceerd.

**Vervolgjob:** haal de npm-buildjob op via `needs` met artifacts. Een imagebuild kan die bestanden daarna vanuit zijn buildcontext met een Dockerfile kopiëren; het Dockerfilepad moet aansluiten op de gekozen outputmap.

## npm-test

Installeert de npm-dependencies en voert het CI-testscript zonder interactie uit.

[Voorbeeld](../examples/modules/npm-test.yml) · [Inputdefinitie en implementatie](../templates/npm-test.yml)

**Vooraf:** Node.js, npm en een lockfile. Het standaard `test:ci`-script moet `reports/junit.xml` schrijven en zelf falen bij mislukte of ontbrekende tests. Lever ook browserlibraries als de gekozen testrunner die nodig heeft. Schrijf `coverage/lcov.info` als Sonar de UI-testdekking moet meenemen.

**Werking en controles:** De module vereist een geslaagd npm-testscript en een niet-leeg `reports/junit.xml`. De module valideert de XML-inhoud niet zelf en stelt geen coveragegrens in.

| Output | Betekenis |
|---|---|
| `NPM_TEST_REPORT_DIR` | Map `<workdir>/reports` met de testrapportage |

**Bestanden:** `<workdir>/reports/` en, indien aangemaakt, `<workdir>/coverage/`. `reports/junit.xml` is ook als JUnit-rapport gedeclareerd. De module stelt geen afzonderlijke coverageoutputvariabele in.

**Vervolgjob:** gebruik `needs` met artifacts voor rapporten of coverage. Als alleen geslaagde tests vereist zijn, volstaat `artifacts: false`.

## cucumber-test

Voert Maven/Failsafe-integratietests uit tegen een gedeployde applicatie of een applicatie die de tests zelf starten.

[Voorbeeld](../examples/modules/cucumber-test.yml) · [Inputdefinitie en implementatie](../templates/cucumber-test.yml)

**Vooraf:** Een JDK, Maven en een Cucumber-suite. Koppel Failsafe aan `integration-test` en `verify`; de testcode leest `cucumber.base-url`. Laat Surefire reageren op `skipUnitTests`, zodat deze job de unittests kan overslaan zonder Failsafe uit te schakelen. Laat de suite falen als het tagfilter geen scenario selecteert. Gebruik voor Playwright een image met de bij de dependency passende browser en systeemlibraries; headless uitvoering heeft die browser nog steeds nodig.

Kies met `tags` de scenario's en eventueel met `profile` het Maven-profiel. Standaard is geen profiel actief en leest de module `HELM_DEPLOY_URL`. Gebruik `target-url-variable: ''` als de tests zelf de applicatie starten; anders haal je de URL op van de deploymentjob.

**Werking en controles:** De module vereist een geslaagde Maven-opdracht `verify` met `-DfailIfNoTests=true`. De module controleert rapportbestanden niet afzonderlijk. Met een ingestelde `target-url-variable` moet de upstreamvariabele bestaan; de tests bepalen of de applicatie bereikbaar is en correct reageert.

| Output | Betekenis |
|---|---|
| `CUCUMBER_TEST_REPORT_ROOT` | Map `<workdir>` waaronder de Maven-testmodules en hun rapporten staan |
| `CUCUMBER_TEST_TAGS` | De gebruikte Cucumber-tagexpressie |
| `CUCUMBER_TEST_PROFILE` | **Optioneel:** alleen aanwezig als `profile` niet leeg is; bevat dat Maven-profiel |
| `CUCUMBER_TEST_TARGET_URL` | **Optioneel:** alleen aanwezig als `target-url-variable` niet leeg is; bevat de ontvangen test-URL |

**Bestanden:** `<workdir>/**/target/failsafe-reports/` en `<workdir>/**/target/cucumber/`. Failsafe-bestanden `TEST-*.xml` zijn ook als JUnit-rapporten gedeclareerd. De applicatie bepaalt welke Cucumber- en browserrapporten zij schrijft.

**Vervolgjob:** haal deze job op via `needs` met artifacts voor de rapporten en gebruikte testselectie. Zet `artifacts: false` als alleen het testresultaat een voorwaarde is. Een ontbrekende optionele output wordt niet als lege variabele gepubliceerd.

## image-build

Bouwt en publiceert één image vanuit een Dockerfile met rootless BuildKit.

[Voorbeeld](../examples/modules/image-build.yml) · [Inputdefinitie en implementatie](../templates/image-build.yml)

**Vooraf:** Een image met `buildctl-daemonless.sh` en Python 3, plus een runner die de benodigde user-namespace- en mountbewerkingen toestaat. De Dockerfile en buildcontext staan in `working-directory`; haal benodigde buildbestanden via `needs` op. Sluit credentials en caches uit met `.dockerignore`. Publicatie gebruikt standaard de GitLab Registry-variabelen; geef bij een andere registry de bestemming en credentials expliciet mee. Zie [GitLabs BuildKit-inrichting](https://docs.gitlab.com/ci/docker/using_buildkit/).

**Werking en controles:** De module vereist een geslaagde build en push, leest `containerimage.digest` uit de JSON-metadata en controleert het digestformaat. De module haalt de image niet opnieuw op.

| Output | Betekenis |
|---|---|
| `IMAGE_BUILD_IMAGE_REF` | Imagereferentie `<image-repository>@sha256:<64 kleine hextekens>` |
| `IMAGE_BUILD_DIGEST` | De door BuildKit gerapporteerde `sha256:<64 kleine hextekens>` |

**Bestanden en opslag:** `<output-dir>/build-metadata.json` bevat BuildKit-metadata en `<output-dir>/digest.txt` de digest. De image staat in de registry; een imagearchief en SBOM behoren niet tot deze outputs.

**Vervolgjob:** haal deze job op via `needs` met artifacts en geef Helm `image-ref-variable: IMAGE_BUILD_IMAGE_REF`. Voor een eigen controle zijn ook de metadata en het digestbestand beschikbaar.

**Bij opnieuw uitvoeren:** Een retry bouwt en pusht opnieuw; een eerdere image kan al aanwezig zijn. De module maakt tijdelijke registry-credentials buiten de artifactmap en verwijdert die in `after_script`. Zij verwijdert geen gepubliceerde image.

## helm-publish

Controleert, verpakt en publiceert één Helm-chart met de gekozen versie.

[Voorbeeld](../examples/modules/helm-publish.yml) · [Inputdefinitie en implementatie](../templates/helm-publish.yml)

**Vooraf:** Helm en de inputs `chart`, `chart-name`, `chart-version` en `oci-repository`. `chart-name` moet overeenkomen met `Chart.yaml`; lever de chartdependencies aan. Regel registry-authenticatie vóór de bewerking, bijvoorbeeld met de gedeelde [Helm-login](../shared/helm.yml). `plain-http` is alleen bedoeld voor een bewust gekozen lokale HTTP-registry.

**Werking en controles:** De module vereist geslaagde `helm lint`, `helm package` en `helm push`. De verpakte chart wordt niet opnieuw uit de registry opgehaald ter controle.

| Output | Betekenis |
|---|---|
| `HELM_PUBLISH_REF` | OCI-chartreferentie `<oci-repository>/<chart-name>`, zonder versie |
| `HELM_PUBLISH_VERSION` | De gepubliceerde `chart-version` |

**Bestanden en opslag:** `<output-dir>/<chart-name>-<chart-version>.tgz` is een jobartifact. De chart wordt ook naar de OCI-registry gepusht. De module geeft geen chartdigest door.

**Vervolgjob:** haal deze job op via `needs` met artifacts en geef Helm `chart-variable: HELM_PUBLISH_REF` en `chart-version-variable: HELM_PUBLISH_VERSION`. Zo gebruikt deployment de bijbehorende chartversie.

**Bij opnieuw uitvoeren:** Een retry verpakt en pusht opnieuw. Bij een eerdere gedeeltelijk geslaagde uitvoering kan de chartversie al in de registry staan; het repositorybeleid bepaalt of opnieuw publiceren is toegestaan.

## helm-deploy

Installeert of wijzigt één Helm-release en wacht op readiness voordat de vervolgtests kunnen starten.

[Voorbeeld](../examples/modules/helm-deploy.yml) · [Inputdefinitie en implementatie](../templates/helm-deploy.yml)

**Vooraf:** Helm en `image-ref-variable`, `values-file`, `release`, `namespace`, `environment` en `target-url`. Lever ook `chart` of `chart-variable` en zo nodig `chart-version-variable` en registry-authenticatie. Kies clustercredentials via `kubeconfig-variable`, `KUBE_CONTEXT` of `KUBECONFIG`. Beperk de rechten tot de doelnamespace; gebruik `create-namespace: false` als het platform die vooraf aanmaakt.

De chart moet `image.repository` en `image.digest` gebruiken, readiness-probes bevatten en de routing laten aansluiten op `target-url`. Commit `Chart.lock` voor chartdependencies. `override-values-file` wordt na `values-file` toegepast; de expliciete image-digest blijft leidend. Gebruik een `helm-major` die overeenkomt met de image: standaard 4, of expliciet 3.

**Werking en controles:** De module controleert de ontvangen imagereferentie en vereist een geslaagde Helm-deployment met wachten op readiness binnen `timeout`. De chart moet de opgegeven imagewaarden en readiness-probes gebruiken. De module doet geen afzonderlijk HTTP-verzoek naar `HELM_DEPLOY_URL` en controleert niet achteraf welke digest iedere pod draait.

| Output | Betekenis |
|---|---|
| `HELM_DEPLOY_IMAGE_REF` | De ontvangen imagereferentie met digest die aan Helm is doorgegeven |
| `HELM_DEPLOY_URL` | De ingestelde `target-url` voor vervolgtests |
| `HELM_DEPLOY_RELEASE` | De gebruikte Helm-releasenaam |
| `HELM_DEPLOY_NAMESPACE` | De gebruikte Kubernetes-namespace |

**Bestanden en opslag:** alleen de gedeelde outputmap is een jobartifact. De deployment staat in het cluster; de module publiceert geen gerenderde manifests of kubeconfig.

**Vervolgjob:** haal deze job op via `needs` met artifacts. Cucumber leest standaard `HELM_DEPLOY_URL`; geef bij een andere prefix de bijbehorende `target-url-variable` op.

**Bij opnieuw uitvoeren:** Een retry past dezelfde release opnieuw toe. Helm 4 gebruikt `--rollback-on-failure`; Helm 3 gebruikt `--atomic`. Een mislukte deployment draait niet de deployments van andere jobs terug. De resourcegroep beschermt deze job, niet automatisch de daaropvolgende tests; zie [deploymentvolgorde](deployment-concurrency.md).

## sonar

Analyseert het Maven-project met SonarScanner for Maven en wacht op de quality gate.

[Voorbeeld](../examples/modules/sonar.yml) · [Inputdefinitie en implementatie](../templates/sonar.yml)

**Vooraf:** Een JDK, Maven, Git en bij JS/TS-analyse ook de benodigde Node-runtime. Stel `SONAR_HOST_URL`, `SONAR_PROJECT_KEY` en een beperkt `SONAR_TOKEN` in. Haal coverage van build- en testjobs via `needs` op en configureer de rapportpaden. Voor gecombineerde Java/UI-analyse moeten ook de frontendbronnen en LCOV in de Sonar-configuratie staan. Een zelfstandige frontendscanner is niet in deze module geïmplementeerd.

Houd `gate-timeout` binnen `job-timeout`. De lokale Community Build draait in onze standaardpipeline alleen op protected `main` en tijdens releases; zie [scannerinrichting](scanners.md).

**Werking en controles:** De module vereist een geslaagde analyse met `sonar.qualitygate.wait=true` en een niet-leeg taakbestand. De Sonar-opdracht bepaalt of de gate slaagt; de module parseert het taakbestand niet zelf.

| Output | Betekenis |
|---|---|
| `SONAR_TASK_FILE` | Bestand `<output-dir>/report-task.txt` met metadata van de scantaak |

**Bestanden en opslag:** `report-task.txt` is een jobartifact. De analyse en quality-gatestatus staan in SonarQube; dit bestand is geen volledige export van de bevindingen.

**Vervolgjob:** gebruik `needs` met artifacts als taakmetadata nodig is. Voor alleen de verplichte quality gate gebruik je de geslaagde job als afhankelijkheid met `artifacts: false`.

**Bij opnieuw uitvoeren:** De module voert eerst Maven `install` met overgeslagen tests uit om reactorafhankelijkheden beschikbaar te maken. Dat kan opnieuw compileren en verpakken. Een afgekeurde quality gate of timeout laat de job falen. Een retry start een nieuwe analyse.

## dependency-check

Controleert Maven-dependencies met OWASP Dependency-Check en blokkeert op de ingestelde ernstgrens.

[Voorbeeld](../examples/modules/dependency-check.yml) · [Inputdefinitie en implementatie](../templates/dependency-check.yml)

**Vooraf:** Een JDK die bij de gekozen plugin past, Maven en toegang tot de NVD-feed. De module gebruikt standaard een openbare JSON-feed zonder API-key; `nvd-datafeed-url` kan een interne mirror aanwijzen. Configureer een cache voor `.cache/dependency-check/` om de database te hergebruiken. De eerste uitvoering kan langer duren. De npm-lockfile wordt niet door deze module gecontroleerd.

De optionele OSS Index-controle staat uit. De lokale mirror, uitzonderingen en beperkingen staan bij [scannerinrichting](scanners.md#dependency-check-zonder-api-key).

**Werking en controles:** De module vereist een geslaagde scan met de ingestelde `fail-cvss`-grens en `failOnError=true`. Daarna controleert de module of het JSON-rapport niet leeg is. Zij controleert het HTML-bestand en de JSON-structuur niet afzonderlijk.

| Output | Betekenis |
|---|---|
| `DEPENDENCY_CHECK_REPORT_DIR` | Map `<output-dir>` met de scanrapporten |

**Bestanden:** `<output-dir>/dependency-check-report.json` en `<output-dir>/dependency-check-report.html`. Dit zijn gewone jobartifacts, geen CycloneDX-SBOM of GitLab dependency-scanningrapport.

**Vervolgjob:** haal deze job op via `needs` met artifacts om de rapporten te verwerken. Gebruik `artifacts: false` als alleen de scan moet slagen.

**Bij opnieuw uitvoeren:** Voor de scan voert de module Maven `install` met overgeslagen tests uit. De standaardgrens `fail-cvss: 7` is organisatiebeleid. Toolfouten en overschrijding van die grens laten de job falen. Een retry voert de scan opnieuw uit; de uitkomst kan veranderen door nieuwe kwetsbaarheidsgegevens.

## deployment-select

Legt cluster- en profielkeuzes vast en maakt daarmee de configuratie voor een childpipeline.

[Voorbeeld](../examples/modules/deployment-select.yml) · [Inputdefinitie en implementatie](../templates/deployment-select.yml)

**Vooraf:** Een shellimage met `sed` en de input `pipeline-config`, met daarin `@CLUSTER@` en `@USER_CONFIG@`. Configureer de toegestane keuzes en een aparte triggerjob. Deze module maakt de keuzestap; zij voert geen Helm-deployment uit. De standaard wachttijd is tien seconden. De bedieningsstappen staan bij [pipelinekeuzes](pipeline-options.md#deployment-kiezen-na-publicatie).

**Werking en controles:** De module gebruikt GitLabs toegestane jobinputkeuzes en accepteert alleen niet-lege namen met kleine letters, cijfers en koppeltekens. De module controleert niet of bijbehorende valuesfiles bestaan en valideert de gegenereerde YAML niet zelf.

| Output | Betekenis |
|---|---|
| `SELECTION_CLUSTER` | De gekozen clusternaam |
| `SELECTION_USER_CONFIG` | De gekozen naam van het gebruikersprofiel |

**Bestanden:** `<output-dir>/pipeline.yml`, waarin `@CLUSTER@` en `@USER_CONFIG@` zijn vervangen. Er wordt geen afzonderlijke outputvariabele met dit bestandspad gepubliceerd.

**Vervolgjob:** een gewone job ontvangt de selectiewaarden via `needs` met artifacts. Een triggerjob gebruikt voor de gegenereerde childconfiguratie `trigger:include:artifact` met `<output-dir>/pipeline.yml` en de producerende jobnaam; GitLab verwerkt die YAML bij het aanmaken van de childpipeline. Zie [pipelinekeuzes](pipeline-options.md).

**Bij opnieuw uitvoeren:** Opnieuw uitvoeren wijzigt het gegenereerde configuratiebestand. Start daarna de bijbehorende trigger opnieuw om die keuze toe te passen; een al gestarte childpipeline verandert niet mee.

## release-reserve

Reserveert een versie met een nieuwe Git-tag op de toegestane protected branch.

[Voorbeeld](../examples/modules/release-reserve.yml) · [Inputdefinitie en implementatie](../templates/release-reserve.yml)

**Vooraf:** Git, SSH, `sed` en een protected releasebranch. Lever een Git-URL, deploy-keybestand en vastgelegde SSH-hostsleutels via `git-url`, `git-key-file` en `git-known-hosts-file`, of hun standaard GitLab-variabelen. De sleutel moet releasetags mogen maken. `release-line` bepaalt major en minor; `auto` kiest de volgende patch binnen die reeks en begint zonder eerdere tag bij patch 0.

**Werking en controles:** De module controleert de versie binnen `release-line`, de toegestane protected branch en de commit. De module vereist een nieuwe tag en een geslaagde push zonder force. Een latere fout laat de reservering bestaan.

| Output | Betekenis |
|---|---|
| `RELEASE_VERSION` | De gereserveerde stabiele versie `major.minor.patch`, zonder `v` |
| `RELEASE_TAG` | De gereserveerde Git-tag `v<RELEASE_VERSION>` |

**Bestanden en opslag:** de tag staat in Git en wijst bij reservering naar `CI_COMMIT_SHA`. Alleen bij een niet-lege `pipeline-config` wordt ook `<output-dir>/pipeline.yml` gemaakt, met de gereserveerde versie en commit ingevuld. Er is nog geen GitLab Release of release-artifact gemaakt.

**Vervolgjob:** een gewone job ontvangt versie, tag en de gedeelde `RELEASE_COMMIT_SHA` via `needs` met artifacts. Voor een childpipeline wordt het optionele `pipeline.yml` via `trigger:include:artifact` geladen. Dotenv-waarden kunnen geen eerder verwerkte componentinputs invullen; de standaardpipeline geeft versie en commit daarom via de gegenereerde childconfiguratie door. Zie [releasebeleid](releases.md).

**Bij opnieuw uitvoeren:** Een gereserveerde tag blijft bestaan bij een latere fout. Met `auto` reserveert een volgende uitvoering een nieuwe patchversie; dezelfde expliciete versie wordt geweigerd. Wijzig major/minor via een beoordeelde wijziging van `release-line`, niet via de jobinput.

## release-check

Controleert de gereserveerde release vóórdat de pipeline release-artifacts gaat bouwen.

[Voorbeeld](../examples/modules/release-check.yml) · [Inputdefinitie en implementatie](../templates/release-check.yml)

**Vooraf:** Git, `curl`, een protected releasebranch en de inputs `image-path`, `version` en `commit`. De tag moet al bestaan. Lever registry-URL en authenticatie aan via de bijbehorende inputs of standaardvariabelen. Geef `chart-path` mee om ook de chartlocatie te controleren. Deze implementatie gebruikt Artifactory-manifestpaden.

**Werking en controles:** De module controleert branch, gereserveerde commit en tag. De opgegeven image- en eventuele chartlocatie moeten op het controlemoment HTTP 404 retourneren; andere antwoorden of netwerkfouten blokkeren publicatie. Dit is geen lock of garantie dat die locaties later nog vrij zijn. Repositoryrechten moeten overschrijven voorkomen; zie [releasebeleid](releases.md).

| Output | Betekenis |
|---|---|
| `RELEASE_CHECK_VERSION` | De gecontroleerde stabiele releaseversie, zonder `v` |
| `RELEASE_CHECK_TAG` | De gecontroleerde Git-tag `v<RELEASE_CHECK_VERSION>` |

**Bestanden:** alleen de gedeelde outputmap; de module maakt geen nieuwe tag of release-artifact.

**Vervolgjob:** gebruik `needs` met artifacts als de gecontroleerde versie en tag nodig zijn. Als alleen de controle moet slagen vóór publicatie, volstaat `artifacts: false`.

**Bij opnieuw uitvoeren:** Opnieuw uitvoeren herhaalt de controles. Zodra een gecontroleerd release-artifact bestaat, wordt verder bouwen geblokkeerd. Gebruik de job samen met het centrale releasebeleid en repositoryrechten.

## gitlab-release

Maakt de GitLab Release met toelichting en links naar de gevalideerde artifacts.

[Voorbeeld](../examples/modules/gitlab-release.yml) · [Inputdefinitie en implementatie](../templates/gitlab-release.yml)

**Vooraf:** `curl`, een bestaande releasetag en de input `version`. GitLab levert `CI_JOB_TOKEN`; de job moet toegang hebben tot de Releases API. Haal image- en chartoutputs rechtstreeks op via `needs` en stel hun variabelenamen in. De defaults `JIB_IMAGE_REF`, `CHART_REF` en `CHART_VERSION` passen bij de centrale pipeline; gebruik bij losse modules bijvoorbeeld `JIB_BUILD_IMAGE_REF`, `HELM_PUBLISH_REF` en `HELM_PUBLISH_VERSION`.

**Werking en controles:** De module controleert de releaseversie, imagereferenties met digest, OCI-chartreferenties en overeenkomende chartversies. De GitLab-API-aanroep moet slagen. De module haalt de assets niet opnieuw op en voert geen integratietests uit; de pipeline moet geslaagde validatie als afhankelijkheid instellen.

| Output | Betekenis |
|---|---|
| `GITLAB_RELEASE_URL` | Releasepagina `<CI_PROJECT_URL>/-/releases/v<version>` |
| `GITLAB_RELEASE_VERSION` | De versie waarvoor de GitLab Release is aangemaakt |

**Bestanden en opslag:** `<output-dir>/release.md` bevat de toelichting. De GitLab Release en assetlinks staan in GitLab. De module uploadt de gelinkte packages, images of charts niet opnieuw.

**Vervolgjob:** gebruik `needs` met artifacts om de release-URL, versie of toelichting te gebruiken. Koppel deze module zelf ook rechtstreeks aan de jobs die de image- en chartvariabelen leveren.

**Bij opnieuw uitvoeren:** Deze job maakt een release aan en werkt een bestaande release niet bij. Controleer na een netwerkfout of de API-aanroep al is verwerkt voordat je de job opnieuw start.

## Eigen gedrag toevoegen

Gebruik een gewone GitLab-job voor een extra stap met een eigen image. Gebruik hooks voor kleine aanvullingen binnen de modulejob.

### Extra stap: een gewone GitLab-job

Dit fragment voegt een verplichte controle toe tussen bestaande jobs `build` en `publish`. De build publiceert `package.jar` als artifact en de stage `check` is gedeclareerd. Stel `CHECK_IMAGE` in op een goedgekeurde image met een POSIX-shell en de tools voor de controle.

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

GitLab start `publish` nadat beide vereiste jobs zijn geslaagd. De exitcode van de controle bepaalt het resultaat. De directe afhankelijkheid van `build` levert ook de bestanden aan; artifacts worden niet automatisch doorgegeven via tussenliggende jobs. Vervang de voorbeeldcontrole op een niet-leeg bestand door de benodigde functionele of technische controle. Zie [GitLab needs](https://docs.gitlab.com/ci/yaml/needs/) en [jobartifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/).

Publiceer aanvullende waarden in een bestand onder `artifacts:reports:dotenv` en haal de artifacts van die job op met `needs`. Gebruik voor gestructureerde gegevens een JSON-artifact. Beheer geheimen via GitLabs voorzieningen voor toegangsgegevens. Een stap die een artifact wijzigt, moet de nieuwe versie publiceren en de benodigde scans en verificatie voor die versie regelen. Zie [dotenv-variabelen](https://docs.gitlab.com/ci/variables/dotenv_variables/).

### Kleine aanvulling binnen een component

De volgende optionele inputs zijn een afspraak van onze bibliotheek boven op GitLabs joblifecycle:

| Componentinput | Uitvoering | Gevolg bij fouten |
|---|---|---|
| `pre-hook` | In `before_script`, na de gedeelde voorbereiding | De job faalt |
| `post-hook` | Aan het einde van `script`, vóór publicatie van outputs | De job faalt |
| `cleanup-hook` | In `after_script`, in een nieuwe shell | Opruimen naar beste vermogen; maakt een geslaagde job niet alsnog rood |

Verplichte controles horen in `script` of in een eigen verplichte job. `after_script` is bedoeld voor opruimen. Elke component verwijst voor deze fasen naar [shared/module.yml](../shared/module.yml). De opmerkingen in dat bestand leggen de YAML-referenties uit. Zie [GitLabs jobuitvoering](https://docs.gitlab.com/ci/jobs/job_execution/).

Alle drie de hooks zijn standaard leeg. De ingebouwde controles staan in de modulecode: de taakspecifieke controles draaien vóór de posthook, de gedeelde controle van outputvariabelen erna. Bestanden worden na de posthook niet opnieuw inhoudelijk gecontroleerd. Zie de [modulebeschrijvingen](#actief-een-module-kiezen) voor de bestaande garanties en beperkingen. Laat een hook die bestanden wijzigt ook het gewijzigde resultaat controleren.

Hookpaden zijn relatief aan de repository van de afnemer. Hooks worden met `sh` uitgevoerd vanuit de werkmap van de component. Ze draaien als subprocessen; geef resultaten terug via bestanden. De inhoud van `hook-parameters-json` komt in `CI_MODULE_PARAMETERS_FILE`. Extra outputs schrijf je naar `CI_MODULE_EXTRA_OUTPUTS`, met de componentprefix gevolgd door `_CUSTOM_`. Zet geen geheimen in hooks of outputs. Er zijn voorbeelden voor [vóór de build](../examples/hooks/pre-build.sh), [na de build](../examples/hooks/post-build.sh) en [opruimen](../examples/hooks/cleanup.sh).

Geef hooks mee als componentinputs, bijvoorbeeld `post-hook: ci/hooks/post-build.sh`. Vervang daarvoor niet de lijsten `before_script`, `script` of `after_script`: GitLab voegt die niet automatisch samen. Cleanup is niet gegarandeerd na elke timeout of het wegvallen van een runner. Hooks zijn vertrouwde applicatiecode; zij vormen geen beveiligingsgrens.

Het verwijderde callbackprotocol wordt vervangen door gewone jobs met `needs`: plaats de extra bewerking in een job, publiceer haar resultaten en laat de volgende job daarvan afhangen. Haal eventuele eerdere artifacts rechtstreeks bij hun producent op. Zie [de ontwerpkeuze](reuse-and-standards.md#bewuste-keuzes-in-de-demo).

## TODO: nog niet actief

Deze modules staan in `modules/todo/`. Ze draaien niet in de standaardpipeline en staan niet in het keuzemenu van **CI samples**. Het uitgebreide `examples/full-pipeline`-voorbeeld toont hun beoogde gebruik; het is geen gevalideerde demo van deze integraties.

| Module | Beoogde taak | Nodig vóór activering |
|---|---|---|
| [npm-audit — TODO](../modules/todo/npm-audit.yml) | Kwetsbaarheden in npm-dependencies controleren | Auditbeleid, uitzonderingen en een echte sample; `npm-test` en Maven Dependency-Check vervangen deze controle niet |
| [fortify — TODO](../modules/todo/fortify.yml) | Fortify-scan en beleidscontrole | Gekozen editie/licentie, server, credentials en gevalideerde integratie; er is nog geen Fortify-installatie |
| [image-scan — TODO](../modules/todo/image-scan.yml) | Trivy-scan, CycloneDX-SBOM en ernstgrens | Scannerimage, actuele kwetsbaarheidsdatabase, beleid en integratievalidatie |
| [image-sign — TODO](../modules/todo/image-sign.yml) | Image-digest met Cosign ondertekenen | Beheerde signing-identiteit of sleutel, rechten en integratievalidatie |
| [image-verify — TODO](../modules/todo/image-verify.yml) | Imagehandtekening controleren | Vertrouwensbeleid en tests met geldige, ontbrekende en ongeldige handtekeningen |
| [zap-baseline — TODO](../modules/todo/zap-baseline.yml) | Passieve ZAP-scan van de gedeployde applicatie | Scanconfiguratie, beoordeelde uitzonderingen en een uitvoerbare sample |

Verplaats een module pas naar `templates/` nadat er een concrete afnemer is en de echte integratie is gevalideerd. De mapnaam **TODO** zegt dat de module nog niet is geactiveerd; niet dat er nog geen code bestaat. Zie [outputs van toekomstige modules](reference.md#modules-voor-toekomstig-gebruik) en [afspraken vóór activering](../modules/todo/README.md).

## Optionele standaardpipeline

[java-service.yml](../pipelines/java-service.yml) is een kant-en-klare samenstelling van dezelfde modules. Deze ondersteunt één Java-applicatie of een Maven-reactor met één deploybare Java-module, eventueel met een Angular-UI. Meerdere Maven-modules betekenen niet automatisch meerdere deployables. Gebruik voor meer deployables expliciete module-instanties zoals in de voorbeelden; automatische verdeling over een willekeurig aantal deployables is niet geïmplementeerd.

De uitgestelde Helm-keuze, dev-lock en handmatige patchrelease van de standaardpipeline zijn optioneel organisatiebeleid. Losse modules vereisen deze afspraken niet. [GitLabs componentadvies](https://docs.gitlab.com/ci/components/#write-a-component) beveelt configureerbare jobs, weinig afhankelijkheden en duidelijke gebruiksvoorbeelden aan; daarop baseren we deze bibliotheek.
