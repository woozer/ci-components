# Applicatie en platform inrichten

Deze uitgebreide handleiding behandelt ook toekomstige scan-/signingmodules. Begin voor de actieve modules met de [modulehandleiding](modules.md) en [uitvoerbare voorbeelden](../examples/samples/README.md).

## Eigen images per taak

Elke module vereist de input `image`. Er is geen globale image of verplicht gedeelde image. Het optionele organisatieprofiel biedt per taak een imagevariabele die je kunt aanpassen. Taken mogen dezelfde image gebruiken als hun toolvereisten overeenkomen. Zet goedgekeurde images vast met `@sha256:<64 hexadecimal characters>`. Zie [standaardwaarden en profielen](defaults.md) voor de verdeling van configuratie. De validatiejob van de componentrepository heeft een eigen imagevariabele buiten dat profiel.

| Voorbeeldvariabele | Benodigde inhoud |
|---|---|
| `MAVEN_BUILD_IMAGE` | Goedgekeurde JDK, vereisten voor Maven Wrapper, `sh` |
| `MAVEN_TEST_IMAGE` | Bijpassende JDK, vereisten voor Maven Wrapper, `sh` |
| `NPM_BUILD_IMAGE` | Goedgekeurde Node.js en npm, `sh` |
| `NPM_TEST_IMAGE` | Node/npm en browserlibraries als de testrunner die nodig heeft |
| `SONAR_SCANNER_IMAGE` | JDK, Maven Wrapper-vereisten, Git en eventueel Node voor JS/TS-analyse |
| `DEPENDENCY_CHECK_IMAGE` | JDK die bij de goedgekeurde plugin past en Maven Wrapper-vereisten |
| `NPM_AUDIT_IMAGE` | Node/npm, `sh` |
| `FORTIFY_IMAGE` | Gelicentieerde scanner en client voor scan én beleidscontrole, taalvereisten, Python 3, `sh` |
| `IMAGE_BUILD_IMAGE` | Rootless BuildKit met `buildctl-daemonless.sh`, Python 3, `sh` |
| `IMAGE_SCAN_IMAGE` | Trivy, CA-certificaten, `sh` |
| `IMAGE_SIGN_IMAGE` | Cosign, KMS-authenticatie, CA-certificaten, `sh` |
| `IMAGE_VERIFY_IMAGE` | Cosign, CA-certificaten, `sh` |
| `HELM_TEST_IMAGE` | Gekozen Helm-majorversie, kubectl, CA-certificaten, `sh` |
| `HELM_PRODUCTION_IMAGE` | Gekozen Helm-majorversie, kubectl, CA-certificaten, `sh` |
| `CUCUMBER_IMAGE` | JDK, Maven Wrapper-vereisten en eventueel browserlibraries |
| `ZAP_IMAGE` | Meegeleverde `zap-baseline.py` van ZAP, schrijfbare `/zap/wrk`, `sh` |
| `CI_VALIDATION_IMAGE` | Python 3, Ruby met standaard YAML-library, `sh`; alleen voor deze componentrepository |

Alle images hebben ook POSIX-basistools nodig: `awk`, `grep`, `wc`, `printenv`, `cat`, `cp`, `mv`, `rm` en `mkdir`. Minimale of distroless images kunnen een kleine interne uitbreiding nodig hebben om de shell toe te voegen. Een image hoeft geen tools voor andere bouwblokken te bevatten. Neem tools op in beheerde images en download geen willekeurige binaries via hooks.

