# Lokale GitLab Community Edition

Gebruik voor de volledige demo `./infra/setup.sh install` vanuit de hoofdmap; zie de [installatiehandleiding](../../installation.md). De beheercommando's hieronder voer je vanuit deze map uit. Het Compose-bestand start GitLab CE 19.3.2 met Dockers automatische architectuurkeuze. Configuratie, logs en gegevens staan in blijvende benoemde volumes.

```sh
docker compose up -d
docker compose ps
```

Open <http://localhost:8929>. De eerste beheerdersnaam is `root`. Haal het initiële wachtwoord lokaal op:

```sh
docker compose exec gitlab cat /etc/gitlab/initial_root_password
```

GitLab verwijdert het initiële wachtwoordbestand na de beschikbaarheidsperiode. Wijzig het wachtwoord na de eerste login. Bij het inrichten kan ook een kopie in de private, door Git genegeerde map `secrets/` zijn opgeslagen. Commit nooit toegangsgegevens.

Git via SSH is bereikbaar op `localhost:2424`. Beide gepubliceerde poorten luisteren alleen op de loopbackinterface van deze machine. HTTP is bedoeld voor deze lokale ontwikkelomgeving. Gebruik een echte hostnaam, HTTPS en toegangsbeheer voordat je GitLab via een netwerk bereikbaar maakt.

De container heeft maximaal vier CPU's en 8 GiB RAM. Monitoring is uitgeschakeld; Puma- en Sidekiq-parallelisme is beperkt voor lokaal gebruik. Eerste configuratie en migraties kunnen enkele minuten duren.

```sh
# Stop the service; named volumes retain GitLab data.
docker compose stop

# Start it again.
docker compose up -d

# View startup diagnostics.
docker compose logs --tail=100 gitlab
```

`docker compose down --volumes` verwijdert de gegevens van deze instance. Gebruik dit alleen als je die bewust wilt wissen. Volg vóór een versie-upgrade [GitLabs upgradeprocedure voor Docker](https://docs.gitlab.com/update/docker/). Bewaar vooraf een back-up van de gegevens en `gitlab-secrets.json` buiten Docker, laat lopende CI-jobs afronden en pauzeer de runners. Werk daarna de expliciete imageversie in Compose bij en controleer na de upgrade de gezondheid van GitLab en een CI-pipeline. Versie 19.3.2 bevat [kritieke beveiligingscorrecties](https://docs.gitlab.com/releases/patches/patch-release-gitlab-19-3-2-released/).

Dit installeert de GitLab-server. CI-jobs vereisen daarnaast een ingestelde GitLab Runner. Runnercontainers hebben een hostnaam/URL nodig die de server vanuit hun eigen netwerk bereikt. Hun `localhost` verwijst naar de runnercontainer zelf.

Bronnen: [GitLab via Docker installeren](https://docs.gitlab.com/install/docker/installation/) en [officiële CE-image](https://hub.docker.com/r/gitlab/gitlab-ce/tags/).
