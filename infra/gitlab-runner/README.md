# Lokale GitLab Runner

De lokale runner-manager bedient de projecten `root/hello-world`, `root/ci-components`, `root/ci-pipelines` en `root/ci-samples` via afzonderlijke runnerregistraties. Jobs met `local-docker` gebruiken maximaal twee CPU's en 2 GiB geheugen en draaien niet privileged. De gedeelde manager voert met `concurrent = 2` maximaal twee jobs tegelijk uit, verdeeld over alle zes registraties. De installer bewaart deze instelling. GitLabs afhankelijkheden en resourcegroepen kunnen jobs alsnog laten wachten. De manager gebruikt de Docker-socket om jobcontainers te maken; jobs krijgen die socket niet.

Start of stop de runner vanuit `ci`:

```sh
docker compose -f infra/gitlab-runner/compose.yml up -d runner
docker compose -f infra/gitlab-runner/compose.yml stop runner
```

Jobcontainers gebruiken Docker Desktops netwerk `kind` om de Kubernetes-API op `desktop-control-plane:6443` te bereiken. GitLab en Artifactory zijn bereikbaar via `host.docker.internal`. De runner past de Git-clone-URL aan, omdat `localhost` binnen een job naar de job zelf verwijst.

CI- en helperimages gebruiken manifestdigests voor de automatisch gekozen architectuur (`amd64` of `arm64`) uit `../artifactory/ci-images.json`. De pullpolicy `always` controleert iedere image bij Artifactory en hergebruikt gedownloade lagen. Als `../artifactory/docker-hub.json` bestaat, kiest `configure.py` de virtuele repository `docker`. Die levert onze eigen artifacts en haalt aangevraagde Docker Hub-images zo nodig op in de remote cache. De Docker-client slaat Artifactory niet over als een image ontbreekt. Verzoeken aan `docker-local` bereiken alleen expliciet gepubliceerde artifacts.

`kubernetes.yaml` definieert een deployment-serviceaccount, een rol beperkt tot de namespace en een blijvend token-Secret voor deze lokale omgeving. Het account kan geen andere namespaces beheren. Maak voor tokenrotatie `gitlab-deployer-token` opnieuw aan en werk `LOCAL_KUBECONFIG` bij. Na het opnieuw maken van het cluster herstelt `./infra/setup.sh install` de namespace, registrytoegang en kubeconfig.

`configure.py` registreert de runner en stelt projectvariabelen in met het provisioningtoken uit `../gitlab-ce/secrets`. Dit is infrastructuurbeheer, geen onderdeel van de applicatiebuild. Houd de gegenereerde map `secrets/` privé; Git negeert die. Commit geen runnertoken, registry-credentials of kubeconfig.

Na inrichting gebruikt de runner zijn eigen authenticatietoken. Maven-publicatie gebruikt `CI_JOB_TOKEN`. Gewone pipelines hebben het provisioningtoken niet nodig.

Maven-packages staan in GitLab Package Registry, dat zo nodig ook npm ondersteunt. Testrapporten zijn GitLab-jobartifacts. Containerimages en OCI-Helm-charts staan in lokale Artifactory JCR. Dit gebruikt gratis edities en maakt geen verbinding met de Artifactory van de organisatie.

## Runner voor het componentproject

`root/ci-components` heeft een eigen projectrunnerregistratie. De registraties delen de lokale manager en parallelismelimiet. `configure.py` behoudt de applicatie- en componentregistraties als `components-project.json` en `validation-image.json` bestaan. De componentvalidatie krijgt de Python/Ruby/Git-image en registry-lees-/cachecredentials. Publicatie- en Kubernetes-credentials worden per afnemend project beheerd. De validatie-image wordt gebouwd vanuit `validation-image/Dockerfile`, gepubliceerd naar Artifactory en met digest vastgelegd in `validation-image.json`. De samplecontroles gebruiken dezelfde validatie-image met Git en curl om gepubliceerde tags en release-assets te controleren.

## Images voor Angular en browsertests

`./infra/setup.sh install` spiegelt naast Java/Helm ook Node 24 LTS, Nginx zonder rootrechten, rootless BuildKit en de browserimage. `configure.py` stelt `NODE_CI_IMAGE`, `BUILDKIT_CI_IMAGE`, `NGINX_RUNTIME_IMAGE` en `BROWSER_CI_IMAGE` in op manifestdigests. De browser-Dockerfile zet Playwright vast op 1.62.0 en neemt de bestaande Java 25-/Maven-toolchain over. Werk de image en de Playwright-dependency van de sample samen bij.

Een aparte runner met tag `local-buildkit` gebruikt `buildkit/seccomp.json`. Dit is gebaseerd op Moby's standaardprofiel, aangevuld met `clone`, `unshare`, `setns`, `mount` en `umount2` voor rootless BuildKit. De runner blijft niet-privileged. `local-docker` houdt Dockers gewone seccomp-profiel. Jobs krijgen geen Docker-socketmount. Beoordeel deze hostgebonden inrichting opnieuw vóór gebruik elders. Helper-/toolimages en de scope van releasecredentials blijven afzonderlijk beheerd.

Het REST-retry-endpoint van GitLab 19.3 gebruikt `inputs: {cluster: ..., user_config: ...}`. Het play-endpoint gebruikt `job_inputs`. Gebruik van dat laatste veld bij retry behoudt stilzwijgend de oude waarden. Kies in de interface **Retry with modified values** en start daarna de deploymenttrigger opnieuw. Zie de gedeelde handleiding voor pipelinekeuzes.

## Validatie met uitvoerbare samples

Het project `root/ci-samples` gebruikt de gewone en BuildKit-runnerregistraties voor echte modulevoorbeelden. `configure-samples.py` richt de testresources in. De namespace `ci-samples`, het eigen serviceaccount en de registry-schrijfrechten onder `docker-local/root-ci-samples/` scheiden de tests van de normale applicatie. De releasevoorbeelden gebruiken een eigen deploy key voor beschermde tags in uitsluitend `ci-samples`. Sonar schrijft naar een eigen SonarQube-project. Deze credentials zijn alleen beschikbaar op de beschermde `main`.

Op **New pipeline** zijn vier samengestelde pipelines en vijftien losse modulevoorbeelden beschikbaar. `all` voert op `main` alle negentien uit; in een merge request draaien de vijftien voorbeelden zonder beschermde Sonar- of releasecredentials. Publicatievoorbeelden maken echte artifacts met unieke versies. De Maven- en Sonar-images voor dit project bevatten `unzip`, zodat de Maven Wrapper zijn ZIP-distributie met de vastgelegde checksum kan controleren.

`CI_SAMPLES_PROJECT=root/ci-samples` koppelt de componentbibliotheek aan dit project. GitLabs trigger geeft de exacte bibliotheekcommit als input door en neemt met `strategy: mirror` het resultaat over. Een resourcegroep houdt deployment, tests en cleanup bij elkaar. De samplepoort voor de API is 8180 en die voor de UI 8190.

De bestanden onder `tests/samples/` staan in `ci-components`; de testapplicatie en het startformulier staan in `ci-samples`. De [samplehandleiding](https://github.com/woozer/ci-components/blob/main/examples/samples/README.md) beschrijft de indeling en het starten via **New pipeline**.
