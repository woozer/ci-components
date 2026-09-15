# Losse modulevoorbeelden

Elk YAML-bestand in deze map neemt één actieve component op. Doel, projectvoorwaarden, inputs en outputs staan per module in de [modulehandleiding](../../docs/modules.md#actief-een-module-kiezen).

Gebruik een voorbeeld in je eigen pipeline of voer het uit in **CI samples** met de keuze `module-<module-name>`. De [samplehandleiding](../samples/README.md#starten-in-gitlab) beschrijft de bediening, toegangsvoorwaarden, testisolatie en controles voor alle voorbeelden.

## Een voorbeeld opnemen in je eigen project

```yaml
include:
  - project: root/ci-components
    ref: &library '1.0.0'
    file: /examples/modules/sonar.yml
    inputs:
      library-ref: *library
```

Het opgenomen voorbeeld bepaalt de stage en component. Je project levert de broncode, runner, tool-image en verbindingen. Het Sonar-voorbeeld gebruikt bijvoorbeeld `SONAR_IMAGE`, `SONAR_HOST_URL`, `SONAR_PROJECT_KEY` en `SONAR_TOKEN`; de gekozen image moet de Maven Wrapper kunnen uitvoeren.

Voor publicatievoorbeelden configureer je ook bestemming, versie en credentials. `maven-publish` gebruikt in het voorbeeld `MAVEN_PUBLISH_URL` en `MAVEN_SETTINGS_FILE`; `repository-id` moet passen bij de server-id in dat bestand. De Helm-voorbeelden gebruiken de gedeelde `.helm-login`. De Dockerfile van het UI-voorbeeld verwacht assets in `ui/dist/`; de [samengestelde samples](../samples/README.md) tonen hoe je producerende jobs met `needs` verbindt.

De aanvullende voorbereiding en assertions onder `tests/samples/` horen bij onze testopstelling. Afnemers nemen die bestanden niet over.
