# Hello World CI-demo

Een Spring Boot-backend met Java 25 en meerdere Maven-modules, plus een aparte Angular 22-UI via Nginx. `GET /hello` geeft `hello world` terug; `GET /api/animals` geeft zes willekeurig gekozen dieren terug. De gedeployde UI staat op [localhost:8090](http://localhost:8090).

| Module | Verantwoordelijkheid |
|---|---|
| `hello-app` | REST-applicatie en zelfstandige Jib-configuratie |
| `integration-tests` | Cucumber-API-tests en Playwright-browserscenario's |
| `ui` | Angular-applicatie, npm-build/tests en Nginx-runtime-image |

Bouw en test zonder GitLab of Docker:

```sh
./mvnw verify
```

De tests starten de backend, controleren health, begroeting, dieren en een onbekend endpoint en stoppen de backend daarna. Browserscenario's draaien via het Maven-profiel `ui` tegen een draaiende UI. Gebruik voor backend-smoketests `./mvnw -Dcucumber.filter.tags="@smoke and not @ui" verify`. In GitLab biedt **test-custom** deze keuze voor een extra uitvoering. De verplichte tests houden hun volledige suite. De Maven Wrapper heeft `unzip` nodig; een geïnstalleerde Maven 3.9.12 werkt ook.

Drie dagelijkse CI-handelingen:

1. **Bouwen:** push een branch of merge een beoordeelde MR. Backend- en Angular-tests starten automatisch. Protected `main` publiceert ook artifacts, deployt naar dev en voert API- en Playwright/Cucumber-tests uit.
2. **Ander Helm-profiel:** start **configure-deploy** opnieuw met gewijzigde waarden, wacht op succes en kies **Run again** bij **deploy-dev**. Images en charts worden hergebruikt; integratietests draaien opnieuw. Gebruik bij de eerste uitvoering binnen tien seconden **Unschedule** om waarden te kiezen. Zonder actie gelden de standaardwaarden.
3. **Release:** start **start-release** na geslaagde dev-validatie. De standaard kiest de volgende patchversie. Open de job om een minor-/majorversie op te geven. Volg **release-delivery** tot **publish-release**. Die laatste job maakt na geslaagde validatie de GitLab Release met artifactlinks aan.

De pipelines heten **CI — main** (of je branch), **Dev — deployment en integratietests** en **Release — 1.2.3** (de gereserveerde versie). GitLab toont childpipelines rechts; hun plaats verandert de afhankelijkheden niet. `start-release` wacht op geslaagde dev-validatie.

Vóór publicatie controleert OWASP Dependency-Check de Maven-dependencies en voert de lokale SonarQube Community Build broncodeanalyse met een quality gate uit. Dependency-Check draait ook in merge requests; Sonar analyseert de beschermde `main` en releases. Een afgekeurde scan blokkeert publicatie van backend en UI. Je hoeft zelf geen API-key aan te vragen; zie de [scanhandleiding](http://localhost:8929/root/ci-components/-/blob/main/docs/scanners.md) voor rapporten en beperkingen, waaronder het ontbreken van npm-audit en coverage-rapporten.

[.gitlab-ci.yml](.gitlab-ci.yml) neemt het gedeelde formulier en één centrale [java-service.yml](http://localhost:8929/root/ci-components/-/blob/main/pipelines/java-service.yml) op. CI-scripts en jobvolgorde staan in die bibliotheek. Helm leest eerst `environment/cluster/<cluster>.yaml` en daarna `environment/user/<profile>.yaml`. Het profiel `two-replicas` laat een aanpassing zien. Toegangsgegevens blijven in GitLab.

Formulier en pipeline gebruiken beide componentversie `1.0.0`. De YAML-anchor `ci_strategy` geeft diezelfde versie door als `library-ref`. Een bibliotheekupgrade verandert beide `ref`-waarden via een merge request; zie de [versieafspraken](http://localhost:8929/root/ci-components/-/blob/main/docs/component-versions.md).

GitLab regelt jobs, afhankelijkheden en locks. De keuzetermijn van tien seconden en automatische patchversie zijn organisatiebeleid. In deze demo met één gebruiker mag de auteur na geslaagde MR-controles zelf mergen. In de echte organisatie beoordeelt een tweede persoon wijzigingen vóór een merge naar een protected branch. Een handmatige releaseknop is geen goedkeuring door een ander.

Maven-packages gaan naar GitLab; images en charts naar lokale Artifactory. Ook een release wordt in dev gevalideerd. Toekomstige productiedeployment via Argo CD moet de bestaande release-image-digests gebruiken zonder opnieuw te bouwen. Zie [pipelinekeuzes](http://localhost:8929/root/ci-components/-/blob/main/docs/pipeline-options.md) en [releasebeleid](http://localhost:8929/root/ci-components/-/blob/main/docs/releases.md).

Health-endpoints:

| Deployable | Readiness | Gezond antwoord |
|---|---|---|
| Backend | [localhost:8080/actuator/health/readiness](http://localhost:8080/actuator/health/readiness) | HTTP 200, `status: UP` |
| Nginx-UI | [localhost:8090/healthz](http://localhost:8090/healthz) | HTTP 200 |

Spring Boot Actuator biedt ook `/actuator/health` en `/actuator/health/liveness` op de applicatiepoort. Standaard is alleen health beschikbaar. Kubernetes controleert iedere tien seconden; een container die nog niet gereed is, kan eerder opnieuw worden gecontroleerd. Helm wacht op alle gewenste replica's. Beide gedeployde integratiesuites wachten op beide Helm-jobs. Een readiness-timeout laat deployment falen en blokkeert de tests. Tests tijdens de build hebben geen cluster nodig.

De optionele centrale input `deployment-timeout` is standaard `5m` per deployable. Geef deze alleen mee voor een afwijking, bijvoorbeeld `deployment-timeout: 8m`. De instelling geldt ook voor releasedeployments. Een Helm-rollback kan extra tijd kosten; zie [pipelineopties](http://localhost:8929/root/ci-components/-/blob/main/docs/pipeline-options.md). UI-health controleert Nginx; browserscenario's controleren of de UI de backend kan lezen.

Voor zelfstandige Jib-builds en lokale Helm-commando's: [ontwikkelhandleiding](docs/development.md).

Bouw en test Angular afzonderlijk:

```sh
cd ui
npm ci
npm run build
npm run test:ci
```

Voer de browsertests vanuit de repositoryroot uit terwijl UI en backend draaien:

```sh
./mvnw verify -Pui -Dcucumber.base-url=http://localhost:8090
```

Dit Maven-profiel installeert en cachet de Chromium-versie die bij Playwright hoort en voert de scenario's `@ui` en `@animals` uit. GitLab-componenten zijn niet nodig. De CI-image bevat de passende browsers al. Het Cucumber-rapport staat in `integration-tests/target/cucumber/cucumber.html`, inclusief screenshots. Bij mislukte scenario's verschijnen ook bestanden `trace-*.zip` in die map.

## Unit- en integratietests

`./mvnw package` bouwt de applicatie en voert de Surefire-unittests uit. De sample schrijft JUnit-rapporten naar `hello-app/target/surefire-reports/` en JaCoCo-coverage naar `hello-app/target/site/jacoco/`.

`./mvnw verify` voert daarnaast de Cucumber-integratietests uit en start daarvoor zelf de backend. In CI doet `maven-build` de build met unittests; de aparte Cucumber-stap gebruikt `-DskipUnitTests=true` om de unittests niet opnieuw uit te voeren. Browsertests blijven apart en vereisen een draaiende UI.
