# Uitvoerbare modulevoorbeelden

Deze voorbeelden zijn gewone GitLab-pipelines, samengesteld uit losse modules. Het validatieproject voert precies deze bestanden uit. De normale pipeline van de Java-applicatie staat daar los van.

| Sample | Wat het voorbeeld laat zien |
|---|---|
| [maven-build](maven-build.yml) | Eén Maven-build, zonder andere modules |
| [build-and-test](build-and-test.yml) | Een Cucumber/Failsafe-job die artifacts van de Maven-build ophaalt |
| [deploy-and-test](deploy-and-test.yml) | Jib-image en OCI-Helm-chart → Helm-deployment en gereedheidscontrole → API-tests |
| [two-deployables](two-deployables.yml) | Backend en UI, met aparte namen en outputs voor herhaalde Helm- en Cucumber-modules |

## Starten in GitLab

1. Open [CI samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new).
2. Selecteer `main` en kies bij `sample` een pipelinevoorbeeld, een los modulevoorbeeld of `all`.
3. Behoud `library_ref` voor de ingestelde bibliotheekversie, of vul de volledige componentcommit in die je wilt testen.
4. Kies **New pipeline**. Open de childpipeline met de naam van het voorbeeld om jobs, artifacts en testrapporten te bekijken.

Bij een modulewijziging start de trigger `validate-samples` in het componentproject ook alle negentien voorbeelden. Met `strategy: mirror` neemt de componentpipeline hun resultaat over. De trigger geeft de gewijzigde componentcommit door, zodat de nieuwe code wordt getest. Een mislukte sample laat de validatie falen. De interne [include voor componentvalidatie](../../tests/samples/component-validation.yml) vult `CI_COMMIT_SHA` met GitLabs `expand_vars` in voordat de waarde naar de downstream-input gaat. Het sampleproject accepteert een volledige uitgebrachte versie of een volledige commit-SHA voor kandidaatvalidatie.

De keuzelijst bevat de vier bovenstaande pipelines en alle vijftien actieve [modulevoorbeelden](../modules/README.md). Losse modules herken je aan `module-`, bijvoorbeeld `module-sonar` of `module-npm-test`. `all` voert op de beschermde `main` alle negentien voorbeelden uit.

Sonar en de drie releasevoorbeelden vereisen de beschermde `main`. Daarom voert `all` in een merge request van het sampleproject de overige vijftien voorbeelden uit. Een expliciete keuze voor een beschermd voorbeeld op een andere branch geeft een foutmelding. Componentwijzigingen worden wel met alle negentien voorbeelden getest: de downstream-pipeline draait op de beschermde `main` van het sampleproject met de kandidaatversie van de componenten.

## Een voorbeeld in je eigen project gebruiken

Neem het gekozen bestand op met een uitgebrachte bibliotheekversie en geef dezelfde versie mee als `library-ref`:

```yaml
include:
  - project: root/ci-components
    ref: &library 1.0.0
    file: /examples/samples/build-and-test.yml
    inputs:
      library-ref: *library
```

Je kunt het voorbeeld ook kopiëren en de component-includes aanpassen. Bepaal de jobvolgorde met `stages` en `needs`. Laat optionele module-inputs weg als de standaardwaarden voldoen. Stel goedgekeurde images in via GitLab-groeps- of projectvariabelen. De bestanden onder `tests/samples/` bevatten alleen instellingen en controles voor onze testopstelling; afnemers hoeven ze niet over te nemen.

De buildvoorbeelden vereisen `JAVA_CI_IMAGE`, Java 25, Maven en een POM in de repository. De ingestelde CI-image levert `mvn`; een eigen applicatie kan ook de standaard `./mvnw` van de module gebruiken. Het testvoorbeeld verwacht dat Cucumber/Failsafe zelf de backend start. Pas die testconfiguratie aan je applicatie aan.

De deploymentvoorbeelden gebruiken de mappen `hello-app`, `helm/hello-world`, `ui` en `helm/hello-world-ui` van de sample. De paden staan expliciet in de YAML, zodat je ziet wat je voor je eigen applicatie moet aanpassen. Stel daarnaast het volgende in:

