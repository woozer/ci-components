# Uitvoerbare CI-samples

Open [New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new), selecteer `main`, kies `sample` en klik op **New pipeline**. Met `all` voer je alle negentien voorbeelden op de beschermde `main` uit. Gebruik bij `library_ref` standaard de uitgebrachte componentversie `1.0.0`, kies een andere volledige versie of geef een volledige commit-SHA op om een kandidaatwijziging te testen. De [versieafspraken](http://localhost:8929/root/ci-components/-/blob/main/docs/component-versions.md) gelden voor alle opgenomen bestanden.

Kies een van de vier pipelinevoorbeelden of een van de vijftien losse modules, zoals `module-sonar`, `module-dependency-check` of `module-npm-test`. Sonar en de drie releasevoorbeelden vereisen de beschermde `main`; `all` in een merge request voert de overige vijftien voorbeelden uit.

De pipelines gebruiken rechtstreeks de [voorbeeld-YAML voor afnemers](http://localhost:8929/root/ci-components/-/tree/main/examples/samples). De validatie voegt alleen lokale testinstellingen, controles en cleanup toe. Modulewijzigingen starten dit project automatisch met de gewijzigde component-SHA.

De testapplicatie is gebaseerd op [hello-world-commit 78bc471e](http://localhost:8929/root/hello-world/-/tree/78bc471e275b9ccbc03c9962b5bc2bb69c8bbe2e). De normale hello-world-repository en pipeline staan hier los van. Werk de testapplicatie bij via een merge request; de documentatie kan afzonderlijk worden onderhouden.

De testkopie gebruikt daarnaast dezelfde Tomcat-beveiligingsupdate naar 11.0.25 als `hello-world`. `environment/cluster/test.yaml` levert de routing voor het losse Helm-voorbeeld. `deploy.yml` controleert de gekozen profielen wanneer het voorbeeld `deployment-select` een childpipeline start.

Build- en testartifacts blijven in GitLab. Sample-images en -charts gaan naar `docker-local/root-ci-samples/`. Deployments gebruiken namespace `ci-samples`, API-poort 8180 en UI-poort 8190. De parenttrigger houdt een lock vast tijdens deployment, tests en cleanup. Cleanup verwijdert de tijdelijke Helm-releases. Na annulering kan het nodig zijn de cleanup-job handmatig opnieuw te starten.

## Waar staan de pipelines?

De `.gitlab-ci.yml` in dit project laadt de centrale keuzelijst uit `tests/samples/options.yml` met `spec:include` en neemt `tests/samples/launcher.yml` op uit **ci-components**. De launcher handelt de samplekeuze af en start de gekozen voorbeelden als childpipelines.

- [`examples/modules/`](http://localhost:8929/root/ci-components/-/tree/main/examples/modules) bevat een uitvoerbaar voorbeeld per actieve module.
- [`examples/samples/`](http://localhost:8929/root/ci-components/-/tree/main/examples/samples) bevat de pipelines die afnemers kunnen overnemen.
- [`tests/samples/`](http://localhost:8929/root/ci-components/-/tree/main/tests/samples) bevat onze launcher, testinstellingen, outputcontroles en cleanup.

De launcher staat onder `tests/` omdat hij de validatie organiseert. Deze mappenindeling is onze keuze; GitLab schrijft die niet voor. `include:inputs` geeft instellingen door aan opgenomen YAML. Keuzes op **New pipeline** komen uit `spec:inputs` van de hoofdconfiguratie.

Lees de [modulehandleiding](http://localhost:8929/root/ci-components/-/blob/main/docs/modules.md) en [handleiding voor de samples](http://localhost:8929/root/ci-components/-/blob/main/examples/samples/README.md).

## Publicatie- en releasetests

De tests publiceren echte Maven-packages, images en charts met unieke versies. De releasevoorbeelden reserveren tags en maken GitLab-releases uitsluitend in dit project. Ze gebruiken een eigen deploy key zonder pushrechten op `main`. De artifacts blijven beschikbaar voor controle; versies en tags worden niet hergebruikt. De Sonar-sample schrijft naar het afzonderlijke SonarQube-project `ci-samples`.

Het volledige overzicht staat in de [handleiding voor losse modulevoorbeelden](http://localhost:8929/root/ci-components/-/blob/main/examples/modules/README.md).
