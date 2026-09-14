# Lokale SonarQube Community Build

Deze inrichting draait SonarQube Community Build 26.9.0.129388 met een eigen PostgreSQL-database. Beide images komen via de lokale Artifactory-proxy en worden in `.env` vastgezet op digest. De webinterface is bereikbaar op [localhost:9000](http://localhost:9000).

Gebruik vanuit de hoofdmap `./infra/setup.sh install`; zie de [installatiehandleiding](../../installation.md). De installer bouwt de scanimage, start SonarQube en maakt de projecten `hello-world` en `ci-samples`, een beperkt CI-account en projectgebonden analysetokens aan. De tokens worden automatisch als beschermde GitLab-variabelen opgeslagen. Er is geen extern account of handmatige API-key nodig.

De gebruikersnaam voor lokaal beheer is `admin`; het automatisch aangemaakte wachtwoord staat alleen in `secrets/credentials.json`. Commit `.env` en `secrets/` niet.

De dienst gebruikt poort 9000 en het bestaande Docker-netwerk `kind` voor toegang vanuit de runner. PostgreSQL staat alleen op het eigen Compose-netwerk. Named volumes bewaren de database en SonarQube-gegevens. De geheugenlimiet is 4 GB voor SonarQube en 512 MB voor PostgreSQL; houd daarnaast ruimte voor GitLab, Artifactory, Kubernetes en CI-jobs. Docker Desktop heeft in deze demo 16 GB geheugen op een Mac met 32 GB RAM. Met 12 GB ontstond zware swapdruk en startte de JavaScript-analyser niet binnen zijn timeout.

De scanimage bevat Maven 3.9.12, Java 25 en Node.js 24 uit de al vastgelegde Artifactory-images. De installer publiceert deze image in Artifactory en stelt `SONAR_CI_IMAGE` automatisch in. De buildcontext bevat alleen de Dockerfile.

De inrichting volgt het [officiële Compose-patroon](https://docs.sonarsource.com/sonarqube-community-build/server-installation/from-docker-image/set-up-and-start-container). HTTP op het lokale Docker-netwerk is een demo-keuze; een organisatie-inrichting gebruikt TLS en beheerde toegangsgegevens.

Test de scanners via [ci-samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new). Kies `module-sonar` of `module-dependency-check`. Deze uitvoerbare voorbeelden gebruiken de echte scanner, runner, configuratie en artifacts. Er is geen aparte lokale checkout of scannerhelper nodig. Zie de [scanhandleiding](../../docs/scanners.md).
