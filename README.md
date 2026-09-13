# GitLab CI-modules

Stel zelf een pipeline samen met zelfstandig bruikbare modules, of gebruik de optionele standaardpipeline voor Java. Elke module voert één herkenbare taak uit, kiest een eigen image en publiceert benoemde outputs. Je pipeline bepaalt `stages`, `needs`, voorwaarden en aanvullende jobs.

## Zelf een pipeline samenstellen

1. Kies een module uit de [modulehandleiding](docs/modules.md).
2. Neem het minimale voorbeeld over, zet de bibliotheek vast op een commit en vul de verplichte inputs in. Optionele standaardwaarden kun je weglaten.
3. Verbind jobs met GitLabs `needs` en artifacts/dotenv. Begin met een [uitvoerbaar voorbeeld](examples/samples/README.md).

| Klein beginnen | Een volgende stap toevoegen | Modules herhalen |
|---|---|---|
| [Maven-build](examples/samples/maven-build.yml) | [Bouwen → testen](examples/samples/build-and-test.yml), [image/chart → deployment → testen](examples/samples/deploy-and-test.yml) | [Twee deployables](examples/samples/two-deployables.yml) |

Start deze via [CI samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new): kies `sample` en daarna **New pipeline**. Dezelfde YAML-bestanden dienen als voorbeeld voor afnemers en valideren modulewijzigingen in echte GitLab-jobs. Lees [hoe de validatie werkt](examples/samples/README.md#testisolatie-en-bewijs).

Voor één module heb je geen standaardpipeline, organisatieprofiel of releaseproces nodig. Je platform levert de images en toegangsgegevens voor diensten; de verplichte inputs en uitvoeringsvoorwaarden staan per module beschreven. De gedeelde afhandeling van hooks wordt automatisch ingeladen.

## Standaardpipeline voor de Java-sample

1. **Bouwen:** push een branch of merge een beoordeelde MR. Verplichte backend- en Angular-tests starten automatisch. Op protected `main` worden ook ontwikkelartifacts gepubliceerd, beide applicaties gedeployed en API-/browserintegratietests uitgevoerd.
2. **Ander Helm-profiel:** start **configure-deploy** opnieuw met gewijzigde waarden, wacht op succes en kies daarna **Run again** bij **deploy-dev**. Dit deployt dezelfde images/charts opnieuw en herhaalt de integratietests. Gebruik bij de eerste uitvoering binnen tien seconden **Unschedule** om vóór de deployment waarden te kiezen; anders gelden de standaardwaarden.
3. **Release:** start **start-release** na geslaagde dev-validatie. Deze job reserveert de volgende patchversie; open de job om voor een minor- of majorrelease een andere versie in te vullen. Volg **release-delivery**. De laatste job, **publish-release**, maakt de GitLab Release met toelichting en artifactlinks zodra de releaseartifacts de dev-validatie hebben doorstaan.

De pipelinenamen tonen wat er gebeurt: **CI — main** (of de featurebranch), **Dev — deployment en integratietests** en **Release — 1.2.3** (de gereserveerde versie). GitLab toont childpipelines als kaarten aan de rechterkant. Hun plaats bepaalt niet de uitvoeringsvolgorde.

De optionele [java-service.yml](pipelines/java-service.yml) stelt een pipeline samen met dezelfde modules. Deze ondersteunt één Java-deployable, ook binnen een Maven-reactor met meerdere modules, en een optionele Angular-UI. Voor meer Java-deployables kun je de losse modules gebruiken; automatische verdeling over een willekeurig aantal deployables is niet geïmplementeerd. Het [CI-bestand van de applicatie](http://localhost:8929/root/hello-world/-/blob/main/.gitlab-ci.yml) toont het gebruik met alleen applicatiespecifieke instellingen en doorgegeven formulierkeuzes.

Naslag: [modulehandleiding](docs/modules.md), [verplichte inputs](docs/inputs.md), [outputs en uitgebreid naslagwerk](docs/reference.md), [hooks en extra jobs](docs/hooks.md), [keuzes in de standaardpipeline](docs/pipeline-options.md), [releasebeleid](docs/releases.md).

We volgen GitLabs advies over componenttests en hergebruik. GitLab levert jobs, afhankelijkheden, artifacts, inputs en locks; de keuzetermijn van tien seconden en automatische patchversie zijn afspraken van onze optionele standaardpipeline. Zie [standaarden en keuzes](docs/reuse-and-standards.md).

De vijftien actieve modules staan in `templates/`; zeven toekomstige modules staan in [modules/todo/](modules/todo/). Er is geen eigen handoff-keten of YAML-generator.

De [scanhandleiding](docs/scanners.md) beschrijft SonarQube en Dependency-Check in de demo, zonder handmatig aangevraagde API-keys.
