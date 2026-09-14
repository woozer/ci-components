# Scanners in de lokale demo

De standaardpipeline voert scans uit vóór publicatie. Je hoeft hiervoor geen extern account te maken, API-key aan te vragen of sleutelbestand te downloaden. De platforminrichting regelt de verbindingen; de applicatie bevat geen scanscripts.

| Component | Controle | Wanneer |
|---|---|---|
| `sonar` | Broncodeanalyse en de quality gate van de lokale SonarQube Community Build | Op de beschermde `main` en tijdens een release |
| `dependency-check` | Bekende kwetsbaarheden in Maven-dependencies, inclusief transitieve dependencies | Bij iedere verplichte validatie, ook in merge requests |

Publicatie wacht op beide controles. Een afgekeurde controle, toolfout of timeout laat de job falen. Er is geen aparte gatejob. Rapporten blijven voor foutonderzoek beschikbaar als GitLab-artifacts; outputvariabelen verschijnen pas na succes.

## SonarQube

SonarQube Community Build is gratis en draait lokaal op [localhost:9000](http://localhost:9000). De inrichting maakt automatisch een beperkt CI-account en een analysetoken voor `hello-world` aan. Alleen GitLab krijgt dat token, als gemaskeerde en beschermde variabele `SONAR_TOKEN`. `SONAR_HOST_URL` en `SONAR_PROJECT_KEY` bepalen de lokale bestemming.

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
