# Lokale SonarQube Community Build

Deze inrichting draait SonarQube Community Build 26.9.0.129388 met een eigen PostgreSQL-database. Beide images komen via de lokale Artifactory-proxy en worden in `.env` vastgezet op digest. De webinterface is bereikbaar op [localhost:9000](http://localhost:9000).

Gebruik vanuit de hoofdmap `./infra/setup.sh install`; zie de [installatiehandleiding](../../installation.md). De installer bouwt de scanimage, start SonarQube en maakt de projecten `hello-world` en `ci-samples`, een beperkt CI-account en projectgebonden analysetokens aan. De tokens worden automatisch als beschermde GitLab-variabelen opgeslagen. Er is geen extern account of handmatige API-key nodig.

De gebruikersnaam voor lokaal beheer is `admin`; het automatisch aangemaakte wachtwoord staat alleen in `secrets/credentials.json`. Commit `.env` en `secrets/` niet.

De dienst gebruikt poort 9000 en het bestaande Docker-netwerk `kind` voor toegang vanuit de runner. PostgreSQL staat alleen op het eigen Compose-netwerk. Named volumes bewaren de database en SonarQube-gegevens. De geheugenlimiet is 4 GB voor SonarQube en 512 MB voor PostgreSQL; houd daarnaast ruimte voor GitLab, Artifactory, Kubernetes en CI-jobs. Docker Desktop heeft in deze demo 16 GB geheugen op een Mac met 32 GB RAM. Met 12 GB ontstond zware swapdruk en startte de JavaScript-analyser niet binnen zijn timeout.

De gedeelde Maven-scanimage voor Sonar en Dependency-Check bevat Maven 3.9.12, Java 25, Node.js 24 en Python 3. De installer neemt de centrale helpers `sonar_report.py`, `dependency_report.py` en `report_api.py` op onder `/opt/ci/`, publiceert de image in Artifactory en stelt `SONAR_CI_IMAGE` automatisch in. De organisatieconfiguratie gebruikt diezelfde image voor `DEPENDENCY_CHECK_IMAGE`. De buildcontext is de repositoryhoofdmap; de `.dockerignore` laat alleen de Dockerfile en de drie helpers toe.

De installer maakt per project ook een Sonar-account met leesrechten en een GitLab project access token met de rol Reporter en scope `api`. `SONAR_REPORT_TOKEN` en `GITLAB_REPORT_TOKEN` zijn gemaskeerd en beschermd. Hiermee plaatst de helper een samenvatting bij de geanalyseerde commit; het is geen MR-analyse. De lokale bestanden staan onder `secrets/` als `<project>-report-account.json`, `<project>-report-token` en `<project>-gitlab-report-token.json`. Het GitLab-token verloopt na maximaal één jaar. Trek het oude token bij rotatie in, verwijder het bijbehorende lokale tokenbestand en voer de inrichting opnieuw uit. Zie ook [alle gegenereerde geheimen](../../installation.md#waar-staan-de-gegenereerde-geheimen).

Na analyse van main koppelt de Sonar-helper het resultaat ook aan de juiste gemergede MR. Voor Dependency-Check maakt de installer een afzonderlijk `<project>-gitlab-mr-report-token.json` aan. Dit Reporter-token komt als gemaskeerde maar niet-beschermde `GITLAB_MR_REPORT_TOKEN` beschikbaar voor de vertrouwde MR-branches in deze demo. Dezelfde verval- en rotatieafspraken gelden. Zie [de rapportagevoorwaarden](../../docs/modules.md#dependency-check).

De inrichting volgt het [officiële Compose-patroon](https://docs.sonarsource.com/sonarqube-community-build/server-installation/from-docker-image/set-up-and-start-container). HTTP op het lokale Docker-netwerk is een demo-keuze; een organisatie-inrichting gebruikt TLS en beheerde toegangsgegevens.

Test de scanners via [ci-samples → New pipeline](http://localhost:8929/root/ci-samples/-/pipelines/new). Kies `module-sonar` of `module-dependency-check`. Deze uitvoerbare voorbeelden gebruiken de echte scanner, runner, configuratie en artifacts. Er is geen aparte lokale checkout of scannerhelper nodig. Zie de [scanhandleiding](../../docs/scanners.md).
