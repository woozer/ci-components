# Inputs: verplicht of optioneel?

Geef instellingen mee via `include:inputs`. De `MODULE_*`-variabelen binnen een component verbinden deze inputs met de scripts. Afnemers hoeven die interne variabelen niet zelf in te stellen.

In `spec:inputs` van elke module staat wat je moet invullen:

- **Zonder `default`: verplicht.** GitLab weigert de pipeline als de input ontbreekt.
- **Met `default`: optioneel.** Vul de input alleen in als je van de standaardwaarde wilt afwijken.
- Bij uitvoering kunnen daarnaast bestanden, variabelen en toegangsgegevens nodig zijn. Die voorwaarden staan hieronder.

Elke module vereist `image`. Voor de dertien actieve modules gelden daarnaast de volgende verplichte inputs:

| Module | Aanvullende verplichte inputs |
|---|---|
| [maven-build](../templates/maven-build.yml) | Geen |
| [cucumber-test](../templates/cucumber-test.yml) | Geen; zie hieronder de voorwaarde voor de doel-URL |
| [maven-publish](../templates/maven-publish.yml) | `settings-file`, `repository-url` |
| [jib-build](../templates/jib-build.yml) | `project-selector`, `settings-file`, `image-repository`, `base-image` |
| [helm-publish](../templates/helm-publish.yml) | `chart`, `chart-name`, `chart-version`, `oci-repository` |
| [helm-deploy](../templates/helm-deploy.yml) | `image-ref-variable`, `values-file`, `release`, `namespace`, `environment`, `target-url` |
| [npm-build](../templates/npm-build.yml) | Geen; de repository moet een lockfile en buildscript bevatten |
| [npm-test](../templates/npm-test.yml) | Geen; de repository moet een lockfile en CI-testscript bevatten |
| [image-build](../templates/image-build.yml) | Geen; gebruikt standaard GitLab Registry voor publicatie en authenticatie |
| [deployment-select](../templates/deployment-select.yml) | `pipeline-config`; voor pipelines waarin gebruikers tijdens de uitvoering een deploymentprofiel kunnen kiezen |
| [release-reserve](../templates/release-reserve.yml) | Geen; vereist bij uitvoering een protected releasebranch en variabelen voor de Git-deploy-key |
| [release-check](../templates/release-check.yml) | `image-path`, `version`, `commit`; toegang tot de registry is nodig |
| [gitlab-release](../templates/gitlab-release.yml) | `version`; gepubliceerde image-/chartoutputs en een GitLab-jobtoken zijn nodig |

Veelgebruikte optionele inputs:

| Input | Standaardwaarde |
|---|---|
| `job-name`, `stage` | Afhankelijk van de gekozen module |
| `working-directory` | `.` |
| `output-prefix` | Modulespecifiek, bijvoorbeeld `MAVEN_BUILD` |
| `pre-hook`, `post-hook`, `cleanup-hook` | Leeg: geen hook |
| `hook-parameters-json` | `{}` |
| `job-timeout` | `30m` voor de demomodules |
| `artifact-expire-in` | `7 days` |
| `maven-executable` | `./mvnw` in de Maven-, Jib- en Cucumber-modules |
| Cucumber `profile` | Leeg: geen Maven-profiel |

**Voorwaarden bij uitvoering:**

- Cucumber leest de URL standaard uit `HELM_DEPLOY_URL`. Lever die variabele aan, kies een andere met `target-url-variable` of stel `target-url-variable: ''` in als de tests zelf de applicatie starten.
- Geef bij `helm-deploy` expliciet `image-ref-variable` mee, bijvoorbeeld `JIB_BUILD_IMAGE_REF`. De module veronderstelt niet langer dat de optionele imageverificatiemodule is uitgevoerd. Bestaande pipelines die op een oudere bibliotheekversie zijn vastgezet, houden hun oude standaardwaarde. Voeg deze input toe bij een upgrade; de standaardpipeline voor Java doet dit al.
- Helm heeft `chart` of `chart-variable` nodig. De gekozen imagevariabele moet een onveranderlijke imagereferentie bevatten. Lever een kubeconfig aan via `kubeconfig-variable` of de beschreven Kubernetes-omgevingsvariabelen. De chart moet `image.repository` en `image.digest` ondersteunen.
- Publiceren vereist authenticatie voor de gekozen registry of Maven-repository. Gebruik een settingsbestand, GitLab-variabelen of een pre-hook voor authenticatie. Zie [organisatie-instellingen en toegangsgegevens](defaults.md).

De [modulehandleiding](modules.md) bevat voor elke actieve module een minimaal voorbeeld. Een pipeline met één module kan zo klein zijn. Stel `MY_MAVEN_IMAGE` in op de gewenste Maven-image; dit voorbeeld gebruikt de daarin geïnstalleerde Maven:

```yaml
stages: [build]

include:
  - component: $CI_SERVER_FQDN/root/ci-components/maven-build@54f0b3819b073d138a5b0842979fe0bc84fefe0f
    inputs:
      image: $MY_MAVEN_IMAGE
      maven-executable: mvn
```

Dit maakt één job aan met de standaardwerkmap, timeout en bewaartermijn, zonder eigen hooks. De gedeelde hookafhandeling wordt automatisch ingeladen. Er is geen organisatiebestand of andere module nodig. Declareer de gekozen stage in je pipeline en gebruik een runner die de gekozen image kan uitvoeren.
