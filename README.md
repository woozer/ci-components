# GitLab CI-modules

Stel zelf een pipeline samen met zelfstandig bruikbare modules, of gebruik de optionele standaardpipeline voor Java. Elke module voert één herkenbare taak uit, kiest een eigen image en publiceert benoemde outputs. Je pipeline bepaalt `stages`, `needs`, voorwaarden en aanvullende jobs.

**Beschikbaarheid:** 15 actieve modules hebben uitvoerbare samples. Daarnaast staan 6 modules op **TODO**: `npm-audit`, `fortify`, `image-scan`, `image-sign`, `image-verify` en `zap-baseline`. Ze draaien niet in de demo en zijn niet selecteerbaar in **CI samples**. Zie [status en resterend werk per module](docs/modules.md#todo-nog-niet-actief).

## Bekijken, clonen en installeren

De demo bestaat uit vier openbare repositories:

| Repository | Inhoud |
|---|---|
| [ci-components](https://github.com/woozer/ci-components) | Losse modules, uitvoerbare voorbeelden, moduletests en de demo-installer |
| [ci-pipelines](https://github.com/woozer/ci-pipelines) | Standaardpipeline `java-service`, eigen versies, pipelinetests en gebruiksdocumentatie |
| [hello-world](https://github.com/woozer/hello-world) | Zelfstandige Java-backend, Angular-UI, Helm-charts en applicatietests |
| [ci-samples](https://github.com/woozer/ci-samples) | Volledige testapplicatie met een keuzelijst om de module- en pipelinevoorbeelden uit te voeren |

Elke repository kan afzonderlijk worden bekeken en gecloned. Volg voor een nieuwe Mac de [installatiehandleiding](installation.md): Docker-instellingen, installatie, validatie en inloggen staan daar bij elkaar. Haal voor de volledige demo alle vier samen op:

```sh
git clone --recurse-submodules https://github.com/woozer/ci-components.git
cd ci-components
```

`ci-components` verwijst met Git-submodules naar vaste commits van `ci-pipelines` onder `pipelines/`, `hello-world` onder `java/` en `ci-samples` onder `infra/seed/ci-samples/`. Elk onderdeel wordt in zijn eigen repository beheerd. Voor alleen de CI-bibliotheek kun je `--recurse-submodules` weglaten.

De [installer](installation.md) vult vier gelijknamige projecten in de lokale GitLab vanuit deze checkouts. Bestaande, gevulde GitLab-repositories worden behouden. GitHub bevat de openbare broncode; de pipelines draaien in GitLab. Links naar `localhost` werken na installatie op je eigen machine. De applicatie kan ook [zelfstandig worden gebouwd en getest](https://github.com/woozer/hello-world#readme).

## Zelf een pipeline samenstellen

1. Kies een module uit de [modulehandleiding](docs/modules.md).
2. Neem het minimale voorbeeld over, kies een uitgebrachte bibliotheekversie zoals `2.0.0` en vul de verplichte inputs in. Optionele standaardwaarden kun je weglaten.
3. Verbind jobs met GitLabs `needs` en artifacts/dotenv. Begin met een [uitvoerbaar voorbeeld](examples/samples/README.md).

| Klein beginnen | Een volgende stap toevoegen | Modules herhalen |
|---|---|---|
| [Maven-build](examples/samples/maven-build.yml) | [Bouwen → testen](examples/samples/build-and-test.yml), [image/chart → deployment → testen](examples/samples/deploy-and-test.yml) | [Twee deployables](examples/samples/two-deployables.yml) |

Start deze via [CI samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new): kies `sample` en daarna **New pipeline**. Dezelfde YAML-bestanden dienen als voorbeeld voor afnemers en valideren modulewijzigingen in echte GitLab-jobs. Lees [hoe de validatie werkt](examples/samples/README.md#testisolatie-en-bewijs).

Voor één module heb je geen standaardpipeline, organisatieprofiel of releaseproces nodig. Je platform levert de images en toegangsgegevens voor diensten; de verplichte inputs en uitvoeringsvoorwaarden staan per module beschreven. De gedeelde afhandeling van hooks wordt automatisch ingeladen.

Gebruik binnen een eigen pipeline dezelfde [componentversie](docs/component-versions.md) voor alle losse modules. De standaardpipeline heeft een eigen versie in **ci-pipelines** en zet haar moduleafhankelijkheden vast. Wijzigingen vóór publicatie testen we op hun exacte commit-SHA.

De actieve modules zijn ook vindbaar in de [CI/CD Catalog van de lokale GitLab](http://localhost:8929/explore/catalog), onder **ci-components**. De catalogus toont de gepubliceerde versies en inputs. Zie [componentversies en cataloguspublicatie](docs/component-versions.md#publicatie-in-de-cicd-catalog) voor de inrichting en publicatiestappen.

## Standaardpipeline voor de Java-sample

Gebruik [java-service uit ci-pipelines](https://github.com/woozer/ci-pipelines) voor bouwen, testen, publiceren, Helm-deployment en releases. Deze cataloguscomponent heeft een eigen versie en gebruikt vaste versies van de bouwblokken. Alleen `maven-project` is verplicht; `ui-directory: ui` schakelt de optionele Angular-UI in.

```yaml
include:
  - component: $CI_SERVER_FQDN/root/ci-pipelines/java-service@1.1.0
    inputs:
      maven-project: hello-app
```

De [pipelinehandleiding](https://github.com/woozer/ci-pipelines#dagelijks-gebruik) beschrijft bouwen, profielkeuze en de releaseknop. Het [applicatievoorbeeld](https://github.com/woozer/hello-world/blob/main/.gitlab-ci.yml) laat ook het formulier op **New pipeline** zien. De standaard ondersteunt één Java-deployable binnen een Maven-reactor en een optionele UI. Gebruik voor meer deployables expliciete module-instanties.

## Waar vind je wat?

| Vraag | Handleiding |
|---|---|
| Hoe gebruik ik een module en verbind ik jobs? | [Modulehandleiding](docs/modules.md): werking, voorwaarden, inputs, defaults, outputs en hooks bij elkaar |
| Hoe voer ik de voorbeelden uit? | [Samples gebruiken en valideren](examples/samples/README.md) |
| Hoe bedien ik de standaardpipeline? | [Pipelinekeuzes](docs/pipeline-options.md) en [releasebeleid](docs/releases.md) |
| Hoe richt ik het platform in? | [Lokale installatie](installation.md) of [platformvoorwaarden](docs/setup.md) en [eigen organisatie](docs/real-environment.md) |
| Hoe onderhoud ik de bibliotheek? | [Ontwerp en onderhoud](docs/reference.md) en [standaarden en keuzes](docs/reuse-and-standards.md) |

We volgen GitLabs advies over componenttests en hergebruik. GitLab levert jobs, afhankelijkheden, artifacts, inputs en locks; de keuzetermijn van tien seconden en automatische patchversie zijn afspraken van onze optionele standaardpipeline. Zie [standaarden en keuzes](docs/reuse-and-standards.md).

De vijftien actieve modules staan in `templates/`; zes toekomstige modules staan in [modules/todo/](modules/todo/). GitLab verwerkt de component-YAML rechtstreeks. Profielkeuze en releasereservering leveren tijdens de uitvoering een klein configuratieartifact voor hun childpipeline op.

De [scanhandleiding](docs/scanners.md) beschrijft SonarQube en Dependency-Check in de demo, zonder handmatig aangevraagde API-keys.
