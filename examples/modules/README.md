# Losse modulevoorbeelden uitvoeren

Elk YAML-bestand in deze map neemt één actieve component op met de noodzakelijke instellingen. De implementatie staat in `templates/`. Gebruik het voorbeeld in een eigen pipeline of voer het rechtstreeks uit in ons testproject.

1. Open [CI samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new).
2. Selecteer `main` en kies bijvoorbeeld `module-sonar` bij `sample`.
3. Behoud de ingestelde `library_ref` en kies **New pipeline**.
4. Open de childpipeline om de modulejob en `verify-sample` te bekijken.

`all` test op de beschermde `main` alle vijftien modulevoorbeelden en de vier samengestelde pipelines. De testinrichting controleert dat de outputs bij dezelfde commit en pipeline horen en dat de verwachte rapporten, packages of releasegegevens bestaan. Een mislukte controle maakt de sample rood.

| Keuze | Wat wordt uitgevoerd? |
|---|---|
| `module-maven-build` | Maven-packages bouwen |
| `module-cucumber-test` | Backendtests die zelf de applicatie starten |
| `module-npm-build` | Angular-assets bouwen |
| `module-npm-test` | UI-unittests met een JUnit-rapport |
| `module-sonar` | Broncodeanalyse en quality gate in het eigen SonarQube-project `ci-samples` |
| `module-dependency-check` | Maven-dependencies controleren met OWASP Dependency-Check |
| `module-maven-publish` | Een unieke Maven-versie publiceren en teruglezen in het sampleproject |
| `module-jib-build` | Een backendimage bouwen en publiceren met Jib |
| `module-image-build` | UI-assets voorbereiden en een Nginx-image bouwen met BuildKit |
| `module-helm-publish` | Een OCI-Helm-chart publiceren |
| `module-helm-deploy` | Image en chart voorbereiden, deployen, health controleren en opruimen |
| `module-deployment-select` | Profielen kiezen en de werkelijk gegenereerde childpipeline uitvoeren |
| `module-release-reserve` | Een unieke releasetag reserveren in `ci-samples` |
| `module-release-check` | Een tag reserveren en controleren dat de release nog niet gepubliceerd is |
| `module-gitlab-release` | Een tag reserveren, image en chart publiceren en een GitLab-release met assetlinks aanmaken |

De Sonar- en releasevoorbeelden draaien alleen op de beschermde `main`. De gratis Sonar-editie ondersteunt geen afzonderlijke branchanalyse. De releasevoorbeelden gebruiken een deploy key die alleen het sampleproject kent; `main` staat geen directe pushes toe. De handmatige jobs uit de releasevoorbeelden worden uitsluitend in deze geïsoleerde testopstelling automatisch uitgevoerd. De parenttrigger houdt een GitLab-resourcegroep vast gedurende de volledige releasetest.

Publicatietests maken echte artifacts. Maven-packages en testreleases staan in `ci-samples`; images en charts in `docker-local/root-ci-samples/`. Tags en gepubliceerde versies blijven bewaard en worden niet hergebruikt. Helm-testreleases worden na afloop verwijderd. Er worden geen applicatiereleases of deployments van `hello-world` gewijzigd. Modules onder `modules/todo/` en het toekomstige profiel met nog niet ingerichte scanners zijn niet uitvoerbaar via deze lijst.

## Een voorbeeld opnemen in je eigen project

```yaml
include:
  - project: root/ci-components
    ref: &library '1.1.0'
    file: /examples/modules/sonar.yml
    inputs:
      library-ref: *library
```

Het voorbeeld bepaalt de stage en de component. Je eigen project levert de broncode, runner, tool-image en serververbinding. Het Sonar-voorbeeld verwacht `SONAR_IMAGE`, `SONAR_HOST_URL`, `SONAR_PROJECT_KEY` en een beperkt, gemaskeerd `SONAR_TOKEN`. De standaard Maven Wrapper is `./mvnw`.

Voor publicatievoorbeelden stel je de registry, bestemmingspaden, versie en toegangsgegevens in. De Helm-voorbeelden gebruiken de gedeelde `.helm-login`. `image-build` verwacht gebouwde UI-assets in `ui/dist/`; `helm-deploy` verwacht image- en chartoutputs van eerdere jobs. Geef die door met `needs`, zoals de [samengestelde voorbeelden](../samples/README.md) laten zien. `plain-http` staat standaard uit; onze lokale testomgeving zet die expliciet aan. Alle vereisten staan in de [modulehandleiding](../../docs/modules.md).

De bestanden onder `tests/samples/` leveren uitsluitend onze testvoorwaarden en assertions. Afnemers nemen die niet over. Het startformulier laadt de centrale [keuzelijst](../../tests/samples/options.yml) met GitLabs `spec:include` en geeft de keuze door aan de launcher. Een contracttest controleert dat de lijst, launcher en actieve voorbeelden overeenkomen. Dit gebruikt ondersteunde GitLab-functionaliteit; de indeling en isolatie zijn onze afspraken. Zie [GitLabs advies voor tests met samplebestanden](https://docs.gitlab.com/ci/components/#test-a-component-against-sample-files).
