# Jobs en pipelines uitbreiden

Gebruik GitLab-jobafhankelijkheden voor een extra pipelinestap. Gebruik de componenthooks voor kleine aanvullingen binnen één job. De Java-demo beheert deze definities in de centrale CI-bibliotheek; de applicatierepository heeft daarvoor geen CI-scripts nodig.

## Extra stap: een gewone GitLab-job

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

## Kleine aanvulling binnen een component

De volgende optionele inputs zijn een afspraak van onze bibliotheek boven op GitLabs joblifecycle:

| Componentinput | Uitvoering | Gevolg bij fouten |
|---|---|---|
| `pre-hook` | In `before_script`, na de gedeelde voorbereiding | De job faalt |
| `post-hook` | Aan het einde van `script`, vóór publicatie van outputs | De job faalt |
| `cleanup-hook` | In `after_script`, in een nieuwe shell | Opruimen naar beste vermogen; maakt een geslaagde job niet alsnog rood |

Verplichte controles horen in `script` of in een eigen verplichte job. `after_script` is bedoeld voor opruimen. Elke component verwijst voor deze fasen naar [shared/module.yml](../shared/module.yml). De opmerkingen in dat bestand leggen de YAML-referenties uit. Zie [GitLabs jobuitvoering](https://docs.gitlab.com/ci/jobs/job_execution/).

Hookpaden zijn relatief aan de repository van de afnemer. Hooks worden met `sh` uitgevoerd vanuit de werkmap van de component. Ze draaien als subprocessen; geef resultaten terug via bestanden. De inhoud van `hook-parameters-json` komt in `CI_MODULE_PARAMETERS_FILE`. Extra outputs schrijf je naar `CI_MODULE_EXTRA_OUTPUTS`, met de componentprefix gevolgd door `_CUSTOM_`. Zet geen geheimen in hooks of outputs. Er zijn voorbeelden voor [vóór de build](../examples/hooks/pre-build.sh), [na de build](../examples/hooks/post-build.sh) en [opruimen](../examples/hooks/cleanup.sh).

## Migreren vanaf de verwijderde callbackcomponent

Vervang de oude vervolgcomponent door een gewone job:

1. Plaats de benodigde bewerking in `script` en gebruik de bijbehorende tool-image.
2. Lees waarden uit eerdere jobs via dotenv-artifacts en verwijder de aanroep van de vervolghelper.
3. Publiceer gewijzigde waarden of bestanden als gewone artifacts.
4. Maak de volgende job afhankelijk van deze job en van eventuele eerdere jobs waarvan de bestanden nog nodig zijn.

GitLab plant de uitvoering; er is geen vervangende callbackhelper. Dotenv-waarden uit een draaiende job kunnen de bestaande jobstructuur niet aanpassen. Selecteer jobs met pipeline-inputs en `rules`, of gebruik een childpipeline wanneer de configuratie pas tijdens de uitvoering kan worden bepaald.