| Instelling | Doel |
|---|---|
| `JAVA_CI_IMAGE`, `HELM_CI_IMAGE`, `JAVA_RUNTIME_IMAGE` | Goedgekeurde images voor Java/Maven, Helm en de Java-runtime |
| `OCI_REGISTRY`, `OCI_REPOSITORY` | Registry en repository voor publicatie |
| `ARTIFACTORY_USERNAME`, `ARTIFACTORY_PASSWORD_FILE`, `ARTIFACTORY_MAVEN_SETTINGS` | Registry-toegangsgegevens met beperkte rechten; wachtwoord en settings zijn bestandsvariabelen |
| `SAMPLE_KUBECONFIG`, `SAMPLE_NAMESPACE`, `API_TARGET_URL` | Vooraf ingerichte testnamespace, kubeconfig met beperkte rechten en bereikbare API-URL |
| `NODE_CI_IMAGE`, `BUILDKIT_CI_IMAGE`, `BROWSER_CI_IMAGE`, `NGINX_RUNTIME_IMAGE`, `UI_TARGET_URL` | Extra images en de URL voor het UI-voorbeeld |

Commit `environment/cluster/validation-api.yaml` en voor de UI ook `validation-ui.yaml`. Daarin staan de servicerouting, het image-pull-secret en de backend-URL voor de UI. De registry-login gebruikt de gedeelde YAML `.helm-login`. Stel `HELM_REGISTRY_PLAIN_HTTP` alleen in voor een testomgeving die bewust HTTP gebruikt. De input `plain-http` staat in de voorbeelden standaard op `false`.

## Testisolatie en bewijs

Het lokale project `ci-samples` bevat een vaste kopie van de Java/Angular-applicatie. De README vermeldt de broncommit. Het project heeft een eigen namespace, Helm-releases en beperkte schrijfrechten in de registry. De backend- en UI-tests gebruiken poorten 8180 en 8190; de gewone dev-omgeving gebruikt 8080 en 8090. Een GitLab-resourcegroep op elke deploymenttrigger houdt de testomgeving bezet tijdens deployment, tests en opruimen. De job `cleanup-sample` verwijdert de testreleases ook als tests falen. Na annulering kan handmatig opruimen nodig zijn. De testcredentials hebben geen rechten in de namespace van de gewone applicatie.

`verify-sample` controleert de gebouwde artifacts, de broncommit en pipeline, en de image-, chart- en URL-outputs die volgende jobs gebruiken. Cucumber en Playwright testen de werkelijk gedeployde applicaties. GitLabs YAML-controle en de bestaande Python-contracttests vullen deze uitvoeringen aan. Alleen CI Lint kan niet aantonen dat een build of deployment werkt.

We volgen hiermee [GitLabs advies voor componenttests](https://docs.gitlab.com/ci/components/#test-the-component) en [tests met samplebestanden](https://docs.gitlab.com/ci/components/#test-a-component-against-sample-files). Het aparte project, de voorbeeldkeuze en de isolatie-instellingen zijn onze keuzes. Voor selectie en aansturing gebruiken we GitLabs [pipeline-inputs](https://docs.gitlab.com/ci/inputs/#for-a-pipeline), [downstream-pipelines](https://docs.gitlab.com/ci/pipelines/downstream_pipelines/) en [resourcegroepen](https://docs.gitlab.com/ci/resource_groups/).

## Bestanden en verantwoordelijkheden

Alle voorbeeld- en validatiebestanden staan in de componentbibliotheek `ci-components`:

| Map of bestand | Verantwoordelijkheid |
|---|---|
| [`examples/modules/`](../modules/) | Een minimaal, uitvoerbaar gebruiksvoorbeeld per actieve module |
| [`examples/samples/`](./) | Complete pipelines die afnemers kunnen overnemen |
| [`tests/samples/launcher.yml`](../../tests/samples/launcher.yml) | De samplekeuze afhandelen en de gekozen voorbeelden als childpipelines starten |
| [`tests/samples/options.yml`](../../tests/samples/options.yml) | Eén gedeelde keuzelijst voor het startformulier en de launcher |
| [`tests/samples/module-runtime.yml`](../../tests/samples/module-runtime.yml) | Lokale voorwaarden en outputcontroles voor losse modules |
| [`tests/samples/runtime.yml`](../../tests/samples/runtime.yml) | De testomgeving instellen en outputs controleren |
| [`tests/samples/deployment-runtime.yml`](../../tests/samples/deployment-runtime.yml) | Tijdelijke Helm-deployments opruimen |

Het aparte project `ci-samples` bevat de testapplicatie en de `.gitlab-ci.yml` met het startformulier. Dat bestand laadt `tests/samples/launcher.yml` uit `ci-components` via `include: project`. De launcher staat onder `tests/` omdat hij onze validatie organiseert. Dit is onze mappenindeling; GitLab schrijft die niet voor.

`include:inputs` geeft instellingen door aan een opgenomen bestand. Keuzevelden op **New pipeline** komen uit `spec:inputs` van de hoofdconfiguratie, eventueel via `spec:include`. Daarom krijgt een afnemer de samplekeuzelijst niet automatisch wanneer die alleen een module of voorbeeld opneemt.
