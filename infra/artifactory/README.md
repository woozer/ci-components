# Lokale Artifactory-containerregistry

Deze testomgeving gebruikt JFrog Container Registry (JCR) 7.161.15, de gratis Artifactory-editie voor Docker/OCI en Helm. PostgreSQL en benoemde volumes bewaren de gegevens. Het is een aparte lokale instance met eigen toegangsgegevens. Er wordt geen Artifactory-endpoint van de organisatie gebruikt.

JCR ondersteunt Docker/OCI-images en Helm-charts. Maven-packages staan in de lokale GitLab Package Registry, die zo nodig ook npm-packages ondersteunt. GitLab-jobartifacts bewaren testrapporten. Zo blijft de omgeving op gratis edities. JCR biedt geen eigen Maven- of npm-repositories. Zie [JFrog-edities](https://docs.jfrog.com/artifactory/docs/jfrog-container-registry) en [GitLab Package Registry](https://docs.gitlab.com/user/packages/package_registry/).

## Starten en initialiseren

Gebruik vanuit de hoofdmap `./infra/setup.sh install`. De [installatiehandleiding](../../installation.md) beschrijft de Docker-instellingen, licentieacceptatie en herinstallatie. Python draait in de installercontainer.

De bootstrap wijzigt het initiële beheerderswachtwoord en maakt `docker-local` plus twee accounts aan: `local-builder` voor publicatie en `local-reader` voor ophalen. Toegangsgegevens staan in de private, door Git genegeerde map `secrets/`. Opnieuw uitvoeren hergebruikt de opgeslagen wachtwoorden.

JCR beperkt de openbare REST API voor repositorybeheer. Deze lokale installer gebruikt daarom de geauthenticeerde beheerendpoints van de meegeleverde JCR-interface. Dat is versiegebonden maatwerk: controleer de installer bij een JCR-upgrade. De Compose-image staat vast op versie 7.161.15. Bestaande repositories worden behouden.

- Webinterface: <http://localhost:8082>.
- Beheerder: `admin`; wachtwoord in `secrets/credentials.json`.
- Registry-imagepad: `localhost:8082/docker-local/hello-world`.
- Jib-toegangsgegevens: `secrets/maven-settings.xml`.

### De JCR-overeenkomst accepteren

De eerste-startwizard bevat de EULA. Scroll binnen het overeenkomstpaneel helemaal naar beneden om het selectievakje te activeren, ga akkoord en ga verder. De statusbalk over een niet-ondertekende EULA is niet de knop om te accepteren. Zie [eerste JCR-inrichting](https://docs.jfrog.com/artifactory/docs/get-started-jfrog-container-registry).

Als de wizard niet beschikbaar is, voer dan vanuit deze map uit:

```sh
python3 accept-eula.py
```

Dit haalt de overeenkomst op bij de lokale instance en opent `eula.html` in de browser. Typ interactief `ACCEPT` om akkoord te sturen; Enter annuleert. De helper gebruikt het acceptatie-endpoint van de geïnstalleerde JCR-interface en leest de opgeslagen beheerderscredentials zonder ze te tonen. `--view-only` downloadt alleen de overeenkomst. De bootstrap accepteert de EULA nooit automatisch.

Kun je de terminalprompt niet bedienen, gebruik dan `python3 accept-eula.py --browser`. Dit opent een lokale beoordelingspagina met een selectievakje en de knop **Accept EULA in Artifactory**. De knop stuurt het akkoord naar de draaiende JCR-instance. De helper luistert alleen op loopback, houdt beheerderscredentials buiten de browser en stopt na een geslaagde indiening.

Poorten 8081 en 8082 luisteren op de loopbackinterface van de host. Artifactory heeft maximaal 6 GiB geheugen, met een Java-heap van 2 GiB; PostgreSQL maximaal 512 MiB. GitLab en Kubernetes delen de Docker Desktop-resources. Deze inrichting is bedoeld als kleine ontwikkelomgeving.

Compose schakelt JFConnect uit, omdat die dienst ontbreekt in deze JCR-image. Met JFConnect ingeschakeld bleven UI-logins wachten op rechtenverzoeken aan de ontbrekende dienst. Zie [JFrog-probleem met de gratis editie](https://github.com/jfrog/charts/issues/2233).

Een Nginx-gateway bedient poort 8082 en stuurt HTTP door naar de JFrog-router. Dit voorkomt diens TLS-antwoord `unrecognized name`, waardoor deze Docker-versie niet terugviel op HTTP ondanks een insecure-registry-instelling. De gateway behoudt de oorspronkelijke host voor registry-authenticatie en stuurt image-uploads zonder buffering door. De gatewayimage is vastgezet op digest. Zie [Docker TLS-terugval](https://github.com/moby/moby/issues/51771).

## CI-images in JCR opslaan

### Automatisch ophalen uit Docker Hub

Voer na de bootstrap `python3 configure-docker-hub.py` uit. Het script maakt repositories aan via JCR's geauthenticeerde UI-beheer-API en kan opnieuw draaien zonder ze te dupliceren.

- `docker-local`: onze gepubliceerde images en OCI-charts.
- `docker-hub-remote`: een online cache van `https://registry-1.docker.io/`, met tokenauthenticatie.
- `docker`: een virtueel endpoint met eerst de lokale repository en daarna Docker Hub remote. De standaard publicatierepository is `docker-local`.

Log in met je lokale Artifactory-account en gebruik het virtuele endpoint voor ophalen:

```sh
docker login localhost:8082
docker pull localhost:8082/docker/library/hello-world:latest
docker pull localhost:8082/docker/library/maven:3.9.12-eclipse-temurin-25
```

Het eerste verzoek om een ontbrekende Docker Hub-image haalt die op naar `docker-hub-remote-cache`. Latere verzoeken hergebruiken de inhoud. Tagmetadata wordt vernieuwd volgens Artifactory's cachebeleid. Officiële Docker Hub-images gebruiken de namespace `library/`. Andere images behouden hun eigenaar, bijvoorbeeld `docker/alpine/helm`. Verzoeken aan `docker-local` zoeken alleen lokale artifacts. Een onverkort `docker pull maven` gaat nog steeds rechtstreeks naar Docker Hub.

De bestaande CI-accounts hebben Read en Deploy/Cache op de remote repository; dat is nodig om een lege cache te vullen. Publicatierechten op de lokale repository worden apart beheerd. Deze omgeving haalt publieke Docker Hub-images upstream anoniem op; de toepasselijke Docker Hub-limieten blijven gelden. Zie [Docker-repositories](https://docs.jfrog.com/artifactory/docs/docker-repositories) en [remote-cacherechten](https://docs.jfrog.com/administration/docs/permissions).

Zodra `docker-hub.json` bestaat, gebruikt de runner het virtuele endpoint voor de bestaande vaste CI-images. Applicatiepublicatie blijft naar `docker-local` gaan.

### Docker-transport en bestaande mirrors

Docker Desktop moet HTTP toestaan voor deze lokale registry. Voeg in **Settings → Docker Engine** deze vermeldingen toe aan de bestaande JSON-configuratie en pas de wijziging toe:

```json
{
  "insecure-registries": ["localhost:8082", "host.docker.internal:8082"]
}
```

Behoud de andere instellingen. Bewerk je `~/.docker/daemon.json` rechtstreeks, stop Docker Desktop dan eerst en start het daarna opnieuw. Een wijziging terwijl Docker Desktop draait, kan door gecachete instellingen worden overschreven. Controleer met `docker info --format '{{json .RegistryConfig.IndexConfigs}}'` dat beide registrynamen `Secure: false` hebben. Zie [Docker Desktop-engine-instellingen](https://docs.docker.com/desktop/settings-and-maintenance/settings/).

`./infra/setup.sh install` haalt de basisimages op, bouwt de aanvullende toolimages en publiceert ze naar Artifactory. De installer kiest automatisch `amd64` of `arm64`, inclusief de passende runner-helper, en schrijft manifestdigests naar `ci-images.json`. Dezelfde ingang werkt bij een nieuwe installatie en bij het bijwerken van de lokale toolimages.

Applicatie-images en OCI-Helm-charts worden door de pipeline gepubliceerd. Images voor het opstarten van GitLab en Artifactory komen rechtstreeks uit de registries van leveranciers; SonarQube wordt na inrichting via de lokale Artifactory gestart.

## De Jib-image van de applicatie publiceren

Voer vanuit `ci/java` uit:

```sh
./mvnw --settings ../infra/artifactory/secrets/maven-settings.xml \
  -pl hello-app compile jib:build \
  -Djib.to.image=localhost:8082/docker-local/hello-world:local \
  -Djib.allowInsecureRegistries=true \
  -DsendCredentialsOverHttp=true
```

De HTTP-opties zijn expliciet voor deze lokale omgeving. Laat ze uit bij een HTTPS-registry. De bestemming is een buildparameter; toegangsgegevens blijven in het private Maven-settingsbestand. Zie [Jib-authenticatie en HTTP](https://github.com/GoogleContainerTools/jib/blob/master/docs/faq.md).

Kubernetes-nodes hebben hun eigen netwerk en imageruntime. Hun `localhost` verwijst niet naar deze Mac. Deployment vanuit deze registry vereist een adres dat vanaf de node bereikbaar is, credentials in een image-pull-secret en passende transport-/vertrouwensinstellingen. Het eerste Docker Desktop-Helm-voorbeeld gebruikt de lokaal gebouwde Jib-image.

## Stoppen en herstarten

```sh
docker compose stop
docker compose up -d
docker compose logs --tail=100 artifactory
```

Bewaar `.env`, de private beheerderscredentials en de benoemde volumes bij elkaar. `docker compose down --volumes` verwijdert de database en artifacts van deze omgeving. Volg vóór een versiewijziging Artifactory's back-up- en upgradeprocedures.

Bron: [JFrog via Docker installeren](https://docs.jfrog.com/installation/docs/docker).
