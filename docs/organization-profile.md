# Standaardwaarden en organisatieprofielen

Elke laag van de GitLab-configuratie heeft een eigen verantwoordelijkheid:

| Locatie | Verantwoordelijkheid |
|---|---|
| `templates/<module>.yml`, onder `spec:inputs` | Standaardwaarden, inputtypen, hooks, outputafspraken en één job |
| `examples/full-pipeline/profile.yml` | Optionele organisatiebasis: images, bewaartermijnen, timeouts, scanbeleid en standaardpaden |
| `.gitlab-ci.yml` van de applicatie | Profielinstellingen, stages, afhankelijkheden, hookscripts en regels voor promotie |

Elke module blijft zelfstandig bruikbaar. De input `image` is verplicht, zodat een Maven-job niet onbedoeld een npm-image overneemt. Er is geen globale `default:image`, apart bestand met moduledefaults, configuratieloader of YAML-generatiestap.

Dit toekomstige voorbeeld gebruikt modules uit `modules/todo/` en wordt niet door de Java-demo ingeladen. Het organisatieprofiel combineert Maven, npm en Kubernetes voor `examples/full-pipeline/application.gitlab-ci.yml`. Het voegt jobs toe; het applicatievoorbeeld bepaalt `workflow`, `stages` en `needs`. Gebruik losse componenten voor een kleinere pipeline of een andere architectuur. Extra stappen zijn gewone jobs met `needs`; zie [uitbreidingen](modules.md#eigen-gedrag-toevoegen).

## Goedgekeurde standaardwaarden aanpassen

Het profiel koppelt elke image-input aan een afzonderlijke CI-variabele op groeps- of projectniveau, bijvoorbeeld `$MAVEN_BUILD_IMAGE`. Stel deze variabelen in op goedgekeurde images met een vaste digest, zoals beschreven bij [inrichting](setup.md). De koppelingen installeren geen images. Wil je een versiebeheerbare imagecatalogus voor de organisatie, zet dan de volledige goedgekeurde imagereferenties in het profiel en publiceer het profiel onder een vaste componentversie.

```yaml
include:
  - project: platform/ci-components
    ref: 1.0.0
    file: /examples/full-pipeline/profile.yml
    inputs:
      production-namespace: application-production
      test-url: https://$CI_PROJECT_ID-$CI_PIPELINE_ID.test.example.com
      production-url: https://application.example.com
      maven-directory: services/api
      npm-directory: web
      maven-build-image: registry.example.com/ci/maven@sha256:REPLACE_WITH_DIGEST
      artifact-expire-in: 30 days
      job-timeout: 45m
```

Deze instellingen gelden voor deze opname van het profiel. Elke image heeft een eigen input, ook de afzonderlijke Helm-images voor test en productie. Gewone jobs hebben standaard 30 minuten, Dependency-Check één uur en Fortify inclusief beleidscontrole twee uur. Pas langere jobs aan via `dependency-check-job-timeout` en `fortify-job-timeout`; zij nemen de gewone timeout niet over. De maximale timeout van GitLab Runner blijft de bovengrens. Artifacts worden standaard zeven dagen bewaard.

Inputs zijn alleen beschikbaar in het bestand dat ze declareert. Het profiel geeft waarden expliciet door aan de opgenomen modules; modules lezen het profiel niet zelf. Geneste `include:local`-bestanden worden opgezocht in het project en de commit van het profiel. Zie [GitLab-inputs](https://docs.gitlab.com/ci/inputs/) en [geneste includes](https://docs.gitlab.com/ci/yaml/includes/).

## Hooks en losse modules

Bij een losse module geef je `pre-hook`, `post-hook`, `cleanup-hook` en `hook-parameters-json` mee als componentinputs, zoals bij [een module uitbreiden](modules.md#kleine-aanvulling-binnen-een-component).

Bij het volledige profiel kun je deze hookvariabelen op de applicatiejob instellen, zonder de componentscripts te vervangen:

```yaml
maven-build:
  variables:
    MODULE_PRE_HOOK: ci/hooks/pre-build.sh
    MODULE_POST_HOOK: ci/hooks/post-build.sh
    MODULE_CLEANUP_HOOK: ci/hooks/cleanup.sh
    MODULE_HOOK_PARAMETERS_JSON: '{"label":"candidate"}'
```

Deze overrides gebruiken dezelfde [hookafspraken](modules.md#kleine-aanvulling-binnen-een-component) als losse modules. Jobinstellingen horen bij de vertrouwde applicatieconfiguratie; een profiel dwingt geen beveiligingsbeleid af tegenover iemand die de pipeline mag wijzigen.

Als later een standaardcomponent de implementatie vervangt, behoud dan de openbare input-, output- en hookafspraken in de adapter. Wijzig de componentkeuze in het organisatieprofiel; voeg daar geen build- of deploymentscripts aan toe.
