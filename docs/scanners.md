# Scanners in de lokale demo

De standaardpipeline voert scans uit vóór publicatie. Je hoeft hiervoor geen extern account te maken, API-key aan te vragen of sleutelbestand te downloaden. De platforminrichting regelt de verbindingen; de applicatie bevat geen scanscripts.

| Component | Controle | Wanneer |
|---|---|---|
| `sonar` | Broncodeanalyse en de quality gate van de lokale SonarQube Community Build | Op de beschermde `main` en tijdens een release |
| `dependency-check` | Bekende kwetsbaarheden in Maven-dependencies, inclusief transitieve dependencies | Bij iedere verplichte validatie, ook in merge requests |

Publicatie wacht op beide controles. Een afgekeurde controle, toolfout of timeout laat de job falen. Er is geen aparte gatejob. Rapporten blijven voor foutonderzoek beschikbaar als GitLab-artifacts; outputvariabelen verschijnen pas na succes.

## Waar vind je de resultaten?

| Weergave | Doel |
|---|---|
| Job- en pipelinestatus | Geslaagd, mislukt of nog bezig. Met **Pipelines must succeed** blokkeert een mislukte verplichte pipeline het mergen. |
| Testrapport in de MR | GitLabs testsamenvatting toont aantallen en aanklikbare foutdetails uit JUnit. Dezelfde rapporten blijven onder **Tests** en bij de jobs beschikbaar. |
| Sonar-reactie | Bij een geschikte Sonar-editie verzorgt de ingebouwde GitLab-integratie de MR-samenvatting. Onze Community-inrichting plaatst alleen een samenvatting bij de werkelijk geanalyseerde commit. |
| Volledig rapport | De joblink **Open SonarQube** opent het dashboard; Dependency-Check bewaart HTML en JSON als jobartifacts. |
| Badge op de projectpagina of in de README | Optioneel overzicht van bijvoorbeeld de laatste buildstatus. Geen vervanging voor het resultaat van een specifieke MR. |

Dependency-Check levert ook zijn native JUnit-formaat aan. Daardoor kun je scanbevindingen lezen in GitLabs testoverzicht zonder eerst HTML te downloaden. De controles staan bij de job `dependency-check` en zijn geen functionele tests. Dit is onze CE-keuze; het is geen vervanging voor de uitgebreidere securityweergave van GitLab Ultimate.