Gebruik bijpassende Java-/Node-versies voor build en tests. Configureer interne CA-certificaten, registry-toegang en proxies. Ook rootless BuildKit vereist een runner die de benodigde user-namespace- en mount-systeemaanroepen toestaat. Valideer dit met het runnerteam. Zie [GitLab BuildKit-inrichting](https://docs.gitlab.com/ci/docker/using_buildkit/).

## Diensten instellen

- Stel `SONAR_HOST_URL` in op HTTPS en configureer `SONAR_PROJECT_KEY` en een beperkt `SONAR_TOKEN`. De component voert de analyse uit met `sonar.qualitygate.wait=true`. SonarScanner wacht zelf op de gate en laat de job falen bij een afgekeurde gate of timeout. De input `gate-timeout` staat standaard op 300 seconden en moet binnen `job-timeout` passen. Na succes publiceert de component CE-taakmetadata en `SONAR_STATUS=passed`. Zie [Sonar-analyse en quality gates](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/ci-integration/overview).
- Dependency-Check gebruikt een openbare NVD-feed zonder API-key. Kies zo nodig een andere bron met `nvd-datafeed-url` en cache `.cache/dependency-check/`. De plugin-versie heeft een vaste default. Regel actualiteitscontroles en uitzonderingsbeleid voordat veel projecten tegelijk scannen; zie de [scanhandleiding](scanners.md).
- Richt Fortify in met de adapters uit `fortify-adapters.md`. Geef scan- en gatecredentials alleen de benodigde rechten.
- Schakel de GitLab-containerregistry in. Configureer Trivy-/Cosign-authenticatie via hun ondersteunde credentials of een pre-hook. De BuildKit-component maakt standaard een tijdelijke registry-configuratie met het GitLab-jobtoken en verwijdert die in `after_script`. Dit bestand staat buiten de artifactmap.
- Stel `COSIGN_KEY_URI` in op de goedgekeurde KMS-URI en gebruik kort geldige KMS-credentials voor de signingjob. Stel `COSIGN_PUBLIC_KEY` in op een goedgekeurd sleutelbestand of verificatie-URI. Regel passende vertrouwens- en transparantieloginstellingen. Dit startpunt ondertekent images. Maven-publicatie kan, afhankelijk van de repositoryafspraken, een aparte component voor GPG-ondertekening/publicatie vereisen.
- Stel `KUBE_CONTEXT` per test-/productieomgeving in. Gebruik de GitLab Kubernetes-agent of een pre-hook die een kort geldige kubeconfig ophaalt. Beperk RBAC tot de namespace. Als applicatiejobs geen namespaces mogen maken, laat het platform dat doen en stel `create-namespace: false` in op `helm-deploy`. Via `kubeconfig-variable` kun je een bestandsvariabele kiezen zonder de context te overschrijven.
- Configureer protected omgevingen, goedkeuringen en bevoegde productiedeployers. De handmatige voorbeeldjob pauzeert de pipeline. Werkelijke goedkeuring en autorisatie zijn GitLab-instellingen en hangen af van de editie.

## Afspraken voor Maven en npm

Maven-componenten gebruiken standaard een uitvoerbare Maven Wrapper in de ingestelde werkmap. `maven-build`, `maven-publish`, `jib-build`, `cucumber-test` en `sonar` accepteren ook `maven-executable: mvn` om Maven uit de goedgekeurde image te gebruiken. Commit de versie- en checksumconfiguratie van de wrapper. Bij een `only-script` wrapper met een ZIP-distributie en checksum moet de tool-image ook `unzip` bevatten. Zet Surefire-, Failsafe-, JaCoCo- en scanpluginversies vast in de parent-POM of componentinputs.

Het profiel `ci-unit` moet JaCoCo `prepare-agent` vóór de tests activeren en Surefire instellen. De testcomponent voert `test jacoco:report` uit. Maak het XML-rapport beschikbaar voor Sonar. `sonar` behoudt opgehaalde coverage-artifacts en installeert reactorartifacts met overgeslagen tests om afhankelijkheden tussen modules op te lossen. Die voorbereiding kan opnieuw compileren/verpakken; de release-OCI-image wordt nog steeds één keer gebouwd vanuit de buildartifacts.

Koppel in de POM de Failsafe-doelen `integration-test` en `verify`, laat een echte Cucumber-suite ontdekken en schrijf JUnit XML naar `target/failsafe-reports`. De testcode leest `cucumber.base-url`. Stuur Surefires `skipTests` aan via een eigen property `skipUnitTests`. Gebruik geen globale `skipTests` voor Cucumber, omdat daarmee ook Failsafe kan worden overgeslagen. Laat de suite falen als het ingestelde tagfilter geen scenario's selecteert. Modules die bewust geen tests bevatten, hebben een beoordeelde afzonderlijke discoveryconfiguratie nodig. Zie [Cucumber met Failsafe](https://maven.apache.org/components/surefire/maven-failsafe-plugin/examples/cucumber.html).

Cucumber activeert standaard geen Maven-profiel. Staat Failsafe in een profiel, geef de naam dan expliciet mee, bijvoorbeeld `profile: cucumber-ci`. Het uitgebreide pipelinevoorbeeld doet dat. Gebruik `target-url-variable: ""` wanneer de tests zelf de applicatie starten. Geef anders de naam door van de URL-output van een eerdere deploymentjob.

Commit `package-lock.json` en de goedgekeurde npm-configuratie. `build` schrijft naar de ingestelde uitvoermap, standaard `dist`. `test:ci` draait zonder interactie, faalt als er geen tests zijn en maakt `reports/junit.xml` aan. Schrijf ook `coverage/lcov.info` als Sonar JS/TS-coverage gebruikt. De npm-build-, test- en auditcomponenten installeren ieder hun dependencies vanuit dezelfde lockfile.

De Sonar-component gebruikt de Maven-scanner. Analyseer je Java en npm als één project, neem dan frontendbronnen en LCOV op in de POM-/Sonar-configuratie. Gebruik voor een afzonderlijk frontendproject een eigen Sonar-CLI-component met overeenkomstige outputs. Geef iedere analysejob een unieke jobnaam en outputprefix; laat de bijbehorende scanner ook de gate afhandelen.

`image-scan` scant de aangeleverde digest één keer met Trivy. Het volledige JSON-rapport bevat alle gevonden packages en ernstniveaus. `trivy convert` maakt daar een CycloneDX-SBOM van en controleert vervolgens de grens HIGH/CRITICAL. Beide rapporten blijven bij een afgekeurde gate beschikbaar als artifacts; succesoutputs verschijnen alleen bij een geslaagde job. Zie [Trivy-rapportconversie](https://trivy.dev/docs/latest/configuration/reporting/#converting).

## Afspraken voor deployment

Gebruik voor Java `jib-build`, een basisimage met vaste digest en Maven-settings voor de registry. Geef de `IMAGE_REF`-output door. De component gebruikt Jibs standaardproperties `jib.to.image` en `jib.from.image`; applicatiespecifieke imageproperties in de POM zijn niet nodig. HTTP-toegang tot de registry vereist een expliciete keuze voor de lokale testomgeving. `maven-publish` verzorgt publicatie naar Maven-repositories afzonderlijk.

Bij de generieke component `image-build` kopieert de Dockerfile artifacts uit `backend/**/target` en `frontend/dist` van de producerende jobs. Haal geen buildoutputs zonder vaste versie op. Zet basisimages vast en sluit caches, credentials en ongerelateerde bestanden uit via `.dockerignore`.

`helm-publish` verpakt een chart met versie en publiceert die naar een OCI-repository. Geef de outputs `REF` en `VERSION` door aan `helm-deploy` via `chart-variable` en `chart-version-variable`. Elke Helm-job die authenticatie nodig heeft, voert een registry-loginhook uit. `plain-http` is standaard `false`.

Commit `Chart.lock` om chartdependencies vast te leggen. De chart moet precies de aangeleverde repository en digest gebruiken:

```yaml
# Helm template fragment inside the chart's container definition
image: "{{ .Values.image.repository }}@{{ required \"image.digest is required\" .Values.image.digest }}"
```

Laat values-bestanden de ingress-host op de `target-url` afstemmen. De component kan geen chartspecifiek ingress-veld afleiden. Configureer readiness-probes en dienstafhankelijkheden. Helm-majorversie 4 is standaard; kies `helm-major: 3` voor een Helm 3-image. De opties verschillen: Helm 4 gebruikt `--rollback-on-failure`, Helm 3 `--atomic`. Zie [Helm 4 upgrade](https://docs.helm.sh/docs/helm/helm_upgrade/) en [Helm 3 upgrade](https://docs.helm.sh/docs/v3/helm/helm_upgrade/).

Het uitgebreide voorbeeld gebruikt een unieke testnamespace en URL per pipeline. Zo kan een andere deployment de applicatie niet vervangen tijdens Cucumber en ZAP. Richt verloop of geplande cleanup voor deze namespaces in. Een resourcegroep alleen op de deploymentjob houdt geen lock vast tijdens volgende testjobs. Voor gedeelde omgevingen bestaan aanvullende planningspatronen; zie het [onderzoek naar deploymentvolgorde](deployment-concurrency.md).

Lever een beoordeeld `ci/zap/rules.tsv` aan. ZAP baseline gebruikt standaard passieve controles en meldt bevindingen als waarschuwingen. Deze component blokkeert op exitcodes 1, 2 en 3. Gebruik expliciete, beoordeelde uitzonderingen. Voeg zo nodig geauthenticeerde actieve/API-scans toe als aparte componenten. Zie [ZAP baseline](https://www.zaproxy.org/docs/docker/baseline-scan/).

Productie gebruikt dezelfde digestoutput als de testdeployment en wacht op beide integratiecontroles. Stel handtekeningverificatie bij clustertoelating in en voorkom verouderde deployments in GitLab. Beoordeel een rollback als afzonderlijke deploymentbeslissing. Bewaar releasebewijs duurzaam gedurende de vereiste auditperiode; de standaard artifactbewaartermijn van zeven dagen moet daarvoor zo nodig worden aangepast.

## Een module uitbreiden

Kopieer voorbeeldhooks naar de repository van de afnemende applicatie en geef de paden mee:

```yaml
include:
  - component: $CI_SERVER_FQDN/platform/ci-components/maven-build@1.0.0
    inputs:
      image: $MAVEN_BUILD_IMAGE
      working-directory: backend
      output-prefix: SERVICE_A_BUILD
      pre-hook: ci/hooks/pre-build.sh
      post-hook: ci/hooks/post-build.sh
      cleanup-hook: ci/hooks/cleanup.sh
```

De voorbeeld-post-hook publiceert `SERVICE_A_BUILD_CUSTOM_BUILD_LABEL`. Een vervolgjob kan die samen met de ingebouwde outputs lezen via `needs` met artifacts. Eigen outputnamen beginnen met `<PREFIX>_CUSTOM_`. Waarden zijn niet-leeg en beslaan één regel. Het totale dotenv-bestand blijft binnen 5 KB. Houd het aantal overgenomen variabelen binnen de dotenv-limiet van de instance. Gebruik een JSON-artifact voor grote of gestructureerde gegevens.
