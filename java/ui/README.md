# UI voor het dierenoverzicht

Angular 22, gebouwd met de officiële Angular CLI. Gebruik een ondersteunde Node-versie uit `package.json`; CI gebruikt Node 24 LTS. De exacte dependencies staan in `package-lock.json`.

```sh
npm ci
npm start
```

Open http://localhost:4200. De ontwikkelproxy stuurt `/api/` door naar de backend op http://localhost:8080. Start die vanuit de repositoryroot met `./mvnw -pl hello-app spring-boot:run`.

```sh
npm run build
npm run test:ci
docker build -t hello-world-ui:local .
```

Nginx serveert `dist/animals-ui/browser` en stuurt `/api/` door naar `BACKEND_URL`, standaard `http://hello-world:8080`. Nginx luistert op poort 8080; de Compose-service of Helm-chart `hello-world-ui` maakt de UI bereikbaar op poort 8090. De container draait zonder rootrechten, met een alleen-lezen rootbestandssysteem en schrijfbare `/tmp`.

Unittests controleren de tabel, verversen, blokkeren tijdens laden, API-fouten en lege resultaten. De Maven-module `integration-tests` bevat de Cucumber-/Playwright-browsertests. Het commando met `-Pui` staat in de [README van de repository](../README.md).
