# GitLab CI-modules

Stel zelf een pipeline samen met zelfstandig bruikbare modules, of gebruik de optionele standaardpipeline voor Java. Elke module voert één herkenbare taak uit, kiest een eigen image en publiceert benoemde outputs. Je pipeline bepaalt `stages`, `needs`, voorwaarden en aanvullende jobs.

**Beschikbaarheid:** 15 actieve modules hebben uitvoerbare samples. Daarnaast staan 6 modules op **TODO**: `npm-audit`, `fortify`, `image-scan`, `image-sign`, `image-verify` en `zap-baseline`. Ze draaien niet in de demo en zijn niet selecteerbaar in **CI samples**. Zie [status en resterend werk per module](docs/modules.md#todo-nog-niet-actief).

## Bekijken, clonen en installeren

De demo bestaat uit drie openbare repositories:

| Repository | Inhoud |
|---|---|
| [ci-components](https://github.com/woozer/ci-components) | Herbruikbare modules, samengestelde pipelines, voorbeelden, bibliotheektests, documentatie en de demo-installer |
| [hello-world](https://github.com/woozer/hello-world) | Zelfstandige Java-backend, Angular-UI, Helm-charts en applicatietests |
| [ci-samples](https://github.com/woozer/ci-samples) | Volledige testapplicatie met een keuzelijst om de module- en pipelinevoorbeelden uit te voeren |

Elke repository kan afzonderlijk worden bekeken en gecloned. Volg voor een nieuwe Mac de [installatiehandleiding](installation.md): Docker-instellingen, installatie, validatie en inloggen staan daar bij elkaar. Haal voor de volledige demo alle drie samen op:

```sh
git clone --recurse-submodules https://github.com/woozer/ci-components.git
cd ci-components
```

`ci-components` verwijst met Git-submodules naar vaste commits van `hello-world` onder `java/` en `ci-samples` onder `infra/seed/ci-samples/`. De applicatiebestanden worden in hun eigen repository beheerd. Voor alleen de CI-bibliotheek kun je `--recurse-submodules` weglaten.

De [installer](installation.md) vult drie gelijknamige projecten in de lokale GitLab vanuit deze checkouts. Bestaande, gevulde GitLab-repositories worden behouden. GitHub bevat de openbare broncode; de pipelines draaien in GitLab. Links naar `localhost` werken na installatie op je eigen machine. De applicatie kan ook [zelfstandig worden gebouwd en getest](https://github.com/woozer/hello-world#readme).

## Zelf een pipeline samenstellen

1. Kies een module uit de [modulehandleiding](docs/modules.md).
2. Neem het minimale voorbeeld over, kies een uitgebrachte bibliotheekversie zoals `1.0.0` en vul de verplichte inputs in. Optionele standaardwaarden kun je weglaten.
3. Verbind jobs met GitLabs `needs` en artifacts/dotenv. Begin met een [uitvoerbaar voorbeeld](examples/samples/README.md).

| Klein beginnen | Een volgende stap toevoegen | Modules herhalen |
|---|---|---|
| [Maven-build](examples/samples/maven-build.yml) | [Bouwen → testen](examples/samples/build-and-test.yml), [image/chart → deployment → testen](examples/samples/deploy-and-test.yml) | [Twee deployables](examples/samples/two-deployables.yml) |

Start deze via [CI samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new): kies `sample` en daarna **New pipeline**. Dezelfde YAML-bestanden dienen als voorbeeld voor afnemers en valideren modulewijzigingen in echte GitLab-jobs. Lees [hoe de validatie werkt](examples/samples/README.md#testisolatie-en-bewijs).

Voor één module heb je geen standaardpipeline, organisatieprofiel of releaseproces nodig. Je platform levert de images en toegangsgegevens voor diensten; de verplichte inputs en uitvoeringsvoorwaarden staan per module beschreven. De gedeelde afhandeling van hooks wordt automatisch ingeladen.

Gebruik dezelfde [componentversie](docs/component-versions.md) voor alle modules, het gedeelde formulier en de centrale pipeline. Wijzigingen vóór publicatie testen we op hun exacte commit-SHA.

## Standaardpipeline voor de Java-sample

1. **Bouwen:** push een branch of merge een beoordeelde MR. Verplichte backend- en Angular-tests starten automatisch. Op protected `main` worden ook ontwikkelartifacts gepubliceerd, beide applicaties gedeployed en API-/browserintegratietests uitgevoerd.
2. **Ander Helm-profiel:** start **configure-deploy** opnieuw met gewijzigde waarden, wacht op succes en kies daarna **Run again** bij **deploy-dev**. Dit deployt dezelfde images/charts opnieuw en herhaalt de integratietests. Gebruik bij de eerste uitvoering binnen tien seconden **Unschedule** om vóór de deployment waarden te kiezen; anders gelden de standaardwaarden.
3. **Release:** start **start-release** na geslaagde dev-validatie. Deze job reserveert de volgende patchversie binnen `release-line`. Een andere major/minor leg je vooraf vast via een beoordeelde wijziging van die instelling. Volg **release-delivery**. De laatste job, **publish-release**, maakt de GitLab Release met toelichting en artifactlinks zodra de releaseartifacts de dev-validatie hebben doorstaan.

De pipelinenamen tonen wat er gebeurt: **CI — main** (of de featurebranch), **Dev — deployment en integratietests** en **Release — 1.2.3** (de gereserveerde versie). GitLab toont childpipelines als kaarten aan de rechterkant. Hun plaats bepaalt niet de uitvoeringsvolgorde.

De optionele [java-service.yml](pipelines/java-service.yml) stelt een pipeline samen met dezelfde modules. Deze ondersteunt één Java-deployable, ook binnen een Maven-reactor met meerdere modules, en een optionele Angular-UI. Voor meer Java-deployables kun je de losse modules gebruiken; automatische verdeling over een willekeurig aantal deployables is niet geïmplementeerd. Het [CI-bestand van de applicatie](https://github.com/woozer/hello-world/blob/main/.gitlab-ci.yml) toont het gebruik met alleen applicatiespecifieke instellingen en doorgegeven formulierkeuzes.

## Waar vind je wat?

| Vraag | Handleiding |
|---|---|
| Hoe gebruik ik een module en verbind ik jobs? | [Modulehandleiding](docs/modules.md): werking, voorwaarden, inputs, defaults, outputs en hooks bij elkaar |
| Hoe voer ik de voorbeelden uit? | [Samples gebruiken en valideren](examples/samples/README.md) |
| Hoe bedien ik de standaardpipeline? | [Pipelinekeuzes](docs/pipeline-options.md) en [releasebeleid](docs/releases.md) |
| Hoe richt ik het platform in? | [Lokale installatie](installation.md) of [platformvoorwaarden](docs/setup.md) en [eigen organisatie](docs/real-environment.md) |
| Hoe onderhoud ik de bibliotheek? | [Ontwerp en onderhoud](docs/reference.md) en [standaarden en keuzes](docs/reuse-and-standards.md) |

We volgen GitLabs advies over componenttests en hergebruik. GitLab levert jobs, afhankelijkheden, artifacts, inputs en locks; de keuzetermijn van tien seconden en automatische patchversie zijn afspraken van onze optionele standaardpipeline. Zie [standaarden en keuzes](docs/reuse-and-standards.md).

De vijftien actieve modules staan in `templates/`; zes toekomstige modules staan in [modules/todo/](modules/todo/). Er is geen eigen handoff-keten of YAML-generator.

De [scanhandleiding](docs/scanners.md) beschrijft SonarQube en Dependency-Check in de demo, zonder handmatig aangevraagde API-keys.