De rapporten moeten uit de pipeline van het betreffende project komen. Een validatiepipeline die samples in een **ander project** start, neemt hun testrapporten niet over in de bibliotheek-MR. Childpipelines binnen hetzelfde project ondersteunen die weergave wel; onze samples gebruiken daarvoor `strategy: mirror`. Zie [GitLabs testrapporten](https://docs.gitlab.com/ci/testing/unit_test_reports/) en [childpipelines](https://docs.gitlab.com/ci/pipelines/downstream_pipelines/#view-child-pipeline-reports-in-merge-requests).

## SonarQube

SonarQube Community Build is gratis en draait lokaal op [localhost:9000](http://localhost:9000). De inrichting maakt automatisch beperkte accounts en analysetokens voor `hello-world` en `ci-samples` aan. GitLab krijgt het analysetoken als gemaskeerde en beschermde variabele `SONAR_TOKEN`. `SONAR_HOST_URL` en `SONAR_PROJECT_KEY` bepalen de lokale bestemming.

De installer regelt ook afzonderlijke rapportagetokens: `SONAR_REPORT_TOKEN` voor lezen en `GITLAB_REPORT_TOKEN` voor een reactie bij de geanalyseerde commit. De centrale Python-helper draait vanuit de scanimage in `after_script`, bewaart `summary.md` en werkt bij een retry zijn eigen reactie bij. Hij controleert de analyse-ID en commit voordat hij meetwaarden publiceert. Ontbrekende of verouderde gegevens krijgen geen groen oordeel. Een fout bij het plaatsen van de reactie verandert de scanstatus niet. De precieze afspraken staan bij [de Sonar-module](modules.md#sonar).

De component gebruikt SonarScanner for Maven en wacht met `sonar.qualitygate.wait=true` op het resultaat. `gate-timeout` staat standaard op 300 seconden. De standaardpipeline schakelt `sonar.maven.scanAll` in om ook niet-Java-bronnen, waaronder de Angular-UI, mee te nemen. Gegenereerde bestanden en dependencycaches zijn uitgesloten. Testdekking kan alleen worden beoordeeld als de applicatie ook coverage-rapporten aanlevert; een geslaagde analyse is geen bewijs dat zulke rapporten aanwezig zijn.

Community Build ondersteunt geen afzonderlijke analyse van featurebranches en merge requests. Daarom draait Sonar in deze demo op de beschermde hoofdtak. Voor analyse vóór het mergen is een passende andere editie of integratie nodig. Zie [Sonars editieoverzicht](https://www.sonarsource.com/products/sonarqube/downloads/) en [de ingebouwde quality gate](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/ci-integration/overview).

## Dependency-Check zonder API-key

De component ondersteunt NVD-feeds in JSON 2.0-formaat via `nvd-datafeed-url`. Los gebruikt zij standaard de openbare NVD-feed. De lokale organisatieconfiguratie kiest de dagelijks bijgewerkte mirror van de Dependency-Check-beheerders. Daarmee is geen NVD-account nodig. GitLab bewaart de lokale database in `.cache/dependency-check/`; de eerste uitvoering duurt langer omdat de database dan nog gevuld moet worden.

De grens `fail-cvss` is standaard 7. Dit is onze beleidskeuze, geen universele norm. De optionele Sonatype OSS Index-controle staat uit omdat we voor deze demo geen extra account instellen. De NVD-controle blijft verplicht. Dit controleert Maven-dependencies; de npm-lockfile wordt hiermee niet geaudit.

Feedgebruik is een ondersteunde Dependency-Check-optie. De keuze voor de publieke mirror is een demo-afspraak: de beheerders werken deze naar beste vermogen dagelijks bij, zonder beschikbaarheidsgarantie. Gegevens kunnen achterlopen. Kies in een echte organisatie een beheerde bron en afspraken over actualiteit, caching en uitzonderingen. Zie [Dependency-Check-feeds](https://dependency-check.github.io/DependencyCheck/data/mirrornvd.html) en [Maven-instellingen](https://dependency-check.github.io/DependencyCheck/dependency-check-maven/check-mojo.html).

## TODO: nog niet actieve controles

De volledige lijst met resterend werk staat in [het TODO-overzicht](modules.md#todo-nog-niet-actief). Voor beveiligingscontroles gaat het om `npm-audit`, `fortify`, `image-scan`, `image-sign`, `image-verify` en `zap-baseline`.

`fortify` blijft in `modules/todo/`. Er is geen geschikte gratis Community-editie vastgesteld; de beschikbare Fortify-integraties vereisen een gekozen editie, licentie en inrichting. Een gratis connector of proefperiode maakt de scanner niet vrij bruikbaar. De samengevoegde component voor scan en beleidscontrole is wel behouden voor later gebruik. Zie de [adapterafspraken](fortify-adapters.md).

Ook `image-scan` blijft voorlopig in `modules/todo/`. Die component combineert Trivy-imagescanning met een CycloneDX-SBOM. Er is geen losse `sbom`-module meer. Signing, verificatie en ZAP zijn nog geen verplichte controles van deze demo.

## Losse modules gebruiken

Je kunt beide actieve scanmodules ook opnemen in een zelf samengestelde pipeline. Begin met [het Sonar-voorbeeld](../examples/modules/sonar.yml) of [het Dependency-Check-voorbeeld](../examples/modules/dependency-check.yml). Een tool-image is verplicht; scanner-versies, bewaartermijn en timeouts hebben vaste standaardwaarden in de component. Geef via `needs` de build-/testartifacts door en laat publicatie op de scannerjobs wachten.

De aanvullende outputs zijn `SONAR_TASK_FILE` en `DEPENDENCY_CHECK_REPORT_DIR`. Beide publiceren daarnaast de gebruikelijke status-, commit- en pipelinevariabelen. Sonars status omvat ook de quality gate. De native exitcode en GitLabs afhankelijkheden bepalen of de pipeline doorgaat.
